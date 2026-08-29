"""Testes das regras puras das ferramentas do Nexum Sales Assistant.

Cada teste cobre uma regra documentada na SPEC correspondente em
docs/specs/. Não exige Spark: somente validações, cálculos e funções
puras.
"""

from datetime import datetime, timedelta, timezone

from nexum_sales_assistant.tools import (
    check_inventory as ci,
    create_quote as cq,
    generate_document as gd,
    request_human_approval as rha,
    search_products as sp,
    simulate_payment as spay,
)


class TestSearchProducts:
    def test_missing_session_id(self):
        result = sp.validate_input({})
        assert result["search_status"] == "validation_error"
        assert result["error_code"] == "MISSING_SESSION_ID"

    def test_invalid_category(self):
        result = sp.validate_input({"session_id": "SES-1", "category": "light"})
        assert result["error_code"] == "INVALID_CATEGORY"

    def test_inverted_range(self):
        result = sp.validate_input(
            {
                "session_id": "SES-1",
                "category": "temperature",
                "min_required_value": 150,
                "max_required_value": 0,
            }
        )
        assert result["error_code"] == "INVALID_REQUIRED_RANGE"
        assert "less than or equal" in result["message"]

    def test_limit_bounds(self):
        assert (
            sp.validate_input({"session_id": "SES-1", "category": "temperature", "limit": 0})[
                "error_code"
            ]
            == "INVALID_LIMIT"
        )
        assert (
            sp.validate_input({"session_id": "SES-1", "category": "temperature", "limit": 11})[
                "error_code"
            ]
            == "INVALID_LIMIT"
        )

    def test_unit_incompatible_with_category(self):
        result = sp.validate_input(
            {"session_id": "SES-1", "category": "temperature", "measurement_unit": "bar"}
        )
        assert result["error_code"] == "INVALID_UNIT"

    def test_normalize_unit(self):
        assert sp.normalize_unit("°C") == "C"
        assert sp.normalize_unit("C") == "C"
        assert sp.normalize_unit("bar") == "bar"
        assert sp.normalize_unit(None) is None

    def test_covers_range(self):
        assert sp.covers_range(0, 150, -20, 180) is True
        assert sp.covers_range(0, 150, 20, 100) is False
        assert sp.covers_range(0, 150, None, 180) is False

    def test_ordering_by_lead_time_price_product_id(self):
        products = [
            {"product_id": "P3", "lead_time_days": 5, "price": 10.0},
            {"product_id": "P1", "lead_time_days": 3, "price": 100.0},
            {"product_id": "P2", "lead_time_days": 3, "price": 50.0},
        ]
        ordered = sp.sort_products(products)
        # Menor prazo primeiro; empate resolvido por menor preço (SPEC §6).
        assert [p["product_id"] for p in ordered] == ["P2", "P1", "P3"]


class TestCheckInventory:
    def test_availability_rule(self):
        assert ci.decide_availability(42, 20) is True
        assert ci.decide_availability(42, 50) is False
        assert ci.decide_availability(20, 20) is True

    def test_stale_beyond_seven_days(self):
        now = datetime(2026, 8, 26, tzinfo=timezone.utc)
        assert ci.is_stale(datetime(2026, 8, 10, tzinfo=timezone.utc), now=now) is True
        assert ci.is_stale(datetime(2026, 8, 20, tzinfo=timezone.utc), now=now) is False

    def test_invalid_quantity(self):
        result = ci.validate_input(
            {"session_id": "SES-1", "product_id": "P1", "quantity_requested": 0}
        )
        assert result["error_code"] == "INVALID_QUANTITY"
        assert result["message"] == "quantity_requested must be greater than zero"


