"""Testes da ferramenta request_human_approval
(docs/specs/request_human_approval.md).

Cobrem os critérios de aceite CA01–CA11: solicitação, registro em
`approvals`, aprovação, rejeição, bloqueio de pagamento, aprovador
obrigatório, justificativa, duplicidade e auditoria (ADR-003).
"""

from nexum_sales_assistant.tools import request_human_approval as rha
from nexum_sales_assistant.tools._table_ref import qualified_table


def _quote(status="draft", session_id="SES-1", total_amount=15600.00):
    return {
        "quote_id": "QTE-1",
        "customer_id": "C0001",
        "session_id": session_id,
        "status": status,
        "total_amount": total_amount,
        "currency": "BRL",
        "created_at": "2026-08-29T10:00:00Z",
        "approved_at": None,
        "approved_by": None,
        "rejection_reason": None,
        "payment_status": "not_started",
        "document_id": None,
    }


def _quote_item():
    return {
        "quote_item_id": "QTI-1",
        "quote_id": "QTE-1",
        "product_id": "PRD-TEMP-001",
        "quantity": 20,
        "unit_price": 780.00,
        "subtotal": 15600.00,
    }


def _approval(status="pending"):
    return {
        "approval_id": "APR-1",
        "quote_id": "QTE-1",
        "requested_by": "assistant",
        "resolved_by": None,
        "status": status,
        "reason": None,
        "created_at": "2026-08-29T10:00:00Z",
        "resolved_at": None,
    }


class TestRequestHumanApproval:
    def test_request_moves_quote_to_pending(self, fake_spark):
        # CA01/CA02: draft → pending_approval; registro em approvals `pending`.
        fake_spark.tables[qualified_table("quotes")] = [_quote("draft")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        result = rha.run(
            {
                "operation": "request",
                "session_id": "SES-1",
                "quote_id": "QTE-1",
                "requested_by": "assistant",
            }
        )
        assert result["approval_status"] == "requested"
        assert result["quote_status"] == "pending_approval"
        assert result["next_action"] == "human_review"
        assert fake_spark.tables[qualified_table("quotes")][0]["status"] == "pending_approval"
        approval = fake_spark.tables[qualified_table("approvals")][0]
        assert approval["status"] == "pending"
        assert approval["resolved_by"] is None
        assert approval["resolved_at"] is None

    def test_resolve_approves_quote(self, fake_spark):
        # CA03: aprovação válida → approved, com cópia para a cotação (ADR-003).
        fake_spark.tables[qualified_table("quotes")] = [_quote("pending_approval")]
        fake_spark.tables[qualified_table("approvals")] = [_approval("pending")]
        result = rha.run(
            {
                "operation": "resolve",
                "session_id": "SES-1",
                "approval_id": "APR-1",
                "decision": "approved",
                "resolved_by": "vendor-001",
            }
        )
        assert result["approval_status"] == "approved"
        assert result["quote_status"] == "approved"
        assert result["next_action"] == "simulate_payment"
        quote = fake_spark.tables[qualified_table("quotes")][0]
        assert quote["status"] == "approved"
        assert quote["approved_by"] == "vendor-001"
        assert quote["approved_at"] is not None
        approval = fake_spark.tables[qualified_table("approvals")][0]
        assert approval["status"] == "approved"
        assert approval["resolved_by"] == "vendor-001"
        assert approval["resolved_at"] is not None

    def test_resolve_rejects_quote(self, fake_spark):
        # CA04/CA07: rejeição com justificativa; approved_by permanece nulo.
        fake_spark.tables[qualified_table("quotes")] = [_quote("pending_approval")]
        fake_spark.tables[qualified_table("approvals")] = [_approval("pending")]
        result = rha.run(
            {
                "operation": "resolve",
                "session_id": "SES-1",
                "approval_id": "APR-1",
                "decision": "rejected",
                "resolved_by": "vendor-001",
                "reason": "Quantidade precisa ser revisada com o cliente",
            }
        )
        assert result["approval_status"] == "rejected"
        assert result["quote_status"] == "rejected"
        assert result["next_action"] == "human_follow_up"
        quote = fake_spark.tables[qualified_table("quotes")][0]
        assert quote["status"] == "rejected"
        assert quote["rejection_reason"] == "Quantidade precisa ser revisada com o cliente"
        assert quote["approved_by"] is None
        assert quote["approved_at"] is None

    def test_requires_authorized_approver(self, fake_spark):
        # CA06/CA11: sem aprovador autorizado → rejeição; o assistente não
        # pode resolver a aprovação em seu próprio nome.
        result = rha.run(
            {
                "operation": "resolve",
                "session_id": "SES-1",
                "approval_id": "APR-1",
                "decision": "approved",
                "resolved_by": "assistant",
            }
        )
        assert result["error_code"] == "UNAUTHORIZED_APPROVER"

    def test_rejection_requires_reason(self, fake_spark):
        result = rha.run(
            {
                "operation": "resolve",
                "session_id": "SES-1",
                "approval_id": "APR-1",
                "decision": "rejected",
                "resolved_by": "vendor-001",
            }
        )
        assert result["error_code"] == "MISSING_REJECTION_REASON"

    def test_request_only_from_draft(self, fake_spark):
        # CA05: cotação fora de `draft` não pode ser encaminhada.
        fake_spark.tables[qualified_table("quotes")] = [_quote("pending_approval")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        result = rha.run(
            {
                "operation": "request",
                "session_id": "SES-1",
                "quote_id": "QTE-1",
                "requested_by": "assistant",
            }
        )
        assert result["error_code"] == "INVALID_QUOTE_STATUS"

    def test_no_duplicate_pending_approval(self, fake_spark):
        # CA08: cotação já pendente não gera segunda solicitação.
        fake_spark.tables[qualified_table("quotes")] = [_quote("pending_approval")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        rha.run(
            {
                "operation": "request",
                "session_id": "SES-1",
                "quote_id": "QTE-1",
                "requested_by": "assistant",
            }
        )
        assert fake_spark.tables.get(qualified_table("approvals"), []) == []

    def test_audit_events_recorded(self, fake_spark):
        # CA09: solicitação e resolução geram eventos de auditoria.
        fake_spark.tables[qualified_table("quotes")] = [_quote("draft")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        request_result = rha.run(
            {
                "operation": "request",
                "session_id": "SES-1",
                "quote_id": "QTE-1",
                "requested_by": "assistant",
            }
        )
        fake_spark.tables[qualified_table("quotes")] = [_quote("pending_approval")]
        fake_spark.tables[qualified_table("approvals")] = [
            {
                **_approval("pending"),
                "approval_id": request_result["approval_id"],
            }
        ]
        rha.run(
            {
                "operation": "resolve",
                "session_id": "SES-1",
                "approval_id": request_result["approval_id"],
                "decision": "approved",
                "resolved_by": "vendor-001",
            }
        )
        events = fake_spark.tables.get(qualified_table("conversation_events"), [])
        event_types = {e.get("event_type") for e in events}
        assert "approval_requested" in event_types
        assert "approval_resolved" in event_types
