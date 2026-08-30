"""Testes da ferramenta check_inventory (docs/specs/check_inventory.md).

Cobrem os critérios de aceite CA01–CA11: disponibilidade, estoque
insuficiente, produto inexistente/inativo, estoque ausente/desatualizado,
entrada inválida, não-alteração do estoque, auditoria e fonte confiável.
"""

from datetime import datetime, timezone

from nexum_sales_assistant.tools import check_inventory as ci
from nexum_sales_assistant.tools._table_ref import qualified_table


def _catalog_row(product_id="PRD-TEMP-001", active=True):
    return {"product_id": product_id, "active": active}


def _inventory_row(
    product_id="PRD-TEMP-001",
    warehouse_id="WH-MAIN",
    available_quantity=42,
    reserved_quantity=0,
    inventory_updated_at="2026-08-26",
):
    # A Gold `gold_product_availability` expõe `inventory_updated_at`
    # (docs/data_model.md §17), consumida por check_inventory.
    return {
        "inventory_id": f"INV-{product_id}",
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "available_quantity": available_quantity,
        "reserved_quantity": reserved_quantity,
        "inventory_updated_at": inventory_updated_at,
    }


class TestCheckInventory:
    def test_available(self, fake_spark):
        # CA01: 42 disponíveis e pedido de 20 → available = true.
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_row()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory_row()]
        result = ci.run(
            {"session_id": "SES-1", "product_id": "PRD-TEMP-001", "quantity_requested": 20}
        )
        assert result["inventory_status"] == "available"
        assert result["available"] is True
        assert result["warehouse_id"] == "WH-MAIN"
        assert result["available_quantity"] == 42

    def test_insufficient_stock(self, fake_spark):
        # CA02: 42 disponíveis e pedido de 50 → available = false.
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_row()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory_row()]
        result = ci.run(
            {"session_id": "SES-1", "product_id": "PRD-TEMP-001", "quantity_requested": 50}
        )
        assert result["inventory_status"] == "insufficient_stock"
        assert result["available"] is False

    def test_product_not_found(self, fake_spark):
        # CA03: product_id inexistente → product_not_found.
        fake_spark.tables[qualified_table("gold_product_catalog")] = []
        result = ci.run(
            {"session_id": "SES-1", "product_id": "PRD-UNKNOWN", "quantity_requested": 20}
        )
        assert result["inventory_status"] == "product_not_found"
        assert result["available"] is False

    def test_inactive_product(self, fake_spark):
        # CA04: produto inativo não confirma disponibilidade.
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_row(active=False)]
        result = ci.run(
            {"session_id": "SES-1", "product_id": "PRD-TEMP-001", "quantity_requested": 20}
        )
        assert result["inventory_status"] == "validation_error"
        assert result["error_code"] == "PRODUCT_INACTIVE"

    def test_inventory_not_found(self, fake_spark):
        # CA05: produto existe, mas sem registro de estoque.
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_row()]
        fake_spark.tables[qualified_table("gold_product_availability")] = []
        result = ci.run(
            {"session_id": "SES-1", "product_id": "PRD-TEMP-001", "quantity_requested": 20}
        )
        assert result["inventory_status"] == "inventory_not_found"
        assert result["available_quantity"] is None

    def test_stale_inventory(self, fake_spark):
        # CA06: atualização superior a 7 dias → stale_inventory.
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_row()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [
            _inventory_row(inventory_updated_at="2026-07-10")
        ]
        result = ci.run(
            {"session_id": "SES-1", "product_id": "PRD-TEMP-001", "quantity_requested": 20}
        )
        assert result["inventory_status"] == "stale_inventory"
        assert result["available"] is False
        assert "older than 7 days" in result["message"]

    def test_invalid_quantity(self, fake_spark):
        # CA07: quantidade <= 0 → erro de validação.
        result = ci.run(
            {"session_id": "SES-1", "product_id": "PRD-TEMP-001", "quantity_requested": 0}
        )
        assert result["inventory_status"] == "validation_error"
        assert result["error_code"] == "INVALID_QUANTITY"

    def test_no_stock_mutation(self, fake_spark):
        # CA08: a consulta não altera os dados de estoque.
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_row()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory_row()]
        before = dict(fake_spark.tables[qualified_table("gold_product_availability")][0])
        ci.run(
            {"session_id": "SES-1", "product_id": "PRD-TEMP-001", "quantity_requested": 20}
        )
        after = fake_spark.tables[qualified_table("gold_product_availability")][0]
        assert before == after

    def test_audit_event_recorded(self, fake_spark):
        # CA10: cada consulta gera evento em conversation_events.
        fake_spark.tables[qualified_table("gold_product_catalog")] = [_catalog_row()]
        fake_spark.tables[qualified_table("gold_product_availability")] = [_inventory_row()]
        ci.run(
            {"session_id": "SES-1", "product_id": "PRD-TEMP-001", "quantity_requested": 20}
        )
        events = fake_spark.tables.get(qualified_table("conversation_events"), [])
        assert any(
            e.get("event_type") == "inventory_checked"
            and e.get("tool_name") == "check_inventory"
            and e.get("tool_reference_id") == "PRD-TEMP-001"
            for e in events
        )

    def test_is_stale_boundary(self):
        now = datetime(2026, 8, 26, tzinfo=timezone.utc)
        assert ci.is_stale("2026-08-10", now=now) is True
        assert ci.is_stale("2026-08-20", now=now) is False
