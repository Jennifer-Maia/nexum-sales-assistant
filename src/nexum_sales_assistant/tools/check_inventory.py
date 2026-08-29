"""Ferramenta `check_inventory` do Nexum Sales Assistant.

Contrato: docs/specs/check_inventory.md
Fonte de dados: `gold_product_availability` (docs/data_model.md §16).

A ferramenta é somente de consulta: não reserva, não reduz e não
altera o estoque (SPEC §16).
"""

import uuid
from datetime import datetime, timedelta, timezone

DEFAULT_WAREHOUSE = "WH-MAIN"
STALE_LIMIT_DAYS = 7


def decide_availability(available_quantity, quantity_requested):
    """Regra de disponibilidade da SPEC §6."""
    return available_quantity >= quantity_requested


def is_stale(inventory_updated_at, now=None, limit_days=STALE_LIMIT_DAYS):
    """Sinaliza dado de estoque desatualizado além do limite (SPEC §13)."""
    if inventory_updated_at is None:
        return False
    if isinstance(inventory_updated_at, str):
        inventory_updated_at = datetime.fromisoformat(
            inventory_updated_at.replace("Z", "+00:00")
        )
    if now is None:
        now = datetime.now(timezone.utc)
    if inventory_updated_at.tzinfo is None:
        inventory_updated_at = inventory_updated_at.replace(tzinfo=timezone.utc)
    return (now - inventory_updated_at) > timedelta(days=limit_days)


def validate_input(inputs):
    """Validações de entrada da SPEC §4.

    Retorna um dicionário de erro (`inventory_status = validation_error`)
    ou `None` quando a entrada é válida.
    """
    session_id = inputs.get("session_id")
    if not session_id:
        return _error("MISSING_SESSION_ID", "session_id is required", session_id, None)
    product_id = inputs.get("product_id")
    if not product_id:
        return _error("MISSING_PRODUCT_ID", "product_id is required", session_id, None)
    quantity_requested = inputs.get("quantity_requested")
    if quantity_requested is None:
        return _error(
            "MISSING_QUANTITY_REQUESTED",
            "quantity_requested is required",
            session_id,
            product_id,
        )
    if not _is_number(quantity_requested) or float(quantity_requested) <= 0:
        return _error(
            "INVALID_QUANTITY",
            "quantity_requested must be greater than zero",
            session_id,
            product_id,
        )
    warehouse_id = inputs.get("warehouse_id")
    if warehouse_id is not None and warehouse_id == "":
        return _error(
            "INVALID_WAREHOUSE",
            "warehouse_id must not be empty when informed",
            session_id,
            product_id,
        )
    return None


