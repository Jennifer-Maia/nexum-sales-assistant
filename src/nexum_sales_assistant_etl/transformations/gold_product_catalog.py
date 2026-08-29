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
# (ADR-005). A lógica vive em função pura testável em memória, com o
# dataset declarativo como cola fina (mesma decisão de
# silver_companies.py).

# Colunas de saída conforme docs/data_model.md §16.
CATALOG_COLUMNS = (
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
)

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


@_materialized_view(
    comment="Gold: catálogo de produtos válidos para consumo das ferramentas (ADR-005)",
)
def gold_product_catalog():
    rows = [r.asDict() for r in spark.read.table("silver_products").collect()]
    return spark.createDataFrame(build_rows(rows), schema=SCHEMA)
