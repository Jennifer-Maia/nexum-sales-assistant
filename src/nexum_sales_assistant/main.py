"""Entry point do bundle Databricks do Nexum Sales Assistant.

Define o catalog e o schema de execução a partir dos argumentos
repassados pelo bundle (`${var.catalog}` e `${var.schema}`), sem
fixar nomes no código.
"""

import argparse

from databricks.sdk.runtime import spark


def main():
    parser = argparse.ArgumentParser(
        description="Nexum Sales Assistant job",
    )
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    # Define o catalog e schema padrão do ambiente de execução.
    spark.sql(f"USE CATALOG {args.catalog}")
    spark.sql(f"USE SCHEMA {args.schema}")


if __name__ == "__main__":
    main()
