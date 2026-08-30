import math

import pandas as pd

try:
    from pyspark import pipelines as dp
except ImportError:  # fora do runtime DLT (ex.: testes unitários locais)
    dp = None


def _materialized_view(**kwargs):
    """Aplica @dp.materialized_view quando o runtime DLT está disponível.

    Fora do Databricks, retorna um decorador no-op para que a lógica pura
    do módulo continue importável e testável em memória.
    """
    if dp is None:
        return lambda fn: fn
    return dp.materialized_view(**kwargs)


# Camada Gold — gold_agent_operations (ADR-008).
#
# Visão granular das operações do agente para o dashboard (que lê
# SOMENTE Gold — ADR-008). Combina:
#   - agent_events (runtime): uma linha por turno e por chamada de
#     ferramenta, com latência, tokens, modelo, status e custo;
#   - conversation_events (runtime): eventos de segurança e qualidade
#     (`refusal`, `tool_selection_blocked`, `error`,
#     `handoff_to_human`) normalizados no mesmo schema.
#
# A coluna `source` preserva a rastreabilidade da origem. As tabelas
# runtime são garantidas pela task bootstrap_runtime do job
# orquestrador, executada antes do refresh da pipeline; a leitura SEMPRE
# parte das tabelas (linhagem DLT — o MV recomputa a cada atualização).
#
# Decisão de implementação: projeções e union em Spark; `build_rows`
# permanece como referência testável do mapeamento.

SECURITY_EVENT_TYPES = ("refusal", "tool_selection_blocked", "error", "handoff_to_human")

COLUMNS = [
    "event_id",
    "session_id",
    "created_at",
    "event_type",
    "tool_name",
    "status",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "model",
    "cost_estimated",
    "error_message",
    "source",
]

SCHEMA = (
    "event_id STRING, session_id STRING, created_at TIMESTAMP, event_type STRING, "
    "tool_name STRING, status STRING, duration_ms BIGINT, input_tokens INT, "
    "output_tokens INT, model STRING, cost_estimated DECIMAL(18,6), "
    "error_message STRING, source STRING"
)


def _agent_row(row):
    return {
        "event_id": row.get("event_id"),
        "session_id": row.get("session_id"),
        "created_at": row.get("created_at"),
        "event_type": row.get("event_type"),
        "tool_name": row.get("tool_name"),
        "status": row.get("status"),
        "duration_ms": row.get("duration_ms"),
        "input_tokens": row.get("input_tokens"),
        "output_tokens": row.get("output_tokens"),
        "model": row.get("model"),
        "cost_estimated": row.get("cost_estimated"),
        "error_message": row.get("error_message"),
        "source": "agent_events",
    }


def _event_row(row):
    return {
        "event_id": row.get("event_id"),
        "session_id": row.get("session_id"),
        "created_at": row.get("created_at"),
        "event_type": row.get("event_type"),
        "tool_name": row.get("tool_name"),
        "status": None,
        "duration_ms": None,
        "input_tokens": None,
        "output_tokens": None,
        "model": None,
        "cost_estimated": None,
        "error_message": row.get("content"),
        "source": "conversation_events",
    }


def build_rows(agent_rows, event_rows):
    """Referência testável: projeta agent_events e normaliza os eventos
    de segurança de conversation_events (ADR-008)."""
    rows = [_agent_row(row) for row in agent_rows]
    for row in event_rows:
        if row.get("event_type") in SECURITY_EVENT_TYPES:
            rows.append(_event_row(row))
    return rows


def _to_python(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _operations_pandas(iterator):
    """Aplica `build_rows` por partição (mapInPandas)."""
    for pdf in iterator:
        records = [
            {key: _to_python(value) for key, value in row.items()}
            for row in pdf.to_dict("records")
        ]
        yield pd.DataFrame(build_rows(records, []), columns=COLUMNS)


def _security_pandas(iterator):
    """Normaliza os eventos de segurança por partição (mapInPandas)."""
    for pdf in iterator:
        records = [
            {key: _to_python(value) for key, value in row.items()}
            for row in pdf.to_dict("records")
        ]
        yield pd.DataFrame(build_rows([], records), columns=COLUMNS)


@_materialized_view(
    comment="Gold: operações do agente (agent_events + eventos de segurança) — ADR-008",
)
def gold_agent_operations():
    agent_events = spark.read.table("agent_events").coalesce(1)
    conversation_events = spark.read.table("conversation_events").coalesce(1)
    agent_rows = agent_events.mapInPandas(_operations_pandas, schema=SCHEMA)
    security_rows = conversation_events.mapInPandas(_security_pandas, schema=SCHEMA)
    return agent_rows.unionByName(security_rows)
