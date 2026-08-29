"""Testes da camada Gold — gold_conversation_audit (docs/data_model.md §16).

Cobrem schema, granularidade por session_id, contagem por tipo de evento,
eventos ignorados (sem session_id / tipo desconhecido), ausência de
duplicatas indevidas e comportamento sem dados, com dados em memória
(sem Spark externo).
"""

import datetime

from nexum_sales_assistant_etl.transformations import gold_conversation_audit as ga


def _schema_columns():
    return [part.strip().split()[0] for part in ga.SCHEMA.split(", ")]


def _event(event_id="EVT-1", session_id="SES-1", event_type="message_received", **overrides):
    row = {
        "event_id": event_id,
        "session_id": session_id,
        "event_type": event_type,
        "actor": "system",
        "content": "{}",
        "tool_name": "search_products",
        "tool_reference_id": None,
        "created_at": datetime.datetime(2026, 8, 27, 10, 0, 0),
    }
    row.update(overrides)
    return row


class TestSchema:
    def test_schema_columns(self):
        assert _schema_columns() == [
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


class TestAggregation:
    def test_counts_by_event_type(self):
        events = [
            _event("EVT-1", event_type="session_started"),
            _event("EVT-2", event_type="message_received"),
            _event("EVT-3", event_type="message_received"),
            _event("EVT-4", event_type="question_asked"),
            _event("EVT-5", event_type="product_search"),
            _event("EVT-6", event_type="recommendation_created"),
            _event("EVT-7", event_type="quote_created"),
            _event("EVT-8", event_type="approval_requested"),
            _event("EVT-9", event_type="approval_resolved"),
            _event("EVT-10", event_type="payment_simulated"),
            _event("EVT-11", event_type="document_generated"),
            _event("EVT-12", event_type="handoff_to_human"),
            _event("EVT-13", event_type="error"),
        ]
        row = ga.build_rows(events)[0]
        assert row["message_count"] == 2
        assert row["question_count"] == 1
        assert row["products_consulted"] == 1
        assert row["recommendations_created"] == 1
        assert row["quotes_created"] == 1
        assert row["approvals_requested"] == 1
        assert row["approvals_resolved"] == 1
        assert row["payments_simulated"] == 1
        assert row["documents_generated"] == 1
        assert row["handoffs_to_human"] == 1
        assert row["errors"] == 1


class TestGranularity:
    def test_one_row_per_session(self):
        events = [_event(session_id="SES-1"), _event("EVT-2", session_id="SES-2")]
        rows = ga.build_rows(events)
        assert [r["session_id"] for r in rows] == ["SES-1", "SES-2"]

    def test_sessions_sorted_deterministically(self):
        events = [
            _event(session_id="SES-2"),
            _event("EVT-2", session_id="SES-1"),
            _event("EVT-3", session_id="SES-3"),
        ]
        rows = ga.build_rows(events)
        assert [r["session_id"] for r in rows] == ["SES-1", "SES-2", "SES-3"]


class TestIgnoredEvents:
    def test_event_without_session_ignored(self):
        rows = ga.build_rows([_event(session_id=None)])
        assert rows == []

    def test_unknown_event_type_ignored(self):
        # event_type fora do mapeamento documentado não entra na
        # agregação nem cria linha de sessão (nenhum dado é inventado).
        rows = ga.build_rows([_event(event_type="session_started")])
        assert rows == []

    def test_mapped_events_only_for_own_columns(self):
        # Um evento mapeado zera as demais colunas da sessão.
        rows = ga.build_rows([_event(event_type="error")])
        assert len(rows) == 1
        assert rows[0]["errors"] == 1
        assert rows[0]["message_count"] == 0


class TestNoInvention:
    def test_only_schema_columns_returned(self):
        row = ga.build_rows([_event()])[0]
        assert set(row.keys()) == set(_schema_columns())

    def test_empty_events(self):
        assert ga.build_rows([]) == []
