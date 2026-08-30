"""Testes das métricas operacionais do Nexum (ADR-007).

Cobrem fontes das queries (isolamento de catalog/schema e de projeto),
comportamento com dados vazios e divisão segura — em memória, sem
Spark externo, sem API real.
"""

import re

from nexum_sales_assistant.metrics import (
    ALLOWED_TABLES,
    DATASET_QUERIES,
    funnel_counts,
    safe_rate,
)


def _table_names(query_lines):
    sql = " ".join(query_lines)
    return set(re.findall(r"\bFROM\s+([a-z_][a-z0-9_]*)", sql, flags=re.IGNORECASE))


class TestQuerySources:
    def test_queries_only_reference_allowed_tables(self):
        for name, lines in DATASET_QUERIES.items():
            tables = _table_names(lines)
            assert tables, f"{name}: nenhuma fonte detectada"
            assert tables <= ALLOWED_TABLES, f"{name}: tabelas fora da lista: {tables}"

    def test_queries_do_not_reference_other_projects_or_legacy(self):
        sql = " ".join(" ".join(lines) for lines in DATASET_QUERIES.values()).lower()
        for forbidden in (
            "sample_",
            "grid_",
            "employees",
            "b2b",
            "score",
            "churn",
            "dashboard_legacy",
        ):
            assert forbidden not in sql, f"referência indevida: {forbidden}"

    def test_queries_are_bare_names(self):
        # Isolamento de catalog/schema: as queries não fixam catalog ou
        # schema; o dashboard supre ambos pela configuração do recurso.
        sql = " ".join(" ".join(lines) for lines in DATASET_QUERIES.values())
        assert "workspace." not in sql
        assert "test_catalog" not in sql

    def test_every_dataset_has_queries(self):
        assert set(DATASET_QUERIES) == {
            "ds_sessions",
            "ds_funnel",
            "ds_tool_calls",
            "ds_agent_turns",
            "ds_quality",
            "ds_cost",
            "ds_update",
        }


class TestEmptyData:
    def test_funnel_counts_with_empty_data(self):
        # Dados vazios produzem zeros (COUNT sobre tabelas vazias) — o
        # dashboard mostra zero sem dados fictícios (ADR-007).
        counts = funnel_counts([], [], [], [], [])
        assert counts == {
            "sessoes": 0,
            "cotacoes": 0,
            "aprovacoes": 0,
            "pagamentos_simulados": 0,
            "documentos_simulados": 0,
        }

    def test_funnel_counts_with_data(self):
        counts = funnel_counts(range(2), range(1), range(1), range(1), range(1))
        assert counts["sessoes"] == 2
        assert counts["cotacoes"] == 1
        assert counts["aprovacoes"] == 1
        assert counts["pagamentos_simulados"] == 1
        assert counts["documentos_simulados"] == 1


class TestSafeRate:
    def test_no_division_by_zero(self):
        assert safe_rate(0, 0) == 0.0
        assert safe_rate(5, 0) == 0.0

    def test_normal_rates(self):
        assert safe_rate(5, 10) == 0.5
        assert safe_rate(0, 10) == 0.0


class TestAllowedTables:
    def test_allowed_tables_cover_pipeline_and_runtime(self):
        assert "gold_product_catalog" in ALLOWED_TABLES
        assert "conversation_events" in ALLOWED_TABLES
        assert "agent_events" in ALLOWED_TABLES
        assert "sample_trips_grid_intelligence" not in ALLOWED_TABLES
