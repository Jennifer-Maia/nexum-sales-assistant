"""Testes da camada Gold — gold_quote_summary (docs/data_model.md §16; ADR-002).

Cobrem schema, granularidade por quote_id, contagem de itens, quantidade
total, status da aprovação, customer_name canônico e comportamento sem
dados, com dados em memória (sem Spark externo).
"""

import datetime
from decimal import Decimal

from nexum_sales_assistant_etl.transformations import gold_quote_summary as gq


def _schema_columns():
    return [part.strip().split()[0] for part in gq.SCHEMA.split(", ")]


def _quote(quote_id="QTE-0001", customer_id="C0001", status="draft", **overrides):
    row = {
        "quote_id": quote_id,
        "customer_id": customer_id,
        "session_id": "SES-1",
        "status": status,
        "total_amount": Decimal("1620.00"),
        "currency": "BRL",
        "created_at": datetime.datetime(2026, 8, 27, 10, 0, 0),
        "approved_at": None,
        "approved_by": None,
        "rejection_reason": None,
        "payment_status": "not_started",
        "document_id": None,
    }
    row.update(overrides)
    return row


def _item(quote_item_id="QTI-1", quote_id="QTE-0001", product_id="PRD-TEMP-001",
          quantity=2, **overrides):
    row = {
        "quote_item_id": quote_item_id,
        "quote_id": quote_id,
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": Decimal("810.00"),
        "subtotal": Decimal("1620.00"),
    }
    row.update(overrides)
    return row


def _approval(approval_id="APR-1", quote_id="QTE-0001", status="approved",
              created_at=None, **overrides):
    row = {
        "approval_id": approval_id,
        "quote_id": quote_id,
        "requested_by": "assistant",
        "resolved_by": None,
        "status": status,
        "reason": None,
        "created_at": created_at or datetime.datetime(2026, 8, 27, 11, 0, 0),
        "resolved_at": None,
    }
    row.update(overrides)
    return row


def _company(company_id="C0001", company_name="Metalúrgica Ferrovale Ltda", **overrides):
    row = {
        "company_id": company_id,
        "company_name": company_name,
        "industry": "metalurgia",
        "region": "Sudeste",
        "_quality_status": "valid",
    }
    row.update(overrides)
    return row


class TestSchema:
    def test_schema_columns(self):
        assert _schema_columns() == [
            "quote_id",
            "customer_id",
            "customer_name",
            "status",
            "total_amount",
            "currency",
            "created_at",
            "approved_at",
            "approved_by",
            "payment_status",
            "item_count",
            "total_quantity",
            "approval_status",
        ]


class TestGranularity:
    def test_one_row_per_quote(self):
        rows = gq.build_rows([_quote("A"), _quote("B")], [], [], [])
        assert [r["quote_id"] for r in rows] == ["A", "B"]

    def test_quote_without_id_ignored(self):
        rows = gq.build_rows([_quote(quote_id=None)], [], [], [])
        assert rows == []


class TestItems:
    def test_item_count_and_total_quantity(self):
        items = [_item("QTI-1"), _item("QTI-2", quantity=3)]
        row = gq.build_rows([_quote()], items, [], [])[0]
        assert row["item_count"] == 2
        assert row["total_quantity"] == 5

    def test_without_items_table(self):
        # Tabela quote_items ausente: contagens zeradas, nada inventado.
        row = gq.build_rows([_quote()], [], [], [])[0]
        assert row["item_count"] == 0
        assert row["total_quantity"] == 0

    def test_items_of_other_quotes_ignored(self):
        row = gq.build_rows([_quote("A")], [_item(quote_id="B")], [], [])[0]
        assert row["item_count"] == 0


class TestApproval:
    def test_approval_status_from_approvals(self):
        row = gq.build_rows([_quote()], [], [_approval(status="approved")], [])[0]
        assert row["approval_status"] == "approved"

    def test_latest_approval_wins(self):
        approvals = [
            _approval("APR-1", status="pending", created_at=datetime.datetime(2026, 8, 27, 10, 0)),
            _approval("APR-2", status="rejected", created_at=datetime.datetime(2026, 8, 27, 12, 0)),
        ]
        row = gq.build_rows([_quote()], [], approvals, [])[0]
        assert row["approval_status"] == "rejected"

    def test_without_approvals_table(self):
        row = gq.build_rows([_quote()], [], [], [])[0]
        assert row["approval_status"] is None


class TestCustomer:
    def test_customer_name_from_canonical_companies(self):
        row = gq.build_rows([_quote()], [], [], [_company()])[0]
        assert row["customer_name"] == "Metalúrgica Ferrovale Ltda"
        assert row["customer_id"] == "C0001"

    def test_customer_without_company(self):
        row = gq.build_rows([_quote(customer_id="C9999")], [], [], [_company()])[0]
        assert row["customer_name"] is None


class TestNoInvention:
    def test_only_schema_columns_returned(self):
        row = gq.build_rows([_quote()], [], [], [])[0]
        assert set(row.keys()) == set(_schema_columns())

    def test_empty_quotes(self):
        assert gq.build_rows([], [], [], []) == []
