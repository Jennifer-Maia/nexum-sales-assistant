"""Testes da camada Silver — silver_inventory (ADR-005; prompts/02-silver.md).

Cobrem schema, tipagem, quantidades não negativas, integridade
referencial com silver_products, unicidade de chaves, timestamps válidos
e preservação da origem, com dados em memória (sem Spark externo).
"""

import datetime

from nexum_sales_assistant_etl.transformations import silver_inventory as si


def _schema_columns():
    return [part.strip().split()[0] for part in si.SCHEMA.split(", ")]


def _raw_row(
    inventory_id="INV-0001",
    product_id="PRD-TEMP-001",
    warehouse_id="WH-MAIN",
    available_quantity="42",
    reserved_quantity="0",
    updated_at="2026-08-26",
    **overrides,
):
    row = {
        "inventory_id": inventory_id,
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "available_quantity": available_quantity,
        "reserved_quantity": reserved_quantity,
        "updated_at": updated_at,
        "_ingestion_timestamp": datetime.datetime(2026, 8, 26, 12, 0, 0),
        "_source_file": "inventory.csv",
        "_source_system": "fixtures",
    }
    row.update(overrides)
    return row


def _one(product_ids=None, **overrides):
    product_ids = {"PRD-TEMP-001"} if product_ids is None else product_ids
    return si.transform_rows([_raw_row(**overrides)], product_ids)[0]


class TestSchema:
    def test_schema_columns(self):
        assert _schema_columns() == [
            "inventory_id",
            "product_id",
            "warehouse_id",
            "available_quantity",
            "reserved_quantity",
            "updated_at",
            "_quality_status",
            "_ingestion_timestamp",
            "_source_file",
            "_source_system",
        ]


class TestValidRows:
    def test_valid_row_with_types(self):
        row = _one()
        assert row["_quality_status"] == "valid"
        assert row["available_quantity"] == 42
        assert row["reserved_quantity"] == 0
        assert row["updated_at"] == datetime.datetime(2026, 8, 26)

    def test_origin_preserved(self):
        row = _one()
        assert row["_ingestion_timestamp"] == datetime.datetime(2026, 8, 26, 12, 0, 0)
        assert row["_source_file"] == "inventory.csv"
        assert row["_source_system"] == "fixtures"


class TestQuantities:
    def test_negative_available_quantity(self):
        row = _one(available_quantity="-1")
        assert "available_quantity_negative" in row["_quality_status"]

    def test_negative_reserved_quantity(self):
        row = _one(reserved_quantity="-1")
        assert "reserved_quantity_negative" in row["_quality_status"]

    def test_unparseable_available_quantity(self):
        row = _one(available_quantity="abc")
        assert "available_quantity_invalid" in row["_quality_status"]

    def test_missing_quantities(self):
        row = _one(available_quantity="", reserved_quantity="")
        assert "available_quantity_required" in row["_quality_status"]
        assert "reserved_quantity_required" in row["_quality_status"]


class TestReferentialIntegrity:
    def test_product_id_must_exist(self):
        # product_id inexistente em silver_products: sinalizado, e nenhum
        # produto é inventado para corrigir o estoque (ADR-005).
        row = _one(product_ids={"PRD-OUTRO"}, product_id="PRD-INEXISTENTE")
        assert "product_not_found" in row["_quality_status"]

    def test_existing_product_not_flagged(self):
        row = _one(product_ids={"PRD-TEMP-001", "PRD-TEMP-002"}, product_id="PRD-TEMP-002")
        assert "product_not_found" not in row["_quality_status"]


class TestUniqueness:
    def test_duplicate_inventory_id_flagged(self):
        rows = si.transform_rows([_raw_row(), _raw_row()], {"PRD-TEMP-001"})
        assert all("duplicate_inventory_id" in r["_quality_status"] for r in rows)

    def test_duplicate_product_warehouse_flagged(self):
        # Ausência de duplicidade de produto e depósito (ADR-005).
        rows = si.transform_rows(
            [_raw_row("INV-1"), _raw_row("INV-2")], {"PRD-TEMP-001"}
        )
        assert all("duplicate_product_warehouse" in r["_quality_status"] for r in rows)


class TestTimestamps:
    def test_invalid_updated_at(self):
        row = _one(updated_at="2026-13-99")
        assert "updated_at_invalid" in row["_quality_status"]

    def test_missing_updated_at(self):
        row = _one(updated_at="")
        assert "updated_at_invalid" in row["_quality_status"]
