"""Testes da ferramenta simulate_payment (docs/specs/simulate_payment.md).

Cobrem os critérios de aceite CA01–CA12: aprovação obrigatória, sucesso,
falha, estado da cotação, valor confiável, simulação explícita, ausência
de pagamento real, idempotência, auditoria e não-alteração do estoque.
"""

from nexum_sales_assistant.tools import simulate_payment as spay
from nexum_sales_assistant.tools._table_ref import qualified_table


def _quote(status="approved"):
    return {
        "quote_id": "QTE-1",
        "customer_id": "C0001",
        "session_id": "SES-1",
        "status": status,
        "total_amount": 15600.00,
        "currency": "BRL",
        "created_at": "2026-08-29T10:00:00Z",
        "approved_at": "2026-08-29T11:00:00Z",
        "approved_by": "vendor-001",
        "rejection_reason": None,
        "payment_status": "not_started",
        "document_id": None,
    }


def _approval():
    return {
        "approval_id": "APR-1",
        "quote_id": "QTE-1",
        "requested_by": "assistant",
        "resolved_by": "vendor-001",
        "status": "approved",
        "reason": None,
        "created_at": "2026-08-29T10:00:00Z",
        "resolved_at": "2026-08-29T11:00:00Z",
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


def _inputs(**overrides):
    inputs = {
        "session_id": "SES-1",
        "quote_id": "QTE-1",
        "requested_by": "vendor-001",
        "simulation_result": "success",
    }
    inputs.update(overrides)
    return inputs


class TestSimulatePayment:
    def test_success_pays_quote(self, fake_spark):
        # CA02/CA04: sucesso → simulated_success e cotação `paid`.
        fake_spark.tables[qualified_table("quotes")] = [_quote("approved")]
        fake_spark.tables[qualified_table("approvals")] = [_approval()]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        result = spay.run(_inputs())
        assert result["payment_status"] == "simulated_success"
        assert result["quote_status"] == "paid"
        assert result["next_action"] == "generate_document"
        payment = fake_spark.tables[qualified_table("payments")][0]
        assert payment["status"] == "simulated_success"
        assert payment["simulated"] is True
        quote = fake_spark.tables[qualified_table("quotes")][0]
        assert quote["status"] == "paid"
        assert quote["payment_status"] == "simulated_success"

    def test_approval_required(self, fake_spark):
        # CA01: sem aprovação válida, o pagamento não pode ser simulado.
        fake_spark.tables[qualified_table("quotes")] = [_quote("draft")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        result = spay.run(_inputs())
        assert result["payment_status"] == "approval_required"
        assert result["error_code"] == "QUOTE_NOT_APPROVED"
        assert fake_spark.tables.get(qualified_table("payments"), []) == []
        assert fake_spark.tables[qualified_table("quotes")][0]["status"] == "draft"

    def test_failure_keeps_quote_approved(self, fake_spark):
        # CA03/CA04: falha → simulated_failure e cotação permanece `approved`.
        fake_spark.tables[qualified_table("quotes")] = [_quote("approved")]
        fake_spark.tables[qualified_table("approvals")] = [_approval()]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        result = spay.run(_inputs(simulation_result="failure"))
        assert result["payment_status"] == "simulated_failure"
        assert result["quote_status"] == "approved"
        assert result["next_action"] == "human_follow_up"
        payment = fake_spark.tables[qualified_table("payments")][0]
        assert payment["status"] == "simulated_failure"
        assert payment["simulated"] is True
        quote = fake_spark.tables[qualified_table("quotes")][0]
        assert quote["status"] == "approved"

    def test_amount_from_quote_total(self, fake_spark):
        # CA05: o valor vem de quotes.total_amount, nunca de entrada externa.
        fake_spark.tables[qualified_table("quotes")] = [_quote("approved")]
        fake_spark.tables[qualified_table("approvals")] = [_approval()]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        spay.run(_inputs())
        assert fake_spark.tables[qualified_table("payments")][0]["amount"] == 15600.00

    def test_idempotency(self, fake_spark):
        # CA08: não gera dois pagamentos simulados bem-sucedidos.
        fake_spark.tables[qualified_table("quotes")] = [_quote("paid")]
        fake_spark.tables[qualified_table("approvals")] = [_approval()]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        fake_spark.tables[qualified_table("payments")] = [
            {
                "payment_id": "PAY-1",
                "quote_id": "QTE-1",
                "status": "simulated_success",
                "amount": 15600.00,
                "currency": "BRL",
                "simulated": True,
                "created_at": "2026-08-29T12:00:00Z",
            }
        ]
        result = spay.run(_inputs())
        assert result["payment_status"] == "already_simulated"
        assert result["next_action"] == "generate_document"
        assert len(fake_spark.tables[qualified_table("payments")]) == 1

    def test_forbidden_simulation_result(self, fake_spark):
        # SPEC §5: valores que confundem simulação com pagamento real.
        result = spay.run(_inputs(simulation_result="paid"))
        assert result["error_code"] == "INVALID_SIMULATION_RESULT"

    def test_audit_event_recorded(self, fake_spark):
        # CA09: toda execução gera evento em conversation_events.
        fake_spark.tables[qualified_table("quotes")] = [_quote("approved")]
        fake_spark.tables[qualified_table("approvals")] = [_approval()]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        spay.run(_inputs())
        events = fake_spark.tables.get(qualified_table("conversation_events"), [])
        assert any(
            e.get("event_type") == "payment_simulated"
            and e.get("tool_name") == "simulate_payment"
            for e in events
        )

    def test_does_not_touch_inventory(self, fake_spark):
        # CA11: a simulação não altera quantidades de estoque.
        fake_spark.tables[qualified_table("quotes")] = [_quote("approved")]
        fake_spark.tables[qualified_table("approvals")] = [_approval()]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [
            {
                "product_id": "PRD-TEMP-001",
                "warehouse_id": "WH-MAIN",
                "available_quantity": 42,
                "reserved_quantity": 0,
            }
        ]
        before = dict(fake_spark.tables[qualified_table("gold_product_availability")][0])
        spay.run(_inputs())
        assert fake_spark.tables[qualified_table("gold_product_availability")][0] == before
