import math

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


# Camada Silver — silver_companies (docs/data_model.md §5.2; ADR-002).
#
# Fonte: bronze_companies. `silver_companies` é a fonte canônica de
# clientes do MVP (ADR-002):
#
#   silver_companies.company_id
#       └── quotes.customer_id
#
# Tratamentos aplicados (ADR-002; prompts/02-silver.md):
#   - normalização: trim em company_name, industry e region;
#   - validação de campos obrigatórios: company_id e company_name;
#   - unicidade de company_id: linhas duplicadas são sinalizadas, não
#     corrigidas silenciosamente (ADR-005);
#   - registros inválidos sinalizados em `_quality_status`
#     (ADR-005: sinalizar pela camada de qualidade, não corrigir);
#   - colunas técnicas de origem preservadas (_ingestion_timestamp,
#     _source_file, _source_system) para rastreabilidade Bronze → Silver.
#
# Decisão de implementação: a lógica de tratamento vive em funções puras
# testáveis em memória (ADRs 004/005). O dataset declarativo aplica a
# transformação via `mapInPandas` sobre a leitura da Bronze, preservando
# a linhagem no DLT (a Silver só materializa depois da Bronze) e usando
# `coalesce(1)` — o catálogo é pequeno e controlado (ADR-005) e as
# regras entre linhas (unicidade) precisam do conjunto completo.

# Colunas na ordem do schema final (snake_case; nomes conforme a origem).
COLUMNS = [
    "company_id",
    "company_name",
    "industry",
    "region",
    "_quality_status",
    "_ingestion_timestamp",
    "_source_file",
    "_source_system",
]

SCHEMA = (
    "company_id STRING, company_name STRING, industry STRING, region STRING, "
    "_quality_status STRING, "
    "_ingestion_timestamp TIMESTAMP, _source_file STRING, _source_system STRING"
)


def _clean(value):
    """Normaliza um campo textual: trim; vazio/nulo vira None."""
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def transform_rows(rows):
    """Aplica normalização e regras de qualidade às linhas brutas da Bronze.

    Entrada: lista de dicts com as colunas da Bronze (valores STRING mais
    as colunas técnicas de rastreabilidade).
    Saída: lista de dicts no schema da Silver, com `_quality_status`
    `valid` ou `invalid:<regra>[;<regra>]`.
    """
    counts = {}
    for row in rows:
        company_id = _clean(row.get("company_id"))
        if company_id:
            counts[company_id] = counts.get(company_id, 0) + 1
    return [_transform_row(row, counts) for row in rows]


def _transform_row(row, counts):
    company_id = _clean(row.get("company_id"))
    company_name = _clean(row.get("company_name"))
    problems = []
    if not company_id:
        problems.append("company_id_required")
    elif counts.get(company_id, 0) > 1:
        problems.append("duplicate_company_id")
    if not company_name:
        problems.append("company_name_required")
    return {
        "company_id": company_id,
        "company_name": company_name,
        "industry": _clean(row.get("industry")),
        "region": _clean(row.get("region")),
        "_quality_status": "valid" if not problems else "invalid:" + ";".join(problems),
        "_ingestion_timestamp": row.get("_ingestion_timestamp"),
        "_source_file": row.get("_source_file"),
        "_source_system": row.get("_source_system"),
    }


def _to_python(value):
    """Converte valores vindos do pandas para tipos Python limpos."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _transform_pandas(iterator):
    """Aplica `transform_rows` por partição (mapInPandas)."""
    for pdf in iterator:
        records = [
            {key: _to_python(value) for key, value in row.items()}
            for row in pdf.to_dict("records")
        ]
        yield pd.DataFrame(transform_rows(records), columns=COLUMNS)


@_materialized_view(
    comment="Silver: empresas tratadas e validadas — fonte canônica de clientes (ADR-002)",
)
def silver_companies():
    bronze = spark.read.table("bronze_companies").coalesce(1)
    return bronze.mapInPandas(_transform_pandas, schema=SCHEMA)
