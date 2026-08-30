"""Testes da camada Silver — silver_products (ADR-005; prompts/02-silver.md).

Cobrem schema, tipagem, regras de qualidade do ADR-005 (preço, unidade,
faixa, moeda, prazo, active), unicidade de chaves, campos obrigatórios e
preservação da origem, com dados em memória (sem Spark externo).
"""

import datetime
from decimal import Decimal

from nexum_sales_assistant_etl.transformations import silver_products as sp


def _schema_columns():
    return [part.strip().split()[0] for part in sp.SCHEMA.split(", ")]


def _raw_row(
    product_id="PRD-TEMP-001",
    sku="NEX-TEMP-001",
    product_name="Sensor de Temperatura Industrial T150",
    category="temperature",
    description="Sensor industrial",
    use_cases="monitoramento de máquinas",
    technical_specs="precisao:+/-0.5C|saida:4-20mA|material:aco_inox",
    measurement_unit="C",
    min_operating_value="-20",
    max_operating_value="180",
    price="780.00",
    currency="BRL",
    lead_time_days="3",
    active="true",
    **overrides,
):
    row = {
        "product_id": product_id,
        "sku": sku,
        "product_name": product_name,
        "category": category,
        "description": description,
        "use_cases": use_cases,
        "technical_specs": technical_specs,
        "measurement_unit": measurement_unit,
        "min_operating_value": min_operating_value,
        "max_operating_value": max_operating_value,
        "price": price,
        "currency": currency,
        "lead_time_days": lead_time_days,
        "active": active,
        "_ingestion_timestamp": datetime.datetime(2026, 8, 26, 12, 0, 0),
        "_source_file": "products.csv",
        "_source_system": "fixtures",
    }
    row.update(overrides)
    return row


def _one(**overrides):
    return sp.transform_rows([_raw_row(**overrides)])[0]


class TestSchema:
    def test_schema_columns(self):
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
            "_quality_status",
            "_ingestion_timestamp",
            "_source_file",
            "_source_system",
        ]


class TestValidRows:
    def test_valid_product_with_types(self):
        row = _one()
        assert row["_quality_status"] == "valid"
        # Valores monetários com tipo e precisão adequados (DECIMAL(10,2)).
        assert row["price"] == Decimal("780.00")
        assert row["min_operating_value"] == Decimal("-20.00")
        assert row["max_operating_value"] == Decimal("180.00")
        assert row["lead_time_days"] == 3
        assert row["active"] is True

    def test_active_false_is_valid(self):
        row = _one(active="false")
        assert row["_quality_status"] == "valid"
        assert row["active"] is False

    def test_origin_preserved(self):
        row = _one()
        assert row["_ingestion_timestamp"] == datetime.datetime(2026, 8, 26, 12, 0, 0)
        assert row["_source_file"] == "products.csv"
        assert row["_source_system"] == "fixtures"


class TestQualityRules:
    def test_negative_price(self):
        # Caso PRD-TEMP-005 dos fixtures: preço -50.00 (ADR-005: preço > 0).
        row = _one(price="-50.00")
        assert "price_not_positive" in row["_quality_status"]

    def test_incompatible_unit(self):
        # Caso PRD-TEMP-006: unidade F para categoria temperature.
        row = _one(measurement_unit="F")
        assert "measurement_unit_incompatible" in row["_quality_status"]

    def test_pressure_accepts_bar_and_psi(self):
        # Unidades compatíveis por categoria (CATEGORY_UNITS documentada
        # em search_products.py): pressure aceita bar e psi.
        assert _one(category="pressure", measurement_unit="bar")["_quality_status"] == "valid"
        assert _one(category="pressure", measurement_unit="psi")["_quality_status"] == "valid"

    def test_missing_technical_specs(self):
        # Caso PRD-PRES-005: especificações essenciais ausentes.
        row = _one(technical_specs="")
        assert "technical_specs_required" in row["_quality_status"]

    def test_invalid_category(self):
        row = _one(category="humidity")
        assert "category_invalid" in row["_quality_status"]

    def test_range_inconsistent(self):
        row = _one(min_operating_value="10", max_operating_value="5")
        assert "operating_range_inconsistent" in row["_quality_status"]

    def test_range_partial(self):
        # Apenas um limite presente: faixa inconsistente (ADR-005).
        row = _one(min_operating_value="", max_operating_value="180")
        assert "operating_range_inconsistent" in row["_quality_status"]

    def test_currency_not_brl(self):
        row = _one(currency="USD")
        assert "currency_invalid" in row["_quality_status"]

    def test_negative_lead_time(self):
        row = _one(lead_time_days="-1")
        assert "lead_time_days_negative" in row["_quality_status"]

    def test_invalid_price_string(self):
        row = _one(price="abc")
        assert "price_invalid" in row["_quality_status"]

    def test_invalid_active_value(self):
        row = _one(active="xyz")
        assert "active_invalid" in row["_quality_status"]


class TestRequiredFields:
    def test_missing_required_string_fields(self):
        row = _one(product_id="", sku="", product_name="", category="",
                   description="", use_cases="", technical_specs="",
                   measurement_unit="", currency="")
        for field in sp.REQUIRED_STRINGS:
            assert f"{field}_required" in row["_quality_status"]

    def test_missing_price(self):
        row = _one(price="")
        assert "price_required" in row["_quality_status"]

    def test_missing_lead_time(self):
        row = _one(lead_time_days="")
        assert "lead_time_days_required" in row["_quality_status"]

    def test_missing_active(self):
        row = _one(active="")
        assert "active_required" in row["_quality_status"]


class TestUniqueness:
    def test_duplicate_product_id_flagged(self):
        rows = sp.transform_rows([_raw_row(), _raw_row()])
        assert all("duplicate_product_id" in r["_quality_status"] for r in rows)

    def test_duplicate_sku_flagged(self):
        rows = sp.transform_rows(
            [_raw_row(product_id="PRD-A", sku="SKU-1"), _raw_row(product_id="PRD-B", sku="SKU-1")]
        )
        assert all("duplicate_sku" in r["_quality_status"] for r in rows)
