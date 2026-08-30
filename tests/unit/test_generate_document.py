"""Testes da ferramenta generate_document (docs/specs/generate_document.md).

Cobrem os critérios de aceite CA01–CA12: pagamento obrigatório, pagamento
simulado, documento simulado, aviso obrigatório, dados confiáveis, estado
da cotação, falha de pagamento, idempotência, auditoria e ausência de
validade fiscal.
"""

from nexum_sales_assistant.tools import generate_document as gd
from nexum_sales_assistant.tools._table_ref import qualified_table


def _quote(status="paid"):
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
        "payment_status": "simulated_success" if status == "paid" else "not_started",
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


def _payment(status="simulated_success", simulated=True, amount=15600.00):
    return {
        "payment_id": "PAY-1",
        "quote_id": "QTE-1",
        "status": status,
        "amount": amount,
        "currency": "BRL",
        "simulated": simulated,
        "created_at": "2026-08-29T12:00:00Z",
    }


def _catalog_product():
    return {
        "product_id": "PRD-TEMP-001",
        "sku": "NEX-TEMP-001",
        "product_name": "Sensor de Temperatura Industrial T150",
    }


def _inputs(**overrides):
    inputs = {
        "session_id": "SES-1",
        "quote_id": "QTE-1",
        "requested_by": "system",
        "document_format": "html",
    }
    inputs.update(overrides)
    return inputs


class TestGenerateDocument:
    def test_generates_simulated_document(self, fake_spark):
        # CA01–CA06: pagamento simulated_success → documento gerado e
        # cotação concluída (paid → completed).
        fake_spark.tables[qualified_table("quotes")] = [_quote("paid")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        fake_spark.tables[qualified_table("payments")] = [_payment()]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product()]
        fake_spark.tables[qualified_table("silver_companies")] = [
            {"company_id": "C0001", "company_name": "Metalúrgica Ferrovale Ltda"}
        ]
        result = gd.run(_inputs())
        assert result["document_status"] == "generated"
        assert result["quote_status"] == "completed"
        document = fake_spark.tables[qualified_table("documents")][0]
        assert document["document_type"] == "simulated_receipt"
        assert document["has_fiscal_value"] is False
        assert document["quote_id"] == "QTE-1"
        quote = fake_spark.tables[qualified_table("quotes")][0]
        assert quote["status"] == "completed"
        assert quote["document_id"] == result["document_id"]

    def test_requires_successful_payment(self, fake_spark):
        # CA01: sem pagamento → payment_required; nenhum documento criado.
        fake_spark.tables[qualified_table("quotes")] = [_quote("paid")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        fake_spark.tables[qualified_table("payments")] = []
        result = gd.run(_inputs())
        assert result["document_status"] == "payment_required"
        assert result["error_code"] == "SUCCESSFUL_SIMULATED_PAYMENT_REQUIRED"
        assert fake_spark.tables.get(qualified_table("documents"), []) == []

    def test_payment_failed_no_document(self, fake_spark):
        # CA07: pagamento com falha → nenhum documento criado.
        fake_spark.tables[qualified_table("quotes")] = [_quote("paid")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        fake_spark.tables[qualified_table("payments")] = [_payment(status="simulated_failure")]
        result = gd.run(_inputs())
        assert result["document_status"] == "payment_failed"
        assert result["error_code"] == "PAYMENT_SIMULATION_FAILED"
        assert fake_spark.tables.get(qualified_table("documents"), []) == []

    def test_quote_not_paid(self, fake_spark):
        # SPEC §8: documento não é gerado para cotação fora de `paid`.
        fake_spark.tables[qualified_table("quotes")] = [_quote("approved")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        fake_spark.tables[qualified_table("payments")] = [_payment()]
        result = gd.run(_inputs())
        assert result["error_code"] == "QUOTE_NOT_PAID"

    def test_idempotency(self, fake_spark):
        # CA08: não cria mais de um documento para a mesma cotação.
        fake_spark.tables[qualified_table("quotes")] = [_quote("completed")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        fake_spark.tables[qualified_table("payments")] = [_payment()]
        fake_spark.tables[qualified_table("documents")] = [
            {
                "document_id": "DOC-1",
                "quote_id": "QTE-1",
                "document_type": "simulated_receipt",
                "has_fiscal_value": False,
                "content_reference": "documents/simulated_receipt/QTE-1.html",
                "created_at": "2026-08-29T13:00:00Z",
            }
        ]
        result = gd.run(_inputs())
        assert result["document_status"] == "already_generated"
        assert result["document_id"] == "DOC-1"
        assert len(fake_spark.tables[qualified_table("documents")]) == 1

    def test_content_contains_mandatory_warnings(self):
        # CA04: o conteúdo informa a ausência de validade fiscal,
        # financeira e contábil.
        content = gd.build_document_content(
            "DOC-1",
            {
                "quote_id": "QTE-1",
                "customer_id": "C0001",
                "total_amount": 15600.00,
                "currency": "BRL",
            },
            [
                {
                    "product_id": "PRD-TEMP-001",
                    "sku": "NEX-TEMP-001",
                    "product_name": "Sensor T150",
                    "quantity": 20,
                    "unit_price": 780.00,
                    "subtotal": 15600.00,
                    "currency": "BRL",
                }
            ],
            {"payment_id": "PAY-1"},
            "Metalúrgica Ferrovale Ltda",
        )
        assert gd.DOCUMENT_WARNING in content
        assert gd.FINAL_WARNING in content

    def test_audit_event_recorded(self, fake_spark):
        # CA09: a geração (ou falha) cria evento em conversation_events.
        fake_spark.tables[qualified_table("quotes")] = [_quote("paid")]
        fake_spark.tables[qualified_table("quote_items")] = [_quote_item()]
        fake_spark.tables[qualified_table("payments")] = [_payment()]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product()]
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        gd.run(_inputs())
        events = fake_spark.tables.get(qualified_table("conversation_events"), [])
        assert any(
            e.get("event_type") == "document_generated"
            and e.get("tool_name") == "generate_document"
            for e in events
        )

    def test_invalid_document_format(self, fake_spark):
        result = gd.run(_inputs(document_format="pdf"))
        assert result["error_code"] == "INVALID_DOCUMENT_FORMAT"