def run(inputs):
    """Executa a consulta de disponibilidade conforme a SPEC check_inventory.

    Saída: dicionário conforme SPEC §9 (disponível), §10 (estoque
    insuficiente), §11 (sem registro de estoque), §12 (produto
    inexistente), §13 (dado desatualizado) ou §14 (erro de qualidade).
    """
    session_id = inputs.get("session_id")
    product_id = inputs.get("product_id")
    quantity_requested = inputs.get("quantity_requested")
    warehouse_id = inputs.get("warehouse_id") or DEFAULT_WAREHOUSE
    checked_at = _now()

    error = validate_input(inputs)
    if error is not None:
        _record_event(session_id, "inventory_checked", product_id, _content(error))
        return error

    spark = _spark()

    # Produto inexistente no catálogo — SPEC §12.
    try:
        catalog_rows = spark.table("gold_product_catalog").filter(
            f"product_id = '{product_id}'"
        ).collect()
    except Exception as exc:
        return _fail_data(
            session_id, product_id, "DATA_ERROR", f"gold_product_catalog is not available: {exc}"
        )
    if not catalog_rows:
        result = {
            "session_id": session_id,
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "inventory_status": "product_not_found",
            "available": False,
            "quantity_requested": quantity_requested,
            "checked_at": checked_at,
        }
        _record_event(session_id, "inventory_checked", product_id, _content(result))
        return result

    # Produto inativo — SPEC §4 (não confirmar disponibilidade).
    if not catalog_rows[0].asDict().get("active"):
        result = _error(
            "PRODUCT_INACTIVE",
            "The product is not active",
            session_id,
            product_id,
        )
        _record_event(session_id, "inventory_checked", product_id, _content(result))
        return result

    # Disponibilidade na Gold — SPEC §5.
    try:
        inventory_rows = spark.table("gold_product_availability").filter(
            f"product_id = '{product_id}' AND warehouse_id = '{warehouse_id}'"
        ).collect()
    except Exception as exc:
        return _fail_data(
            session_id, product_id, "DATA_ERROR", f"gold_product_availability is not available: {exc}"
        )

    # Sem registro de estoque — SPEC §11.
    if not inventory_rows:
        result = {
            "session_id": session_id,
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "inventory_status": "inventory_not_found",
            "available": False,
            "quantity_requested": quantity_requested,
            "available_quantity": None,
            "reserved_quantity": None,
            "checked_at": checked_at,
        }
        _record_event(session_id, "inventory_checked", product_id, _content(result))
        return result

    # Erros de qualidade dos dados — SPEC §14 (não corrigir silenciosamente).
    if len(inventory_rows) > 1:
        result = _fail_data(
            session_id,
            product_id,
            "DATA_ERROR",
            "multiple valid inventory records for the same product and warehouse",
        )
        _record_event(session_id, "inventory_checked", product_id, _content(result))
        return result

    row = inventory_rows[0].asDict()
    available_quantity = row.get("available_quantity")
    reserved_quantity = row.get("reserved_quantity")
    inventory_updated_at = row.get("inventory_updated_at")
    quality_error = None
    if available_quantity is None:
        quality_error = "available_quantity is null"
    elif available_quantity < 0:
        quality_error = "available_quantity is negative"
    if reserved_quantity is not None and reserved_quantity < 0:
        quality_error = "reserved_quantity is negative"
    if inventory_updated_at is None:
        quality_error = "inventory_updated_at is invalid"
    if quality_error:
        result = _fail_data(session_id, product_id, "DATA_ERROR", quality_error)
        _record_event(session_id, "inventory_checked", product_id, _content(result))
        return result

    base = {
        "session_id": session_id,
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "quantity_requested": quantity_requested,
        "available_quantity": available_quantity,
        "reserved_quantity": reserved_quantity,
        "inventory_updated_at": inventory_updated_at,
        "checked_at": checked_at,
    }

    # Dado desatualizado além do limite — SPEC §13.
    if is_stale(inventory_updated_at):
        result = {
            **base,
            "inventory_status": "stale_inventory",
            "available": False,
            "message": "Inventory data requires human confirmation because it is older than 7 days",
        }
        _record_event(session_id, "inventory_checked", product_id, _content(result))
        return result

    available = decide_availability(available_quantity, float(quantity_requested))
    result = {
        **base,
        "inventory_status": "available" if available else "insufficient_stock",
        "available": available,
    }
    _record_event(session_id, "inventory_checked", product_id, _content(result))
    return result


def _error(code, message, session_id, product_id):
    return {
        "session_id": session_id,
        "product_id": product_id,
        "inventory_status": "validation_error",
        "error_code": code,
        "message": message,
    }


def _fail_data(session_id, product_id, code, message):
    return {
        "session_id": session_id,
        "product_id": product_id,
        "inventory_status": "data_error",
        "error_code": code,
        "message": message,
    }


def _content(result):
    """Conteúdo do evento de auditoria (SPEC §15)."""
    return {
        "inventory_status": result.get("inventory_status"),
        "available": result.get("available"),
        "quantity_requested": result.get("quantity_requested"),
        "available_quantity": result.get("available_quantity"),
        "inventory_updated_at": result.get("inventory_updated_at"),
        "error_code": result.get("error_code"),
        "message": result.get("message"),
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
    """Registra o evento de auditoria em conversation_events (SPEC §15)."""
    spark = _spark()
    row = spark.createDataFrame(
        [
            (
                "EVT-" + uuid.uuid4().hex[:8].upper(),
                session_id,
                event_type,
                "system",
                _json_dumps(content),
                "check_inventory",
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
