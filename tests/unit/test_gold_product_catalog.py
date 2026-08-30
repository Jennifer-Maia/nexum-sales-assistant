"""Testes da camada Gold — gold_product_catalog (docs/data_model.md §17).

Cobrem schema, exclusão de produtos inválidos, permanência de inativos
válidos, ausência de dados inventados e comportamento sem dados, com
dados em memória (sem Spark externo).
"""

from decimal import Decimal

from nexum_sales_assistant_etl.transformations import gold_product_catalog as gc


def _schema_columns():
    return [part.strip().split()[0] for part in gc.SCHEMA.split(", ")]


def _product(product_id="PRD-TEMP-001", active=True, quality="valid", **overrides):
    row = {
        "product_id": product_id,
        "sku": f"SKU-{product_id}",
        "product_name": "Sensor de Temperatura Industrial T150",
        "category": "temperature",
        "description": "Sensor industrial",
        "use_cases": "monitoramento de máquinas",
        "technical_specs": "precisao:+/-0.5C",
        "measurement_unit": "C",
        "min_operating_value": Decimal("-20.00"),
        "max_operating_value": Decimal("180.00"),
        "price": Decimal("780.00"),
        "currency": "BRL",
        "lead_time_days": 3,
        "active": active,
        "_quality_status": quality,
    }
    row.update(overrides)
    return row


class TestSchema:
    def test_schema_columns(self):
        # Campos exatamente conforme docs/data_model.md §17.
        assert _schema_columns() == [
            "product_id",
            "sku",
            "product_name",
            "category",
            "description",
            "use_cases",
            "technical_specs",
            "measurement_unit",
            "min_operating_value",
            "max_operating_value",
            "price",
            "currency",
            "lead_time_days",
            "active",
        ]


class TestExclusions:
    def test_invalid_products_excluded(self):
        rows = gc.build_rows([_product(), _product("PRD-X", quality="invalid:price_not_positive")])
        assert [r["product_id"] for r in rows] == ["PRD-TEMP-001"]

    def test_inactive_valid_product_kept(self):
        # Produto válido inativo permanece no catálogo; a exclusão de
        # inativos da recomendação é da ferramenta (SPEC search_products §5.1).
        rows = gc.build_rows([_product("PRD-TEMP-004", active=False)])
        assert len(rows) == 1
        assert rows[0]["active"] is False


class TestNoInvention:
    def test_only_catalog_columns_returned(self):
        # Nenhuma coluna além do contrato da Gold (docs/data_model.md §17).
        row = gc.build_rows([_product()])[0]
        assert set(row.keys()) == set(gc.CATALOG_COLUMNS)

    def test_output_is_subset_of_input(self):
        rows = gc.build_rows([_product("A"), _product("B")])
        assert {r["product_id"] for r in rows} == {"A", "B"}

    def test_empty_input(self):
        assert gc.build_rows([]) == []
