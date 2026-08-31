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
    tables = set(re.findall(r"\bFROM\s+([a-z_][a-z0-9_]*)", sql, flags=re.IGNORECASE))
    # Alias de CTE (WITH x AS (...)) não são tabelas físicas.
    ctes = set(re.findall(r"([a-z_][a-z0-9_]*)\s+AS\s*\(", sql, flags=re.IGNORECASE))
    return tables - ctes


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
            "ds_conversion",
            "ds_tool_calls",
            "ds_agent_turns",
            "ds_quality",
            "ds_cost",
            "ds_update",
        }

    def test_division_by_zero_is_safe_in_sql(self):
        # As taxas do funil usam NULLIF/COALESCE (ADR-007): denominador
        # zero produz 0, nunca erro de divisão.
        sql = " ".join(DATASET_QUERIES["ds_conversion"]).lower()
        assert "nullif" in sql
        assert "coalesce" in sql
        sql_cost = " ".join(DATASET_QUERIES["ds_cost"]).lower()
        assert "nullif" in sql_cost


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
    def test_dashboard_reads_only_gold_tables(self):
        # Regra do ADR-008: o dashboard consulta exclusivamente Gold —
        # nenhuma tabela runtime/transacional é permitida nas queries.
        for name in ALLOWED_TABLES:
            assert name.startswith("gold_"), f"tabela não-Gold permitida: {name}"
        assert "gold_conversation_audit" in ALLOWED_TABLES
        assert "gold_agent_operations" in ALLOWED_TABLES
        assert "gold_data_freshness" in ALLOWED_TABLES

    def test_runtime_tables_not_allowed(self):
        for forbidden in (
            "agent_events",
            "conversation_events",
            "quotes",
            "quote_items",
            "approvals",
            "payments",
            "documents",
            "bronze_companies",
            "silver_companies",
            "sample_trips_grid_intelligence",
        ):
            assert forbidden not in ALLOWED_TABLES
