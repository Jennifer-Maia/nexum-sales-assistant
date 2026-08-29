from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp, lit


# Camada Bronze — ingestão bruta de fixtures/companies.csv
# (docs/data_model.md §5.1).
#
# A base de empresas existente é mantida como contexto de clientes B2B
# previamente cadastrados; a fonte canônica de clientes será
# silver_companies (ADR-002).
#
# Decisões documentadas:
#   - leitura batch em Materialized View (arquivo estático; carga completa
#     a cada refresh);
#   - sem inferência de schema: inferSchema=false, colunas de origem
#     preservadas como STRING (a tipagem é responsabilidade da Silver,
#     conforme docs/data_model.md §5.2);
#   - sem deduplicação, limpeza ou regras de negócio nesta camada;
#   - caminho parametrizado por configuration.source_base_path
#     (catalog/schema nunca fixados no código);
#   - Column Mapping do Delta habilitado para preservar os nomes originais
#     das colunas, que contêm espaços, parênteses e %.


@dp.materialized_view(
    comment="Bronze: ingestão bruta de fixtures/companies.csv",
    table_properties={
        "delta.columnMapping.mode": "name",
        "delta.minReaderVersion": "2",
        "delta.minWriterVersion": "5",
    },
)
def bronze_companies():
    base_path = spark.conf.get("source_base_path")
    return (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "false")
        .load(f"{base_path}/companies.csv")
        .withColumn("_ingestion_timestamp", current_timestamp())
        .withColumn("_source_file", lit("companies.csv"))
        .withColumn("_source_system", lit("fixtures"))
    )
