"""Ferramenta `search_products` do Nexum Sales Assistant.

Contrato: docs/specs/search_products.md
Fonte de dados: `gold_product_catalog` (docs/data_model.md §17).
"""

import uuid
from datetime import datetime, timezone
from nexum_sales_assistant.tools._table_ref import qualified_table

ALLOWED_CATEGORIES = {"temperature", "pressure", "vibration"}
DEFAULT_LIMIT = 3
MAX_LIMIT = 10

# Unidades aceitas por categoria no MVP. A ferramenta não realiza
# conversão de unidades (SPEC §5.4); apenas normaliza `°C` para `C`.
CATEGORY_UNITS = {
    "temperature": {"C"},
    "pressure": {"bar", "psi"},
    "vibration": {"mm/s"},
}


def normalize_unit(unit):
    """Normaliza a unidade informada (SPEC §5.4: `C` e `°C` são a mesma unidade)."""
    if unit is None:
        return None
    return "C" if unit in ("C", "°C") else unit


def covers_range(min_required, max_required, min_operating, max_operating):
    """Regra de compatibilidade de faixa da SPEC §5.3.

    Produto sem faixa operacional registrada não pode ser considerado
    compatível (não recomendar sem requisitos essenciais).
    """
    if min_operating is None or max_operating is None:
        return False
    return min_operating <= min_required and max_operating >= max_required


def validate_input(inputs):
    """Validações de entrada da SPEC §10.

    Retorna um dicionário de erro (`search_status = validation_error`)
    ou `None` quando a entrada é válida.
    """
    session_id = inputs.get("session_id")
    if not session_id:
        return _error("MISSING_SESSION_ID", "session_id is required", session_id)

    category = inputs.get("category")
    if not category:
        return _error("MISSING_CATEGORY", "category is required", session_id)
    if category not in ALLOWED_CATEGORIES:
        return _error(
            "INVALID_CATEGORY",
            f"category must be one of: {', '.join(sorted(ALLOWED_CATEGORIES))}",
            session_id,
        )

    min_required = inputs.get("min_required_value")
    max_required = inputs.get("max_required_value")
    if min_required is not None and max_required is not None:
        if not _is_number(min_required) or not _is_number(max_required):
            return _error(
                "INVALID_TECHNICAL_VALUE",
                "min_required_value and max_required_value must be numeric",
                session_id,
            )
        if float(min_required) > float(max_required):
            return _error(
                "INVALID_REQUIRED_RANGE",
                "min_required_value must be less than or equal to max_required_value",
                session_id,
            )

    quantity = inputs.get("quantity")
    if quantity is not None and (not _is_number(quantity) or float(quantity) <= 0):
        return _error("INVALID_QUANTITY", "quantity must be greater than zero", session_id)

    limit = inputs.get("limit")
    if limit is not None:
        if not _is_number(limit) or int(limit) < 1 or int(limit) > MAX_LIMIT:
            return _error(
                "INVALID_LIMIT",
                f"limit must be between 1 and {MAX_LIMIT}",
                session_id,
            )

    unit = normalize_unit(inputs.get("measurement_unit"))
    if unit is not None and unit not in CATEGORY_UNITS[category]:
        return _error(
            "INVALID_UNIT",
            f"measurement_unit '{unit}' is not compatible with category '{category}'",
            session_id,
        )

    return None


def sort_products(products):
    """Ordenação determinística da SPEC §6.

    A ordenação por compatibilidade técnica e por produto ativo já é
    garantida pelos filtros; entre os resultados aplica-se: menor prazo,
    menor preço e `product_id` como critério final.
    """
    return sorted(
        products,
        key=lambda p: (
            p.get("lead_time_days", 0),
            p.get("price", 0),
            p.get("product_id", ""),
        ),
    )


