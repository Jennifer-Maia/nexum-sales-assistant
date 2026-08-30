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


# Camada Gold — gold_conversation_audit (docs/data_model.md §17).
#
# Visão de auditoria da conversa e das ferramentas, uma linha por
# session_id, agregando os eventos de `conversation_events` — tabela
# persistida em tempo de execução pelas ferramentas (docs/data_model.md
# §13; docs/agent_harness.md §20).
#
# Mapeamento dos campos de docs/data_model.md §17 para os tipos de
# evento documentados em docs/data_model.md §13:
#   - quantidade de mensagens ............ message_received
#   - quantidade de perguntas ............ question_asked
#   - produtos consultados ............... product_search
#   - recomendações realizadas ........... recommendation_created
#   - cotação criada ..................... quote_created
#   - aprovação (solicitada/resolvida) ... approval_requested /
#                                         approval_resolved
#   - pagamento simulado ................. payment_simulated
#   - documento gerado ................... document_generated
#   - encaminhamento humano .............. handoff_to_human
#   - erros .............................. error
#
# Eventos com session_id ausente ou com event_type fora do mapeamento
# não entram na agregação (nada é inventado). Comportamento sem dados:
# `conversation_events` é garantida com `CREATE TABLE IF NOT EXISTS`
# (mesmo schema do schema_bootstrap do agente, ADR-007) e a Gold lê
# SEMPRE a tabela, preservando a linhagem no DLT (o MV recomputa a cada
# atualização da pipeline).
#
# Decisão de implementação: `build_rows` (função pura testável) aplicada
# via `mapInPandas` com `coalesce(1)` — mesma decisão documentada em
# silver_companies.py.

# event_type (docs/data_model.md §13) → coluna da Gold (docs/data_model.md §17).
EVENT_TYPE_MAPPING = {
    "message_received": "message_count",
    "question_asked": "question_count",
    "product_search": "products_consulted",
    "recommendation_created": "recommendations_created",
    "quote_created": "quotes_created",
    "approval_requested": "approvals_requested",
    "approval_resolved": "approvals_resolved",
    "payment_simulated": "payments_simulated",
    "document_generated": "documents_generated",
    "handoff_to_human": "handoffs_to_human",
    "error": "errors",
}

COLUMNS = [
    "session_id",
    "message_count",
    "question_count",
    "products_consulted",
    "recommendations_created",
    "quotes_created",
    "approvals_requested",
    "approvals_resolved",
    "payments_simulated",
    "documents_generated",
    "handoffs_to_human",
    "errors",
]

SCHEMA = (
    "session_id STRING, message_count INT, question_count INT, products_consulted INT, "
    "recommendations_created INT, quotes_created INT, approvals_requested INT, "
    "approvals_resolved INT, payments_simulated INT, documents_generated INT, "
    "handoffs_to_human INT, errors INT"
)


def build_rows(events):
    """Agrega eventos de conversa por sessão.

    Entrada: lista de dicts no schema de conversation_events.
    Saída: lista de dicts no schema da Gold, uma linha por session_id,
    ordenada por session_id (determinística).
    """
    sessions = {}
    for event in events:
        session_id = event.get("session_id")
        if session_id is None:
            continue
        column = EVENT_TYPE_MAPPING.get(event.get("event_type"))
        if column is None:
            continue
        stats = sessions.setdefault(
            session_id, {name: 0 for name in EVENT_TYPE_MAPPING.values()}
        )
        stats[column] += 1
    rows = [{"session_id": session_id, **stats} for session_id, stats in sessions.items()]
    rows.sort(key=lambda row: row["session_id"])
    return rows


def _to_python(value):
    """Converte valores vindos do pandas para tipos Python limpos."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _audit_pandas(iterator):
    """Aplica `build_rows` por partição (mapInPandas)."""
    for pdf in iterator:
        records = [
            {key: _to_python(value) for key, value in row.items()}
            for row in pdf.to_dict("records")
        ]
        yield pd.DataFrame(build_rows(records), columns=COLUMNS)


# Schema de conversation_events (mesmo do schema_bootstrap do agente —
# ADR-007). Duplicado aqui para o pacote ETL permanecer autocontido.
_CONVERSATION_EVENTS_SCHEMA = (
    "event_id STRING, session_id STRING, event_type STRING, actor STRING, "
    "content STRING, tool_name STRING, tool_reference_id STRING, created_at TIMESTAMP"
)


@_materialized_view(
    comment="Gold: auditoria da conversa e das ferramentas por sessão (docs/data_model.md §17)",
)
def gold_conversation_audit():
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS conversation_events ({_CONVERSATION_EVENTS_SCHEMA})"
    )
    events = spark.read.table("conversation_events").coalesce(1)
    return events.mapInPandas(_audit_pandas, schema=SCHEMA)
