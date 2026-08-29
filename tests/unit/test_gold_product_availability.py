"""Testes da camada Gold — gold_product_availability (docs/data_model.md §16).

Cobrem schema, cálculo de is_available, combinação somente de registros
válidos, ausência de produto sem estoque e comportamento sem dados, com
dados em memória (sem Spark externo).
"""

import datetime

from nexum_sales_assistant_etl.transformations import gold_product_availability as ga


def _schema_columns():
    return [part.strip().split()[0] for part in ga.SCHEMA.split(", ")]


def _product(product_id="PRD-TEMP-001", quality="valid", **overrides):
    row = {
        "product_id": product_id,
        "sku": f"SKU-{product_id}",
        "product_name": "Sensor de Temperatura Industrial T150",
        "category": "temperature",
        "measurement_unit": "C",
        "active": True,
        "_quality_status": quality,
    }
    row.update(overrides)
    return row


def _inventory(product_id="PRD-TEMP-001", warehouse_id="WH-MAIN",
               available_quantity=42, reserved_quantity=0, quality="valid", **overrides):
    row = {
        "inventory_id": f"INV-{product_id}",
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "available_quantity": available_quantity,
        "reserved_quantity": reserved_quantity,
        "updated_at": datetime.datetime(2026, 8, 26),
        "_quality_status": quality,
    }
    row.update(overrides)
    return row


class TestSchema:
    def test_schema_columns(self):
        assert _schema_columns() == [
            "product_id",
            "sku",
            "product_name",
            "category",
            "measurement_unit",
            "active",
            "warehouse_id",
            "available_quantity",
            "reserved_quantity",
            "inventory_updated_at",
            "is_available",
        ]


class TestAvailability:
    def test_is_available_positive_quantity(self):
        row = ga.build_rows([_product()], [_inventory()])[0]
        assert row["is_available"] is True

    def test_is_available_zero_quantity(self):
        # is_available indica existência de quantidade disponível
        # (docs/data_model.md §16), sem reserva física no MVP.
        row = ga.build_rows([_product()], [_inventory(available_quantity=0)])[0]
        assert row["is_available"] is False

    def test_combines_product_and_inventory_fields(self):
        row = ga.build_rows([_product()], [_inventory()])[0]
        assert row["product_id"] == "PRD-TEMP-001"
        assert row["warehouse_id"] == "WH-MAIN"
        assert row["available_quantity"] == 42
        assert row["reserved_quantity"] == 0
        assert row["inventory_updated_at"] == datetime.datetime(2026, 8, 26)


class TestCombinationRules:
    def test_invalid_inventory_excluded(self):
        rows = ga.build_rows([_product()], [_inventory(quality="invalid:product_not_found")])
        assert rows == []

    def test_inventory_of_invalid_product_excluded(self):
        rows = ga.build_rows(
            [_product(quality="invalid:price_not_positive")], [_inventory()]
        )
        assert rows == []

    def test_product_without_inventory_absent(self):
        # Produto sem registro de estoque fica ausente da Gold, para que
        # check_inventory retorne inventory_not_found (SPEC §11).
        rows = ga.build_rows([_product("A"), _product("B")], [_inventory("A")])
        assert [r["product_id"] for r in rows] == ["A"]

    def test_empty_inputs(self):
        assert ga.build_rows([], []) == []
