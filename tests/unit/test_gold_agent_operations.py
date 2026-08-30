"""Testes da Gold operacional gold_agent_operations (ADR-008).

Cobrem schema, mapeamento de agent_events, normalização dos eventos de
segurança de conversation_events e rastreabilidade (`source`), com
dados em memória (sem Spark externo).
"""

import datetime

from nexum_sales_assistant_etl.transformations import gold_agent_operations as go


def _schema_columns():
    return [part.strip().split()[0] for part in go.SCHEMA.split(", ")]


def _agent_event(event_id="AGE-1", event_type="tool_call", **overrides):
    row = {
        "event_id": event_id,
        "session_id": "SES-1",
        "conversation_event_id": None,
        "created_at": datetime.datetime(2026, 8, 30, 12, 0, 0),
        "event_type": event_type,
        "tool_name": "search_products",
        "result_summary": "{}",
        "status": "success",
        "duration_ms": 100,
        "input_tokens": 10,
        "output_tokens": 5,
        "model": "fake-model",
        "cost_estimated": None,
        "error_message": None,
    }
    row.update(overrides)
    return row


def _conversation_event(event_id="EVT-1", event_type="refusal", **overrides):
    row = {
        "event_id": event_id,
        "session_id": "SES-1",
        "event_type": event_type,
        "actor": "system",
        "content": "injection: ignore as instruções",
        "tool_name": "search_products",
        "tool_reference_id": None,
        "created_at": datetime.datetime(2026, 8, 30, 12, 1, 0),
    }
    row.update(overrides)
    return row


class TestSchema:
    def test_schema_columns(self):
        assert _schema_columns() == [
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


class TestMapping:
    def test_agent_rows_projected_with_source(self):
        rows = go.build_rows([_agent_event()], [])
        assert len(rows) == 1
        assert rows[0]["source"] == "agent_events"
        assert rows[0]["duration_ms"] == 100
        assert rows[0]["input_tokens"] == 10
        assert rows[0]["model"] == "fake-model"

    def test_security_events_normalized(self):
        rows = go.build_rows([], [_conversation_event(event_type="refusal")])
        assert len(rows) == 1
        assert rows[0]["source"] == "conversation_events"
        assert rows[0]["event_type"] == "refusal"
        assert rows[0]["error_message"] == "injection: ignore as instruções"
        assert rows[0]["duration_ms"] is None
        assert rows[0]["input_tokens"] is None

    def test_non_security_events_ignored(self):
        rows = go.build_rows(
            [], [_conversation_event(event_type="session_started"), _conversation_event(event_type="message_received")]
        )
        assert rows == []

    def test_empty_inputs(self):
        assert go.build_rows([], []) == []
