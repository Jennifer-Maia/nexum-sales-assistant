import argparse
from databricks.sdk.runtime import spark


def main():
    # Process command-line arguments
    parser = argparse.ArgumentParser(
        description="Databricks job with catalog and schema parameters",
    )
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    # Set the default catalog and schema
    spark.sql(f"USE CATALOG {args.catalog}")
    spark.sql(f"USE SCHEMA {args.schema}")

    # A lógica de negócio (Bronze, Silver e Gold) será adicionada nas próximas etapas.


if __name__ == "__main__":
    main()