def run(inputs):
    """Executa a busca conforme a SPEC search_products.

    Entrada: dicionário com os campos da SPEC §3.
    Saída: dicionário conforme SPEC §8 (sucesso), §9 (sem resultados),
    §10 (erro de validação) ou §11 (falha de dados).
    """
    session_id = inputs.get("session_id")

    error = validate_input(inputs)
    if error is not None:
        _record_event(session_id, "product_search", None, _content(error, "validation_error"))
        return error

    searched_at = _now()
    limit = inputs.get("limit") or DEFAULT_LIMIT
    category = inputs["category"]
    unit = normalize_unit(inputs.get("measurement_unit"))
    min_required = inputs.get("min_required_value")
    max_required = inputs.get("max_required_value")
    quantity = inputs.get("quantity")
    use_case = inputs.get("use_case")
    product_ids = inputs.get("product_ids")

    try:
        catalog = _spark().table(qualified_table("gold_product_catalog")).collect()
    except Exception as exc:  # tabela indisponível — SPEC §11
        return _fail_data(
            session_id,
            "DATA_ERROR",
            f"gold_product_catalog is not available: {exc}",
        )

    # Falhas de qualidade dos dados — SPEC §11 (não corrigir silenciosamente).
    data_errors = []
    for row in catalog:
        row_dict = row.asDict()
        if not row_dict.get("category"):
            data_errors.append(f"product without category: {row_dict.get('product_id')}")
        if row_dict.get("active") and not row_dict.get("technical_specs"):
            data_errors.append(
                f"active product without essential specs: {row_dict.get('product_id')}"
            )
        min_op = row_dict.get("min_operating_value")
        max_op = row_dict.get("max_operating_value")
        if min_op is not None and max_op is not None and min_op > max_op:
            data_errors.append(f"inconsistent operating range: {row_dict.get('product_id')}")
        if row_dict.get("price") is None or row_dict.get("price") < 0:
            data_errors.append(f"invalid price: {row_dict.get('product_id')}")
        if row_dict.get("lead_time_days") is None or row_dict.get("lead_time_days") < 0:
            data_errors.append(f"invalid lead time: {row_dict.get('product_id')}")
    if data_errors:
        result = _fail_data(session_id, "DATA_ERROR", "; ".join(data_errors))
        _record_event(session_id, "product_search", None, _content(result, "data_error"))
        return result

    products = []
    for row in catalog:
        p = row.asDict()
        if not p.get("active"):
            continue
        if p.get("category") != category:
            continue
        if product_ids is not None and p.get("product_id") not in product_ids:
            continue
        if use_case and use_case.lower() not in str(p.get("use_cases") or "").lower():
            continue
        if min_required is not None and max_required is not None:
            if not covers_range(
                float(min_required),
                float(max_required),
                p.get("min_operating_value"),
                p.get("max_operating_value"),
            ):
                continue
        if unit is not None and normalize_unit(p.get("measurement_unit")) != unit:
            continue
        products.append(p)

    ordered = sort_products(products)[:limit]

    if not ordered:
        result = {
            "session_id": session_id,
            "search_status": "no_compatible_product",
            "result_count": 0,
            "products": [],
            "searched_at": searched_at,
        }
        _record_event(session_id, "product_search", None, _content(result, "no_compatible_product"))
        return result

    result = {
        "session_id": session_id,
        "search_status": "success",
        "result_count": len(ordered),
        "products": [
            {
                "product_id": p.get("product_id"),
                "sku": p.get("sku"),
                "product_name": p.get("product_name"),
                "category": p.get("category"),
                "description": p.get("description"),
                "use_cases": p.get("use_cases"),
                "technical_specs": p.get("technical_specs"),
                "measurement_unit": p.get("measurement_unit"),
                "min_operating_value": p.get("min_operating_value"),
                "max_operating_value": p.get("max_operating_value"),
                "price": p.get("price"),
                "currency": p.get("currency"),
                "lead_time_days": p.get("lead_time_days"),
                "active": p.get("active"),
            }
            for p in ordered
        ],
        "searched_at": searched_at,
    }
    # A quantidade solicitada é apenas contexto; a disponibilidade é
    # responsabilidade de check_inventory (SPEC §5.6, §13).
    if quantity is not None:
        result["quantity_requested"] = quantity
    _record_event(session_id, "product_search", None, _content(result, "success"))
    return result


def _error(code, message, session_id):
    return {
        "session_id": session_id,
        "search_status": "validation_error",
        "error_code": code,
        "message": message,
    }


def _fail_data(session_id, code, message):
    return {
        "session_id": session_id,
        "search_status": "data_error",
        "error_code": code,
        "message": message,
    }


def _content(result, outcome):
    """Conteúdo do evento de auditoria (SPEC §14)."""
    return {
        "outcome": outcome,
        "search_status": result.get("search_status"),
        "result_count": result.get("result_count"),
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
    """Registra o evento de auditoria em conversation_events (SPEC §14)."""
    spark = _spark()
    row = spark.createDataFrame(
        [
            (
                "EVT-" + uuid.uuid4().hex[:8].upper(),
                session_id,
                event_type,
                "system",
                _json_dumps(content),
                "search_products",
                tool_reference_id,
                datetime.now(timezone.utc),
            )
        ],
        schema=(
            "event_id STRING, session_id STRING, event_type STRING, actor STRING, "
            "content STRING, tool_name STRING, tool_reference_id STRING, created_at TIMESTAMP"
        ),
    )
    row.write.mode("append").saveAsTable(qualified_table("conversation_events"))


def _json_dumps(content):
    import json

    return json.dumps(content, ensure_ascii=False, default=str)
