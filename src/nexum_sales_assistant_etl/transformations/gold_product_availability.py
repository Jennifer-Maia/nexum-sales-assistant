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


# Camada Gold — gold_product_availability (docs/data_model.md §16;
# prompts/03-gold.md).
#
# Combina catálogo (silver_products) e estoque (silver_inventory),
# somente registros válidos de ambas as camadas. Campos conforme
# docs/data_model.md §16:
#   - campos principais de products (product_id, sku, product_name,
#     category, measurement_unit, active);
#   - warehouse_id, available_quantity, reserved_quantity,
#     inventory_updated_at (atualização do estoque na Silver);
#   - is_available: indica se existe quantidade disponível
#     (available_quantity > 0), sem considerar reserva física no MVP.
#
# A combinação é um inner join lógico: produtos sem registro de estoque
# ficam ausentes da Gold, permitindo que check_inventory retorne
# `inventory_not_found` (docs/specs/check_inventory.md §11). A decisão
# available_quantity >= quantity_requested continua na ferramenta
# (docs/specs/check_inventory.md §6).
#
# Consumida por: check_inventory e create_quote (ADR-005). Lógica pura
# testável em memória; dataset declarativo como cola fina.

# Campos principais de products na Gold (docs/data_model.md §16).
PRODUCT_COLUMNS = ("product_id", "sku", "product_name", "category", "measurement_unit", "active")

SCHEMA = (
    "product_id STRING, sku STRING, product_name STRING, category STRING, "
    "measurement_unit STRING, active BOOLEAN, warehouse_id STRING, "
    "available_quantity INT, reserved_quantity INT, inventory_updated_at TIMESTAMP, "
    "is_available BOOLEAN"
)


def build_rows(products, inventory):
    """Combina produtos e estoque válidos; is_available = quantidade > 0.

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
        rows.append(
            {
                **{column: product[column] for column in PRODUCT_COLUMNS},
                "warehouse_id": inv["warehouse_id"],
                "available_quantity": inv["available_quantity"],
                "reserved_quantity": inv["reserved_quantity"],
                "inventory_updated_at": inv["updated_at"],
                "is_available": inv["available_quantity"] > 0,
            }
        )
    return rows


@_materialized_view(
    comment="Gold: disponibilidade combinando catálogo e estoque válidos (docs/data_model.md §16)",
)
def gold_product_availability():
    products = [r.asDict() for r in spark.read.table("silver_products").collect()]
    inventory = [r.asDict() for r in spark.read.table("silver_inventory").collect()]
    return spark.createDataFrame(build_rows(products, inventory), schema=SCHEMA)
