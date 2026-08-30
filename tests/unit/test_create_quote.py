"""Testes da ferramenta create_quote (docs/specs/create_quote.md).

Cobrem os critérios de aceite CA01–CA13: criação válida em `draft`,
itens, cálculo de subtotal/total, congelamento de preço, cliente
inexistente, produto inativo, estoque insuficiente, ausência de reserva,
aprovação obrigatória e auditoria.
"""

from nexum_sales_assistant.tools import create_quote as cq
from nexum_sales_assistant.tools._table_ref import qualified_table


def _catalog_product(
    product_id="PRD-TEMP-001",
    price=780.00,
    active=True,
    technical_specs="precisao:+/-0.5C",
):
    return {
        "product_id": product_id,
        "sku": f"SKU-{product_id}",
        "product_name": f"Produto {product_id}",
        "category": "temperature",
        "description": "Descrição",
        "use_cases": "monitoramento de máquinas",
        "technical_specs": technical_specs,
        "measurement_unit": "C",
        "min_operating_value": -20,
        "max_operating_value": 180,
        "price": price,
        "currency": "BRL",
        "lead_time_days": 3,
        "active": active,
    }


def _inventory(
    product_id="PRD-TEMP-001", available_quantity=42, inventory_updated_at="2026-08-26"
):
    # A Gold `gold_product_availability` expõe `inventory_updated_at`
    # (docs/data_model.md §16), consumida por check_inventory.
    return {
        "inventory_id": f"INV-{product_id}",
        "product_id": product_id,
        "warehouse_id": "WH-MAIN",
        "available_quantity": available_quantity,
        "reserved_quantity": 0,
        "inventory_updated_at": inventory_updated_at,
    }


def _inputs(items=None):
    return {
        "session_id": "SES-1",
        "customer_id": "C0001",
        "requested_by": "assistant",
        "items": items or [{"product_id": "PRD-TEMP-001", "quantity": 20}],
    }


class TestCreateQuote:
    def test_creates_draft_quote(self, fake_spark):
        # CA01: cliente válido + produto ativo com estoque → cotação `draft`.
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory()]
        result = cq.run(_inputs())
        assert result["quote_status"] == "created"
        assert result["status"] == "draft"
        assert result["next_action"] == "request_human_approval"
        quote = fake_spark.tables[qualified_table("quotes")][0]
        assert quote["status"] == "draft"
        assert quote["customer_id"] == "C0001"
        assert quote["payment_status"] == "not_started"
        assert result["items"][0]["subtotal"] == 15600.00

    def test_total_equals_sum_of_subtotals(self, fake_spark):
        # CA03/CA04: subtotal = quantidade * preço; total = soma dos subtotais.
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [
            _catalog_product(),
            _catalog_product(product_id="PRD-TEMP-002", price=450.00),
        ]
        fake_spark.tables[qualified_table("gold_product_availability")] = [
            _inventory(),
            _inventory(product_id="PRD-TEMP-002", available_quantity=100),
        ]
        result = cq.run(
            _inputs(
                [
                    {"product_id": "PRD-TEMP-001", "quantity": 20},
                    {"product_id": "PRD-TEMP-002", "quantity": 2},
                ]
            )
        )
        assert result["total_amount"] == 15600.00 + 900.00
        subtotals = [item["subtotal"] for item in result["items"]]
        assert subtotals == [15600.00, 900.00]

    def test_freezes_price_in_items(self, fake_spark):
        # CA05: unit_price copiado do catálogo e persistido nos itens.
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product(price=780.00)]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory()]
        result = cq.run(_inputs())
        assert result["items"][0]["unit_price"] == 780.00
        item_row = fake_spark.tables[qualified_table("quote_items")][0]
        assert item_row["unit_price"] == 780.00
        assert item_row["subtotal"] == 15600.00

    def test_customer_not_found(self, fake_spark):
        # CA06: cliente inexistente → rejeição, sem criar cotação.
        fake_spark.tables[qualified_table("silver_companies")] = []
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory()]
        result = cq.run(_inputs())
        assert result["quote_status"] == "validation_error"
        assert result["error_code"] == "CUSTOMER_NOT_FOUND"
        assert fake_spark.tables.get(qualified_table("quotes"), []) == []

    def test_inactive_product_rejected(self, fake_spark):
        # CA07: produto inativo → rejeição.
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product(active=False)]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory()]
        result = cq.run(_inputs())
        assert result["error_code"] == "PRODUCT_NOT_AVAILABLE"

    def test_insufficient_stock(self, fake_spark):
        # CA08: estoque insuficiente → rejeição com o item problemático.
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [
            _inventory(available_quantity=8)
        ]
        result = cq.run(_inputs())
        assert result["quote_status"] == "inventory_validation_error"
        assert result["error_code"] == "INSUFFICIENT_STOCK"
        assert result["items"][0]["available_quantity"] == 8
        assert fake_spark.tables.get(qualified_table("quotes"), []) == []

    def test_no_stock_reservation(self, fake_spark):
        # CA09: a criação não altera available/reserved_quantity.
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory()]
        before = dict(fake_spark.tables[qualified_table("gold_product_availability")][0])
        cq.run(_inputs())
        after = fake_spark.tables[qualified_table("gold_product_availability")][0]
        assert before == after

    def test_never_sets_approval_fields(self, fake_spark):
        # CA10: a cotação criada não avança para approved/paid/completed
        # e não possui campos de aprovação preenchidos.
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory()]
        result = cq.run(_inputs())
        assert result["status"] == "draft"
        quote = fake_spark.tables[qualified_table("quotes")][0]
        assert quote["approved_by"] is None
        assert quote["approved_at"] is None
        assert quote["status"] == "draft"

    def test_audit_event_recorded(self, fake_spark):
        # CA11: a criação gera evento em conversation_events.
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_product()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory()]
        result = cq.run(_inputs())
        events = fake_spark.tables.get(qualified_table("conversation_events"), [])
        assert any(
            e.get("event_type") == "quote_created"
            and e.get("tool_reference_id") == result["quote_id"]
            for e in events
        )

    def test_validation_duplicate_product(self, fake_spark):
        result = cq.run(
            _inputs(
                [
                    {"product_id": "PRD-TEMP-001", "quantity": 1},
                    {"product_id": "PRD-TEMP-001", "quantity": 2},
                ]
            )
        )
        assert result["error_code"] == "DUPLICATE_PRODUCT"

    def test_validation_valid_until_before_creation(self, fake_spark):
        result = cq.run(
            {
                "session_id": "SES-1",
                "customer_id": "C0001",
                "requested_by": "assistant",
                "items": [{"product_id": "PRD-TEMP-001", "quantity": 1}],
                "valid_until": "2020-01-01",
            }
        )
        assert result["error_code"] == "INVALID_VALID_UNTIL"