class TestCreateQuote:
    def test_invalid_currency(self):
        result = cq.validate_input(
            {"session_id": "SES-1", "customer_id": "C1", "requested_by": "assistant",
             "items": [{"product_id": "P1", "quantity": 1}], "currency": "USD"}
        )
        assert result["error_code"] == "INVALID_CURRENCY"

    def test_duplicate_product(self):
        result = cq.validate_input(
            {
                "session_id": "SES-1",
                "customer_id": "C1",
                "requested_by": "assistant",
                "items": [
                    {"product_id": "P1", "quantity": 1},
                    {"product_id": "P1", "quantity": 2},
                ],
            }
        )
        assert result["error_code"] == "DUPLICATE_PRODUCT"

    def test_quantity_must_be_positive(self):
        result = cq.validate_input(
            {"session_id": "SES-1", "customer_id": "C1", "requested_by": "assistant",
             "items": [{"product_id": "P1", "quantity": 0}]}
        )
        assert result["error_code"] == "INVALID_QUANTITY"

    def test_valid_until_before_creation(self):
        result = cq.validate_input(
            {
                "session_id": "SES-1",
                "customer_id": "C1",
                "requested_by": "assistant",
                "items": [{"product_id": "P1", "quantity": 1}],
                "valid_until": "2020-01-01",
            }
        )
        assert result["error_code"] == "INVALID_VALID_UNTIL"

    def test_build_items_freezes_price_and_subtotal(self):
        items = cq.build_items(
            [{"product_id": "P1", "quantity": 20}],
            {"P1": 780.00},
        )
        assert items == [
            {"product_id": "P1", "quantity": 20, "unit_price": 780.00, "subtotal": 15600.00}
        ]

    def test_compute_total(self):
        items = [{"subtotal": 15600.00}, {"subtotal": 400.00}]
        assert cq.compute_total(items) == 16000.00

    def test_default_valid_until_seven_days(self):
        created_at = datetime(2026, 8, 26, tzinfo=timezone.utc)
        assert cq.default_valid_until(created_at) == "2026-09-02"


class TestRequestHumanApproval:
    def test_invalid_operation(self):
        result = rha.run({"operation": "bogus", "session_id": "SES-1"})
        assert result["error_code"] == "INVALID_OPERATION"

    def test_unauthorized_approver(self):
        result = rha.run(
            {
                "operation": "resolve",
                "session_id": "SES-1",
                "approval_id": "APR-1",
                "decision": "approved",
                "resolved_by": "assistant",
            }
        )
        assert result["error_code"] == "UNAUTHORIZED_APPROVER"

    def test_rejection_requires_reason(self):
        result = rha.run(
            {
                "operation": "resolve",
                "session_id": "SES-1",
                "approval_id": "APR-1",
                "decision": "rejected",
                "resolved_by": "vendor-001",
            }
        )
        assert result["error_code"] == "MISSING_REJECTION_REASON"

    def test_invalid_decision(self):
        result = rha.run(
            {
                "operation": "resolve",
                "session_id": "SES-1",
                "approval_id": "APR-1",
                "decision": "maybe",
                "resolved_by": "vendor-001",
            }
        )
        assert result["error_code"] == "INVALID_DECISION"


class TestSimulatePayment:
    def test_forbidden_simulation_result(self):
        result = spay._validate(
            {"session_id": "SES-1", "quote_id": "QTE-1", "requested_by": "vendor-001",
             "simulation_result": "paid"}
        )
        assert result["error_code"] == "INVALID_SIMULATION_RESULT"

    def test_default_simulation_result_success(self):
        assert spay.default_simulation_result({}) == "success"


class TestGenerateDocument:
    def test_invalid_format(self):
        result = gd._validate(
            {"session_id": "SES-1", "quote_id": "QTE-1", "requested_by": "system",
             "document_format": "pdf"}
        )
        assert result["error_code"] == "INVALID_DOCUMENT_FORMAT"

    def test_html_content_contains_mandatory_warnings(self):
        content = gd.build_document_content(
            "DOC-1",
            {
                "quote_id": "QTE-1",
                "customer_id": "C1",
                "total_amount": 15600.00,
                "currency": "BRL",
            },
            [
                {
                    "product_id": "P1",
                    "sku": "NEX-TEMP-001",
                    "product_name": "Sensor T150",
                    "quantity": 20,
                    "unit_price": 780.00,
                    "subtotal": 15600.00,
                    "currency": "BRL",
                }
            ],
            {"payment_id": "PAY-1"},
            "Nexum Cliente Ltda",
        )
        assert gd.DOCUMENT_WARNING in content
        assert gd.FINAL_WARNING in content
        assert "DOC-1" in content
        assert "Nexum Cliente Ltda" in content

    def test_txt_content_contains_mandatory_warnings(self):
        content = gd.build_document_content(
            "DOC-1",
            {"quote_id": "QTE-1", "customer_id": "C1", "total_amount": 10.0, "currency": "BRL"},
            [],
            {"payment_id": "PAY-1"},
            None,
            document_format="txt",
        )
        assert gd.DOCUMENT_WARNING in content
        assert gd.FINAL_WARNING in content
