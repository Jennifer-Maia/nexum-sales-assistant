"""Ferramenta `create_quote` do Nexum Sales Assistant.

Contrato: docs/specs/create_quote.md
Fontes de dados: `silver_companies` (ADR-002), `gold_product_catalog`,
`gold_product_availability`. Persistência em `quotes` e `quote_items`
(docs/data_model.md §8–§9).

Nota: `valid_until` é retornado na saída da ferramenta (SPEC §12–§13),
mas não é persistido, pois `docs/data_model.md` §8 não define essa
coluna na tabela `quotes`.
"""

import uuid
from datetime import datetime, timedelta, timezone

MVP_CURRENCY = "BRL"
DEFAULT_VALIDITY_DAYS = 7


def build_items(items_input, catalog_prices):
    """Congela o preço do catálogo nos itens e calcula subtotais (SPEC §9).

    `catalog_prices` é um dicionário `product_id -> unit_price` consultado
    em `gold_product_catalog`.
    """
    items = []
    for item in items_input:
        product_id = item["product_id"]
        quantity = int(item["quantity"])
        unit_price = catalog_prices[product_id]
        items.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": round(quantity * unit_price, 2),
            }
        )
    return items


def compute_total(items):
    """Total da cotação como soma dos subtotais (SPEC §9)."""
    return round(sum(item["subtotal"] for item in items), 2)


def default_valid_until(created_at):
    """Validade padrão do MVP: criada + 7 dias (SPEC §12)."""
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return (created_at + timedelta(days=DEFAULT_VALIDITY_DAYS)).strftime("%Y-%m-%d")


def validate_input(inputs):
    """Validações de entrada da SPEC §4."""
    session_id = inputs.get("session_id")
    if not session_id:
        return _error("MISSING_SESSION_ID", "session_id is required")
    customer_id = inputs.get("customer_id")
    if not customer_id:
        return _error("MISSING_CUSTOMER_ID", "customer_id is required")
    items = inputs.get("items")
    if not items:
        return _error("MISSING_ITEMS", "items is required and must not be empty")
    requested_by = inputs.get("requested_by")
    if not requested_by:
        return _error("MISSING_REQUESTED_BY", "requested_by is required")
    currency = inputs.get("currency") or MVP_CURRENCY
    if currency != MVP_CURRENCY:
        return _error("INVALID_CURRENCY", f"currency must be '{MVP_CURRENCY}' in the MVP")

    seen = set()
    for item in items:
        product_id = item.get("product_id")
        if not product_id:
            return _error("MISSING_PRODUCT_ID", "every item must have a product_id")
        quantity = item.get("quantity")
        if quantity is None:
            return _error("MISSING_QUANTITY", "every item must have a quantity")
        if not _is_number(quantity) or float(quantity) <= 0:
            return _error("INVALID_QUANTITY", "quantity must be greater than zero")
        if product_id in seen:
            return _error("DUPLICATE_PRODUCT", "the same product appears more than once in the list")
        seen.add(product_id)

    valid_until = inputs.get("valid_until")
    if valid_until is not None:
        try:
            if datetime.strptime(valid_until, "%Y-%m-%d").date() < datetime.now(timezone.utc).date():
                return _error("INVALID_VALID_UNTIL", "valid_until must not be before the creation date")
        except ValueError:
            return _error("INVALID_VALID_UNTIL", "valid_until must be a date in YYYY-MM-DD format")
    return None


