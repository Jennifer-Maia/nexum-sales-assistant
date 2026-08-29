from datetime import datetime

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


# Camada Silver — silver_inventory (docs/data_model.md §5.2, §7).
#
# Fonte: bronze_inventory. Aplica tipagem e as regras de qualidade do
# ADR-005 e de prompts/02-silver.md:
#   - unicidade de inventory_id;
#   - product_id deve existir em silver_products (integridade
#     referencial — nenhum produto é inventado para corrigir o estoque);
#   - ausência de duplicidade de produto e depósito
#     (product_id, warehouse_id);
#   - quantidades não negativas (available_quantity, reserved_quantity);
#   - campos obrigatórios conforme docs/data_model.md §7;
#   - updated_at convertido para TIMESTAMP e validado.
#
# Registros inválidos são sinalizados em `_quality_status`, nunca
# corrigidos silenciosamente (ADR-005; docs/agent_harness.md §14).
# As colunas técnicas de origem são preservadas para rastreabilidade
# Bronze → Silver. A lógica vive em funções puras testáveis em memória,
# com o dataset declarativo como cola fina (mesma decisão de
# silver_companies.py).

# Schema final da Silver (snake_case; tipos conforme docs/data_model.md §7).
SCHEMA = (
    "inventory_id STRING, product_id STRING, warehouse_id STRING, "
    "available_quantity INT, reserved_quantity INT, updated_at TIMESTAMP, "
    "_quality_status STRING, "
    "_ingestion_timestamp TIMESTAMP, _source_file STRING, _source_system STRING"
)


def _clean(value):
    """Normaliza um campo textual: trim; vazio/nulo vira None."""
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _to_int(value):
    """Converte para int; retorna None quando não numérico."""
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _to_timestamp(value):
    """Converte data/hora em datetime; None quando inválido.

    Aceita o formato de origem dos dados sintéticos (AAAA-MM-DD) e
    timestamps ISO (ex.: AAAA-MM-DDTHH:MM:SS).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value).strip())
    except ValueError:
        return None
    return parsed


def transform_rows(rows, product_ids):
    """Aplica tipagem e regras de qualidade às linhas brutas da Bronze.

    Entrada:
      - rows: lista de dicts com as colunas da Bronze (valores STRING
        mais as colunas técnicas de rastreabilidade);
      - product_ids: conjunto de product_id existentes em
        silver_products (referência de integridade).
    Saída: lista de dicts no schema da Silver, com `_quality_status`
    `valid` ou `invalid:<regra>[;<regra>]`.
    """
    inventory_id_counts = {}
    product_warehouse_counts = {}
    for row in rows:
        inventory_id = _clean(row.get("inventory_id"))
        product_id = _clean(row.get("product_id"))
        warehouse_id = _clean(row.get("warehouse_id"))
        if inventory_id:
            inventory_id_counts[inventory_id] = inventory_id_counts.get(inventory_id, 0) + 1
        if product_id and warehouse_id:
            key = (product_id, warehouse_id)
            product_warehouse_counts[key] = product_warehouse_counts.get(key, 0) + 1
    return [
        _transform_row(row, inventory_id_counts, product_warehouse_counts, product_ids)
        for row in rows
    ]


def _transform_row(row, inventory_id_counts, product_warehouse_counts, product_ids):
    problems = []

    inventory_id = _clean(row.get("inventory_id"))
    product_id = _clean(row.get("product_id"))
    warehouse_id = _clean(row.get("warehouse_id"))

    if not inventory_id:
        problems.append("inventory_id_required")
    elif inventory_id_counts.get(inventory_id, 0) > 1:
        problems.append("duplicate_inventory_id")
    if not product_id:
        problems.append("product_id_required")
    elif product_id not in product_ids:
        # Integridade referencial: o estoque deve referenciar um produto
        # existente em silver_products (ADR-005).
        problems.append("product_not_found")
    if not warehouse_id:
        problems.append("warehouse_id_required")

    if product_id and warehouse_id and product_warehouse_counts.get((product_id, warehouse_id), 0) > 1:
        # Ausência de duplicidade de produto e depósito (ADR-005).
        problems.append("duplicate_product_warehouse")

    available_quantity = _to_int(row.get("available_quantity"))
    if _clean(row.get("available_quantity")) is None:
        problems.append("available_quantity_required")
    elif available_quantity is None:
        problems.append("available_quantity_invalid")
    elif available_quantity < 0:
        problems.append("available_quantity_negative")

    reserved_quantity = _to_int(row.get("reserved_quantity"))
    if _clean(row.get("reserved_quantity")) is None:
        problems.append("reserved_quantity_required")
    elif reserved_quantity is None:
        problems.append("reserved_quantity_invalid")
    elif reserved_quantity < 0:
        problems.append("reserved_quantity_negative")

    updated_at = _to_timestamp(row.get("updated_at"))
    if updated_at is None:
        problems.append("updated_at_invalid")

    return {
        "inventory_id": inventory_id,
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "available_quantity": available_quantity,
        "reserved_quantity": reserved_quantity,
        "updated_at": updated_at,
        "_quality_status": "valid" if not problems else "invalid:" + ";".join(problems),
        "_ingestion_timestamp": row.get("_ingestion_timestamp"),
        "_source_file": row.get("_source_file"),
        "_source_system": row.get("_source_system"),
    }


@_materialized_view(
    comment="Silver: estoque tipado e validado, referenciando silver_products (ADR-005)",
)
def silver_inventory():
    product_rows = [r.asDict() for r in spark.read.table("silver_products").collect()]
    product_ids = {row["product_id"] for row in product_rows}
    rows = [r.asDict() for r in spark.read.table("bronze_inventory").collect()]
    return spark.createDataFrame(transform_rows(rows, product_ids), schema=SCHEMA)
