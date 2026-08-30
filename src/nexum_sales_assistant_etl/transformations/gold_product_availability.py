import math
from datetime import datetime

import pandas as pd
from pyspark.sql.functions import col

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


# Camada Gold — gold_product_availability (docs/data_model.md §17;
# prompts/03-gold.md).
#
# Combina catálogo (silver_products) e estoque (silver_inventory),
# somente registros válidos de ambas as camadas. Campos conforme
# docs/data_model.md §17:
#   - campos principais de products (product_id, sku, product_name,
#     category, measurement_unit, active);
#   - warehouse_id, available_quantity, reserved_quantity,
#     inventory_updated_at (atualização do estoque na Silver);
#   - is_available: indica se existe quantidade disponível
#     (available_quantity > 0), sem considerar reserva física no MVP.
#
# A combinação é um inner join: produtos sem registro de estoque ficam
# ausentes da Gold, permitindo que check_inventory retorne
# `inventory_not_found` (docs/specs/check_inventory.md §11). A decisão
# available_quantity >= quantity_requested continua na ferramenta
# (docs/specs/check_inventory.md §6).
#
# Consumida por: check_inventory e create_quote (ADR-005). Decisão de
# implementação: filtro de válidos e inner join em Spark (linhagem
# preservada no DLT); a projeção das linhas usa a função pura
# `_availability_row` via mapInPandas — a mesma usada pela referência
# testável `build_rows`.

# Campos principais de products na Gold (docs/data_model.md §17).
PRODUCT_COLUMNS = ("product_id", "sku", "product_name", "category", "measurement_unit", "active")

COLUMNS = [
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

SCHEMA = (
    "product_id STRING, sku STRING, product_name STRING, category STRING, "
    "measurement_unit STRING, active BOOLEAN, warehouse_id STRING, "
    "available_quantity INT, reserved_quantity INT, inventory_updated_at TIMESTAMP, "
    "is_available BOOLEAN"
)


def _availability_row(row):
    """Projeta uma linha combinada (produto + estoque) para o schema da Gold.

    `is_available` indica existência de quantidade disponível
    (docs/data_model.md §17), sem reserva física no MVP.
    """
    return {
        **{column: row[column] for column in PRODUCT_COLUMNS},
        "warehouse_id": row["warehouse_id"],
        "available_quantity": row["available_quantity"],
        "reserved_quantity": row["reserved_quantity"],
        "inventory_updated_at": row["updated_at"],
        "is_available": row["available_quantity"] > 0,
    }


def build_rows(products, inventory):
    """Referência testável da combinação produto + estoque válidos.

    Entrada: listas de dicts nos schemas de silver_products e
    silver_inventory.
    Saída: lista de dicts no schema da Gold, uma linha por produto com
    registro de estoque válido (nenhum dado é inventado).
    """
    valid_products = {
        row["product_id"]: row
        for row in products
        if row.get("_quality_status") == "valid"
    }
    rows = []
    for inv in inventory:
        if inv.get("_quality_status") != "valid":
            continue
        product = valid_products.get(inv.get("product_id"))
        if product is None:
            # Estoque sem produto válido na Silver não chega à Gold
            # (integridade referencial — ADR-005).
            continue
        rows.append(_availability_row({**inv, **product}))
    return rows


def _to_python(value):
    """Converte valores vindos do pandas para tipos Python limpos."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _to_pandas_value(value):
    """Converte valores Python para tipos suportados pelo pandas/Arrow."""
    if isinstance(value, datetime):
        return pd.Timestamp(value)
    return value


def _availability_pandas(iterator):
    """Aplica `_availability_row` por partição (mapInPandas)."""
    for pdf in iterator:
        rows = [
            {key: _to_python(value) for key, value in row.items()}
            for row in pdf.to_dict("records")
        ]
        transformed = [_availability_row(row) for row in rows]
        clean = [
            {key: _to_pandas_value(value) for key, value in row.items()}
            for row in transformed
        ]
        yield pd.DataFrame(clean, columns=COLUMNS)


@_materialized_view(
    comment="Gold: disponibilidade combinando catálogo e estoque válidos (docs/data_model.md §17)",
)
def gold_product_availability():
    products = (
        spark.read.table("silver_products")
        .filter(col("_quality_status") == "valid")
        .select(*PRODUCT_COLUMNS)
        .coalesce(1)
    )
    inventory = (
        spark.read.table("silver_inventory")
        .filter(col("_quality_status") == "valid")
        .coalesce(1)
    )
    joined = inventory.join(products, "product_id", "inner")
    return joined.mapInPandas(_availability_pandas, schema=SCHEMA)
