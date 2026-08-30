from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp, lit


# Camada Bronze — ingestão bruta de fixtures/products.csv
# (docs/data_model.md §5.1).
#
# Catálogo sintético pequeno e controlado conforme
# docs/adrs/ADR-005-catalogo-pequeno-no-mvp.md.
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
#   - sem Column Mapping: os dados sintéticos do catálogo usam nomes de
#     coluna em snake_case, sem caracteres especiais.


@dp.materialized_view(
    comment="Bronze: ingestão bruta de fixtures/products.csv",
)
def bronze_products():
    base_path = spark.conf.get("source_base_path")
    return (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "false")
        .load(f"{base_path}/products.csv")
        .withColumn("_ingestion_timestamp", current_timestamp())
        .withColumn("_source_file", lit("products.csv"))
        .withColumn("_source_system", lit("fixtures"))
    )
