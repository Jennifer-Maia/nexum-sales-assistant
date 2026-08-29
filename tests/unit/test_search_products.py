"""Testes da ferramenta search_products (docs/specs/search_products.md).

Cobrem os critérios de aceite CA01–CA10: categoria, produtos ativos,
compatibilidade de faixa, limite de resultados, ausência de resultados,
dados reais do catálogo, auditoria e reprodutibilidade.
"""

from nexum_sales_assistant.tools import search_products as sp


def _product(**overrides):
    row = {
        "product_id": "PRD-TEMP-001",
        "sku": "NEX-TEMP-001",
        "product_name": "Sensor de Temperatura Industrial T150",
        "category": "temperature",
        "description": "Sensor industrial para monitoramento contínuo",
        "use_cases": "monitoramento de máquinas|fornos industriais",
        "technical_specs": "precisao:+/-0.5C|saida:4-20mA",
        "measurement_unit": "C",
        "min_operating_value": -20,
        "max_operating_value": 180,
        "price": 780.00,
        "currency": "BRL",
        "lead_time_days": 3,
        "active": True,
    }
    row.update(overrides)
    return row


class TestSearchProducts:
    def test_success_returns_active_compatible_products(self, fake_spark):
        # CA01/CA02/CA03: somente produtos ativos, da categoria e que
        # cobrem integralmente a faixa solicitada.
        fake_spark.tables["gold_product_catalog"] = [
            _product(),
            _product(
                product_id="PRD-TEMP-002",
                sku="NEX-TEMP-002",
                min_operating_value=0,
                max_operating_value=100,
                price=450.00,
            ),
            _product(
                product_id="PRD-PRES-001",
                sku="NEX-PRES-001",
                category="pressure",
                measurement_unit="bar",
                min_operating_value=0,
                max_operating_value=10,
                price=640.00,
            ),
        ]
        result = sp.run(
            {
                "session_id": "SES-1",
                "category": "temperature",
                "min_required_value": 0,
                "max_required_value": 150,
                "measurement_unit": "C",
            }
        )
        assert result["search_status"] == "success"
        assert result["result_count"] == 1
        assert result["products"][0]["product_id"] == "PRD-TEMP-001"

    def test_inactive_products_never_returned(self, fake_spark):
        # CA02: produto inativo nunca aparece nos resultados.
        fake_spark.tables["gold_product_catalog"] = [
            _product(),
            _product(product_id="PRD-TEMP-OLD", sku="NEX-TEMP-OLD", active=False),
        ]
        result = sp.run({"session_id": "SES-1", "category": "temperature"})
        assert result["search_status"] == "success"
        assert [p["product_id"] for p in result["products"]] == ["PRD-TEMP-001"]

    def test_ordering_and_default_limit(self, fake_spark):
        # SPEC §6: menor prazo, depois menor preço, depois product_id.
        # SPEC §7: limite padrão de 3 resultados.
        fake_spark.tables["gold_product_catalog"] = [
            _product(product_id="PRD-A", lead_time_days=5, price=100.0),
            _product(product_id="PRD-B", lead_time_days=3, price=500.0),
            _product(product_id="PRD-C", lead_time_days=3, price=200.0),
            _product(product_id="PRD-D", lead_time_days=3, price=200.0),
        ]
        result = sp.run({"session_id": "SES-1", "category": "temperature"})
        assert result["result_count"] == 3
        assert [p["product_id"] for p in result["products"]] == [
            "PRD-C",
            "PRD-D",
            "PRD-B",
        ]

    def test_no_compatible_product(self, fake_spark):
        # CA05: sem produto compatível → no_compatible_product, sem invenção.
        fake_spark.tables["gold_product_catalog"] = [
            _product(min_operating_value=20, max_operating_value=100),
        ]
        result = sp.run(
            {
                "session_id": "SES-1",
                "category": "temperature",
                "min_required_value": 0,
                "max_required_value": 150,
            }
        )
        assert result["search_status"] == "no_compatible_product"
        assert result["result_count"] == 0
        assert result["products"] == []

    def test_validation_error_invalid_category(self, fake_spark):
        result = sp.run({"session_id": "SES-1", "category": "light"})
        assert result["search_status"] == "validation_error"
        assert result["error_code"] == "INVALID_CATEGORY"

    def test_validation_error_inverted_range(self, fake_spark):
        result = sp.run(
            {
                "session_id": "SES-1",
                "category": "temperature",
                "min_required_value": 150,
                "max_required_value": 0,
            }
        )
        assert result["error_code"] == "INVALID_REQUIRED_RANGE"

    def test_data_error_active_product_without_specs(self, fake_spark):
        # SPEC §11: produto ativo sem especificações essenciais sinaliza
        # erro; a ferramenta não corrige silenciosamente.
        fake_spark.tables["gold_product_catalog"] = [
            _product(product_id="PRD-X", technical_specs=None),
        ]
        result = sp.run({"session_id": "SES-1", "category": "temperature"})
        assert result["search_status"] == "data_error"
        assert result["error_code"] == "DATA_ERROR"

    def test_audit_event_recorded(self, fake_spark):
        # CA09: cada execução gera evento em conversation_events.
        fake_spark.tables["gold_product_catalog"] = [_product()]
        sp.run({"session_id": "SES-1", "category": "temperature"})
        events = fake_spark.tables.get("conversation_events", [])
        assert any(
            e.get("event_type") == "product_search"
            and e.get("tool_name") == "search_products"
            for e in events
        )

    def test_reproducibility(self, fake_spark):
        # CA08: mesmas entradas e mesmo catálogo → resultados consistentes.
        fake_spark.tables["gold_product_catalog"] = [
            _product(),
            _product(
                product_id="PRD-TEMP-002",
                sku="NEX-TEMP-002",
                min_operating_value=0,
                max_operating_value=100,
                price=450.00,
            ),
        ]
        inputs = {"session_id": "SES-1", "category": "temperature"}
        first = sp.run(inputs)
        second = sp.run(inputs)
        assert [p["product_id"] for p in first["products"]] == [
            p["product_id"] for p in second["products"]
        ]

    def test_normalize_unit(self):
        assert sp.normalize_unit("°C") == "C"
        assert sp.normalize_unit("bar") == "bar"
        assert sp.normalize_unit(None) is None