def run(inputs):
    """Cria a cotação conforme a SPEC create_quote.

    Saída: dicionário conforme SPEC §13 (sucesso) ou erros das SPEC
    §4–§7 e §17.
    """
    session_id = inputs.get("session_id")
    customer_id = inputs.get("customer_id")
    currency = inputs.get("currency") or MVP_CURRENCY

    error = validate_input(inputs)
    if error is not None:
        _record_event(session_id, "quote_created", None, _content(error))
        return error

    spark = _spark()

    # Validação do cliente — SPEC §5 (ADR-002).
    try:
        customer_rows = spark.table("silver_companies").filter(
            f"company_id = '{customer_id}'"
        ).collect()
    except Exception as exc:
        return _fail_data(
            f"silver_companies is not available: {exc}"
        )
    if not customer_rows:
        result = _error(
            "CUSTOMER_NOT_FOUND",
            "The customer could not be found in the approved customer dataset",
        )
        _record_event(session_id, "quote_created", None, _content(result))
        return result

    # Produtos e preços do catálogo — SPEC §6 e §8.
    try:
        catalog_rows = spark.table("gold_product_catalog").collect()
    except Exception as exc:
        return _fail_data(f"gold_product_catalog is not available: {exc}")
    catalog = {r.asDict().get("product_id"): r.asDict() for r in catalog_rows}

    for item in inputs["items"]:
        product = catalog.get(item["product_id"])
        if (
            product is None
            or not product.get("active")
            or product.get("price") is None
            or product.get("price") < 0
            or not product.get("currency")
            or product.get("lead_time_days") is None
            or product.get("lead_time_days") < 0
            or not product.get("technical_specs")
        ):
            result = _error(
                "PRODUCT_NOT_AVAILABLE",
                "The product does not exist or is not active",
            )
            _record_event(session_id, "quote_created", None, _content(result))
            return result

    # Disponibilidade — SPEC §7 (mesma lógica de check_inventory).
    inventory_status = _check_inventory(session_id, items)
    if inventory_status is not None:
        _record_event(session_id, "quote_created", None, _content(inventory_status))
        return inventory_status

    catalog_prices = {pid: catalog[pid]["price"] for pid in catalog}
    items = build_items(inputs["items"], catalog_prices)
    total_amount = compute_total(items)

    quote_id = "QTE-" + uuid.uuid4().hex[:8].upper()
    created_at = datetime.now(timezone.utc)
    valid_until = inputs.get("valid_until") or default_valid_until(created_at)

    # Persistência — SPEC §14 (docs/data_model.md §8–§9). Estado inicial draft
    # e pagamento não iniciado; campos de aprovação permanecem nulos (§18).
    quote_row = spark.createDataFrame(
        [
            (
                quote_id,
                customer_id,
                session_id,
                "draft",
                total_amount,
                currency,
                created_at,
                None,
                None,
                None,
                "not_started",
                None,
            )
        ],
        schema=(
            "quote_id STRING, customer_id STRING, session_id STRING, status STRING, "
            "total_amount DECIMAL(10,2), currency STRING, created_at TIMESTAMP, "
            "approved_at TIMESTAMP, approved_by STRING, rejection_reason STRING, "
            "payment_status STRING, document_id STRING"
        ),
    )
    quote_row.write.mode("append").saveAsTable("quotes")

    item_rows = []
    for item in items:
        item_row = {
            "quote_item_id": "QTI-" + uuid.uuid4().hex[:8].upper(),
            "quote_id": quote_id,
            "product_id": item["product_id"],
            "quantity": item["quantity"],
            "unit_price": item["unit_price"],
            "subtotal": item["subtotal"],
        }
        item_rows.append(item_row)
    spark.createDataFrame(
        [
            (
                row["quote_item_id"],
                row["quote_id"],
                row["product_id"],
                row["quantity"],
                row["unit_price"],
                row["subtotal"],
            )
            for row in item_rows
        ],
        schema=(
            "quote_item_id STRING, quote_id STRING, product_id STRING, "
            "quantity INT, unit_price DECIMAL(10,2), subtotal DECIMAL(10,2)"
        ),
    ).write.mode("append").saveAsTable("quote_items")

    result = {
        "quote_status": "created",
        "quote_id": quote_id,
        "session_id": session_id,
        "customer_id": customer_id,
        "status": "draft",
        "currency": currency,
        "items": [
            {
                "quote_item_id": row["quote_item_id"],
                "product_id": row["product_id"],
                "quantity": row["quantity"],
                "unit_price": row["unit_price"],
                "subtotal": row["subtotal"],
            }
            for row in item_rows
        ],
        "total_amount": total_amount,
        "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "valid_until": valid_until,
        "next_action": "request_human_approval",
    }
    _record_event(session_id, "quote_created", quote_id, _content(result))
    return result


def _check_inventory(session_id, items):
    """Aplica a lógica de disponibilidade da SPEC §7 (check_inventory).

    Retorna o erro estruturado (`inventory_validation_error`) ou `None`
    quando todos os itens possuem estoque suficiente.
    """
    from nexum_sales_assistant.tools import check_inventory as ci

    problems = []
    for item in items:
        result = ci.run(
            {
                "session_id": session_id,
                "product_id": item["product_id"],
                "quantity_requested": item["quantity"],
            }
        )
        status = result.get("inventory_status")
        if status == "available":
            continue
        problem = {
            "product_id": item["product_id"],
            "quantity_requested": item["quantity"],
        }
        if status == "insufficient_stock":
            problem["available_quantity"] = result.get("available_quantity")
            problem["error_code"] = "INSUFFICIENT_STOCK"
        elif status == "inventory_not_found":
            problem["error_code"] = "INVENTORY_NOT_FOUND"
        elif status == "stale_inventory":
            problem["error_code"] = "STALE_INVENTORY"
        elif status == "product_not_found":
            problem["error_code"] = "PRODUCT_NOT_FOUND"
        else:
            problem["error_code"] = "INVENTORY_DATA_ERROR"
        problems.append(problem)

    if not problems:
        return None

    primary = problems[0]
    return {
        "quote_status": "inventory_validation_error",
        "error_code": primary["error_code"],
        "items": problems,
    }


def _error(code, message):
    return {
        "quote_status": "validation_error",
        "error_code": code,
        "message": message,
    }


def _fail_data(message):
    return {
        "quote_status": "data_error",
        "error_code": "DATA_ERROR",
        "message": message,
    }


def _content(result):
    """Conteúdo do evento de auditoria (SPEC §16)."""
    return {
        "quote_status": result.get("quote_status"),
        "quote_id": result.get("quote_id"),
        "error_code": result.get("error_code"),
        "message": result.get("message"),
        "total_amount": result.get("total_amount"),
    }


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _spark():
    try:
        from databricks.sdk.runtime import spark

        return spark
    except Exception:
        from pyspark.sql import SparkSession

        return SparkSession.builder.getOrCreate()


def _record_event(session_id, event_type, tool_reference_id, content):
    """Registra o evento de auditoria em conversation_events (SPEC §16)."""
    spark = _spark()
    row = spark.createDataFrame(
        [
            (
                "EVT-" + uuid.uuid4().hex[:8].upper(),
                session_id,
                event_type,
                "system",
                _json_dumps(content),
                "create_quote",
                tool_reference_id,
                datetime.now(timezone.utc),
            )
        ],
        schema=(
            "event_id STRING, session_id STRING, event_type STRING, actor STRING, "
            "content STRING, tool_name STRING, tool_reference_id STRING, created_at TIMESTAMP"
        ),
    )
    row.write.mode("append").saveAsTable("conversation_events")


def _json_dumps(content):
    import json

    return json.dumps(content, ensure_ascii=False, default=str)
