from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp, lit


# Camada Bronze — ingestão bruta de fixtures/inventory_clean.csv
# (docs/data_model.md §5.1).
#
# Estoque sintético do depósito padrão WH-MAIN, com casos de estoque
# suficiente, insuficiente, ausente e desatualizado
# (docs/adrs/ADR-005-catalogo-pequeno-no-mvp.md).
#
# Decisões documentadas:
#   - leitura batch em Materialized View (arquivo estático; carga completa
#     a cada refresh);
#   - sem inferência de schema: colunas de origem preservadas como STRING
#     (a tipagem é responsabilidade da Silver, conforme
#     docs/data_model.md §5.2);
#   - sem deduplicação, limpeza ou regras de negócio nesta camada;
#   - caminho parametrizado por configuration.source_base_path
#     (catalog/schema nunca fixados no código);
#   - sem Column Mapping: os dados sintéticos de estoque usam nomes de
#     coluna em snake_case, sem caracteres especiais.


@dp.materialized_view(
    comment="Bronze: ingestão bruta de fixtures/inventory_clean.csv",
)
def bronze_inventory():
    base_path = spark.conf.get("source_base_path")
    return (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "false")
        .load(f"{base_path}/inventory_clean.csv")
        .withColumn("_ingestion_timestamp", current_timestamp())
        .withColumn("_source_file", lit("inventory_clean.csv"))
        .withColumn("_source_system", lit("fixtures"))
    )
