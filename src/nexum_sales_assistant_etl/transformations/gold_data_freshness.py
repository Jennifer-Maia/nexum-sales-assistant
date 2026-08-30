from pyspark.sql.functions import col, count, lit, max as spark_max

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


# Camada Gold — gold_data_freshness (ADR-008).
#
# Atualização dos dados para o dashboard (que lê SOMENTE Gold):
# contagem de registros e último timestamp de ingestão por tabela das
# camadas Bronze/Silver/Gold, mais conversation_events e agent_events
# (tabelas runtime garantidas pela task bootstrap_runtime do job
# orquestrador).
#
# `atualizado_em` vem de `_ingestion_timestamp` (Bronze/Silver) ou de
# `created_at` (runtime); é NULL para as Golds, que não possuem
# timestamp próprio — limitação documentada no dashboard (ADR-008).

# (tabela, camada, coluna de timestamp ou None)
FRESHNESS_TABLES = [
    ("bronze_companies", "bronze", "_ingestion_timestamp"),
    ("bronze_products", "bronze", "_ingestion_timestamp"),
    ("bronze_inventory", "bronze", "_ingestion_timestamp"),
    ("silver_companies", "silver", "_ingestion_timestamp"),
    ("silver_products", "silver", "_ingestion_timestamp"),
    ("silver_inventory", "silver", "_ingestion_timestamp"),
    ("gold_product_catalog", "gold", None),
    ("gold_product_availability", "gold", None),
    ("gold_quote_summary", "gold", None),
    ("gold_conversation_audit", "gold", None),
    ("gold_agent_operations", "gold", None),
    ("conversation_events", "runtime", "created_at"),
    ("agent_events", "runtime", "created_at"),
]

SCHEMA = "tabela STRING, camada STRING, registros BIGINT, atualizado_em TIMESTAMP"


def freshness_entries():
    """Referência testável: tabelas cobertas por esta Gold (ADR-008)."""
    return [(table, layer) for table, layer, _ in FRESHNESS_TABLES]


@_materialized_view(
    comment="Gold: atualização dos dados por camada (ADR-008)",
)
def gold_data_freshness():
    frames = []
    for table, layer, timestamp_column in FRESHNESS_TABLES:
        source = spark.read.table(table)
        if timestamp_column:
            frame = source.select(
                lit(table).alias("tabela"),
                lit(layer).alias("camada"),
                count(col("*")).cast("bigint").alias("registros"),
                spark_max(col(timestamp_column)).alias("atualizado_em"),
            )
        else:
            frame = source.select(
                lit(table).alias("tabela"),
                lit(layer).alias("camada"),
                count(col("*")).cast("bigint").alias("registros"),
                lit(None).cast("timestamp").alias("atualizado_em"),
            )
        frames.append(frame)
    result = frames[0]
    for frame in frames[1:]:
        result = result.unionByName(frame)
    return result.select(
        col("tabela"), col("camada"), col("registros"), col("atualizado_em")
    ).orderBy("tabela")
