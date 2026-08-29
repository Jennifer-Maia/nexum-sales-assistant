from decimal import Decimal, InvalidOperation

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


# Camada Silver — silver_products (docs/data_model.md §5.2, §6).
#
# Fonte: bronze_products. Aplica tipagem, normalização e as regras de
# qualidade do ADR-005 e de prompts/02-silver.md:
#   - unicidade de product_id e de sku;
#   - categoria válida (temperature, pressure, vibration);
#   - unidade de medição compatível com a categoria;
#   - faixa operacional consistente (min_operating_value <=
#     max_operating_value, quando ambos presentes);
#   - preço maior que zero;
#   - currency = BRL;
#   - prazo (lead_time_days) maior ou igual a zero;
#   - estado active booleano válido;
#   - campos obrigatórios conforme docs/data_model.md §6;
#   - especificações essenciais (technical_specs) presentes
#     (docs/data_model.md §6; docs/specs/search_products.md §11).
#
# Registros inválidos são sinalizados em `_quality_status`, nunca
# corrigidos silenciosamente (ADR-005; docs/agent_harness.md §14).
#
# A unidade compatível por categoria segue a tabela CATEGORY_UNITS já
# documentada em src/nexum_sales_assistant/tools/search_products.py
# (temperature: C; pressure: bar, psi; vibration: mm/s).
#
# Valores monetários e de faixa usam DECIMAL(10,2)
# (docs/data_model.md §6). A decisão de manter a lógica em funções
# puras testáveis em memória e o dataset declarativo como cola fina é a
# mesma documentada em silver_companies.py.

ALLOWED_CATEGORIES = {"temperature", "pressure", "vibration"}

CATEGORY_UNITS = {
    "temperature": {"C"},
    "pressure": {"bar", "psi"},
    "vibration": {"mm/s"},
}

# Campos textuais obrigatórios conforme docs/data_model.md §6.
REQUIRED_STRINGS = (
    "product_id",
    "sku",
    "product_name",
    "category",
    "description",
    "use_cases",
    "technical_specs",
    "measurement_unit",
    "currency",
)

# Schema final da Silver (snake_case; tipos conforme docs/data_model.md §6).
SCHEMA = (
    "product_id STRING, sku STRING, product_name STRING, category STRING, "
    "description STRING, use_cases STRING, technical_specs STRING, "
    "measurement_unit STRING, min_operating_value DECIMAL(10,2), "
    "max_operating_value DECIMAL(10,2), price DECIMAL(10,2), currency STRING, "
    "lead_time_days INT, active BOOLEAN, _quality_status STRING, "
    "_ingestion_timestamp TIMESTAMP, _source_file STRING, _source_system STRING"
)


def _clean(value):
    """Normaliza um campo textual: trim; vazio/nulo vira None."""
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _to_decimal(value):
    """Converte para Decimal(10,2); retorna None quando não numérico."""
    try:
        return Decimal(str(value).strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(value):
    """Converte para int; retorna None quando não numérico."""
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _to_bool(value):
    """Converte 'true'/'false' (ou 1/0) para bool; None quando inválido."""
    normalized = _clean(value)
    if normalized is None:
        return None
    if normalized.lower() in ("true", "1"):
        return True
    if normalized.lower() in ("false", "0"):
        return False
    return None


def transform_rows(rows):
    """Aplica tipagem e regras de qualidade às linhas brutas da Bronze.

    Entrada: lista de dicts com as colunas da Bronze (valores STRING mais
    as colunas técnicas de rastreabilidade).
    Saída: lista de dicts no schema da Silver, com `_quality_status`
    `valid` ou `invalid:<regra>[;<regra>]`.
    """
    product_id_counts = {}
    sku_counts = {}
    for row in rows:
        product_id = _clean(row.get("product_id"))
        sku = _clean(row.get("sku"))
        if product_id:
            product_id_counts[product_id] = product_id_counts.get(product_id, 0) + 1
        if sku:
            sku_counts[sku] = sku_counts.get(sku, 0) + 1
    return [_transform_row(row, product_id_counts, sku_counts) for row in rows]


def _transform_row(row, product_id_counts, sku_counts):
    problems = []

    product_id = _clean(row.get("product_id"))
    sku = _clean(row.get("sku"))
    category = _clean(row.get("category"))
    measurement_unit = _clean(row.get("measurement_unit"))
    currency = _clean(row.get("currency"))
    technical_specs = _clean(row.get("technical_specs"))

    for field in REQUIRED_STRINGS:
        if _clean(row.get(field)) is None:
            problems.append(f"{field}_required")

    if product_id and product_id_counts.get(product_id, 0) > 1:
        problems.append("duplicate_product_id")
    if sku and sku_counts.get(sku, 0) > 1:
        problems.append("duplicate_sku")

    if category is not None and category not in ALLOWED_CATEGORIES:
        problems.append("category_invalid")
    if category in ALLOWED_CATEGORIES and measurement_unit is not None:
        if measurement_unit not in CATEGORY_UNITS[category]:
            problems.append("measurement_unit_incompatible")

    min_operating_value = _to_decimal(row.get("min_operating_value"))
    max_operating_value = _to_decimal(row.get("max_operating_value"))
    if row.get("min_operating_value") not in (None, "") and min_operating_value is None:
        problems.append("min_operating_value_invalid")
    if row.get("max_operating_value") not in (None, "") and max_operating_value is None:
        problems.append("max_operating_value_invalid")
    if min_operating_value is not None and max_operating_value is not None:
        if min_operating_value > max_operating_value:
            problems.append("operating_range_inconsistent")
    elif (min_operating_value is None) != (max_operating_value is None):
        # Apenas um dos limites presente: faixa inconsistente (ADR-005).
        problems.append("operating_range_inconsistent")

    price = _to_decimal(row.get("price"))
    if _clean(row.get("price")) is None:
        problems.append("price_required")
    elif price is None:
        problems.append("price_invalid")
    elif price <= 0:
        # Regra do ADR-005: preço maior que zero.
        problems.append("price_not_positive")

    lead_time_days = _to_int(row.get("lead_time_days"))
    if _clean(row.get("lead_time_days")) is None:
        problems.append("lead_time_days_required")
    elif lead_time_days is None:
        problems.append("lead_time_days_invalid")
    elif lead_time_days < 0:
        problems.append("lead_time_days_negative")

    active = _to_bool(row.get("active"))
    if _clean(row.get("active")) is None:
        problems.append("active_required")
    elif active is None:
        problems.append("active_invalid")

    if currency is not None and currency != "BRL":
        problems.append("currency_invalid")

    return {
        "product_id": product_id,
        "sku": sku,
        "product_name": _clean(row.get("product_name")),
        "category": category,
        "description": _clean(row.get("description")),
        "use_cases": _clean(row.get("use_cases")),
        "technical_specs": technical_specs,
        "measurement_unit": measurement_unit,
        "min_operating_value": min_operating_value,
        "max_operating_value": max_operating_value,
        "price": price,
        "currency": currency,
        "lead_time_days": lead_time_days,
        "active": active,
        "_quality_status": "valid" if not problems else "invalid:" + ";".join(problems),
        "_ingestion_timestamp": row.get("_ingestion_timestamp"),
        "_source_file": row.get("_source_file"),
        "_source_system": row.get("_source_system"),
    }


@_materialized_view(
    comment="Silver: produtos tipados e validados conforme ADR-005",
)
def silver_products():
    rows = [r.asDict() for r in spark.read.table("bronze_products").collect()]
    return spark.createDataFrame(transform_rows(rows), schema=SCHEMA)
