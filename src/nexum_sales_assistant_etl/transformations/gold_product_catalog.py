import math
from decimal import Decimal

import pandas as pd

try:
    from pyspark import pipelines as dp
except ImportError:  # fora do runtime DLT (ex.: testes unitários locais)
    dp = None


def _materialized_view(**kwargs):
    """Aplica @dp.materialized_view quando o runtime DLT está disponível.

    Fora do Databricks, retorna um decorador no-op para que a lógica pura
    do módulo continue importável e testável em memória.
    """
    if dp is None:
        return lambda fn: fn
    return dp.materialized_view(**kwargs)


# Camada Gold — gold_product_catalog (docs/data_model.md §16;
# prompts/03-gold.md).
#
# Fonte: silver_products. Campos exatamente conforme
# docs/data_model.md §16 — a Gold inclui apenas produtos com
# `_quality_status = valid` (ADR-005: os critérios de qualidade são
# verificados antes de os dados chegarem à Gold; dados inválidos são
# sinalizados na Silver, não corrigidos silenciosamente).
#
# Produtos válidos inativos permanecem no catálogo (`active = false`):
# a exclusão de inativos da recomendação é responsabilidade de
# search_products (docs/specs/search_products.md §5.1).
#
# Consumida por: search_products, check_inventory e create_quote
# (ADR-005). A lógica vive em função pura testável em memória, aplicada
# via `mapInPandas` com `coalesce(1)` (mesma decisão documentada em
# silver_companies.py), preservando a linhagem no DLT.

# Colunas de saída conforme docs/data_model.md §16.
CATALOG_COLUMNS = [
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

SCHEMA = (
    "product_id STRING, sku STRING, product_name STRING, category STRING, "
    "description STRING, use_cases STRING, technical_specs STRING, "
    "measurement_unit STRING, min_operating_value DECIMAL(10,2), "
    "max_operating_value DECIMAL(10,2), price DECIMAL(10,2), currency STRING, "
    "lead_time_days INT, active BOOLEAN"
)


def build_rows(products):
    """Projeta somente produtos válidos da Silver para o contrato da Gold.

    Entrada: lista de dicts no schema de silver_products.
    Saída: lista de dicts com exatamente as colunas de
    docs/data_model.md §16 (nenhum dado é inventado).
    """
    return [
        {column: row[column] for column in CATALOG_COLUMNS}
        for row in products
        if row.get("_quality_status") == "valid"
    ]


def _to_python(value):
    """Converte valores vindos do pandas para tipos Python limpos."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _to_pandas_value(value):
    """Converte valores Python para tipos suportados pelo pandas/Arrow."""
    if isinstance(value, Decimal):
        return float(value)
    return value


def _catalog_pandas(iterator):
    """Aplica `build_rows` por partição (mapInPandas)."""
    for pdf in iterator:
        records = [
            {key: _to_python(value) for key, value in row.items()}
            for row in pdf.to_dict("records")
        ]
        catalog = build_rows(records)
        clean = [
            {key: _to_pandas_value(value) for key, value in row.items()}
            for row in catalog
        ]
        yield pd.DataFrame(clean, columns=CATALOG_COLUMNS)


@_materialized_view(
    comment="Gold: catálogo de produtos válidos para consumo das ferramentas (ADR-005)",
)
def gold_product_catalog():
    products = spark.read.table("silver_products").coalesce(1)
    return products.mapInPandas(_catalog_pandas, schema=SCHEMA)
