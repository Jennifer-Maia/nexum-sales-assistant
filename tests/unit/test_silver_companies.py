"""Testes da camada Silver — silver_companies (ADR-002; prompts/02-silver.md).

Cobrem schema, campos obrigatórios, deduplicação, normalização,
registros inválidos e preservação da origem, com dados em memória
(sem Spark externo, sem API remota).
"""

import datetime

from nexum_sales_assistant_etl.transformations import silver_companies as sc


def _schema_columns():
    return [part.strip().split()[0] for part in sc.SCHEMA.split(", ")]


def _raw_row(company_id="C0001", company_name="Metalúrgica Ferrovale Ltda",
             industry="metalurgia", region="Sudeste", **overrides):
    row = {
        "company_id": company_id,
        "company_name": company_name,
        "industry": industry,
        "region": region,
        "_ingestion_timestamp": datetime.datetime(2026, 8, 26, 12, 0, 0),
        "_source_file": "companies.csv",
        "_source_system": "fixtures",
    }
    row.update(overrides)
    return row


class TestSchema:
    def test_schema_columns(self):
        assert _schema_columns() == [
            "company_id",
            "company_name",
            "industry",
            "region",
            "_quality_status",
            "_ingestion_timestamp",
            "_source_file",
            "_source_system",
        ]


class TestValidRows:
    def test_valid_row(self):
        rows = sc.transform_rows([_raw_row()])
        assert len(rows) == 1
        assert rows[0]["_quality_status"] == "valid"
        assert rows[0]["company_id"] == "C0001"

    def test_normalization_trims_fields(self):
        rows = sc.transform_rows(
            [_raw_row(company_name="  Fiação Santa Amália  ", industry="têxtil ", region=" Sul")]
        )
        assert rows[0]["company_name"] == "Fiação Santa Amália"
        assert rows[0]["industry"] == "têxtil"
        assert rows[0]["region"] == "Sul"

    def test_industry_and_region_optional(self):
        # ADR-002: tratar valores nulos; apenas company_id/name obrigatórios.
        rows = sc.transform_rows([_raw_row(industry=None, region="")])
        assert rows[0]["_quality_status"] == "valid"
        assert rows[0]["industry"] is None
        assert rows[0]["region"] is None

    def test_origin_preserved(self):
        rows = sc.transform_rows([_raw_row()])
        assert rows[0]["_ingestion_timestamp"] == datetime.datetime(2026, 8, 26, 12, 0, 0)
        assert rows[0]["_source_file"] == "companies.csv"
        assert rows[0]["_source_system"] == "fixtures"


class TestRequiredFields:
    def test_missing_company_id(self):
        rows = sc.transform_rows([_raw_row(company_id="")])
        assert "company_id_required" in rows[0]["_quality_status"]

    def test_missing_company_name(self):
        rows = sc.transform_rows([_raw_row(company_name=None)])
        assert "company_name_required" in rows[0]["_quality_status"]

    def test_multiple_problems_joined(self):
        rows = sc.transform_rows([_raw_row(company_id="", company_name="")])
        assert rows[0]["_quality_status"] == (
            "invalid:company_id_required;company_name_required"
        )


class TestDeduplication:
    def test_duplicate_company_id_flagged(self):
        # Linhas duplicadas são sinalizadas, não corrigidas (ADR-002/ADR-005).
        rows = sc.transform_rows([_raw_row(), _raw_row()])
        assert all("duplicate_company_id" in r["_quality_status"] for r in rows)

    def test_distinct_ids_not_flagged(self):
        rows = sc.transform_rows([_raw_row("C0001"), _raw_row("C0002")])
        assert all(r["_quality_status"] == "valid" for r in rows)
