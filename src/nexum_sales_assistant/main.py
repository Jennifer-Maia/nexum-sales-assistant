"""Entry point do bundle Databricks do Nexum Sales Assistant.

Recebe o catalog e o schema das variáveis do bundle (`${var.catalog}` e
`${var.schema}`), sem fixar nomes no código, e:

1. entrega os valores às ferramentas via variáveis de ambiente
   `NEXUM_CATALOG`/`NEXUM_SCHEMA` — as ferramentas montam nomes de
   tabela totalmente qualificados e não dependem do estado de sessão
   (docs/data_model.md §19);
2. alinha o catalog/schema padrão da sessão para demais usos.

O uso de `USE CATALOG`/`USE SCHEMA` permanece como conveniência de
sessão, mas as ferramentas não dependem dele.
"""

import argparse
import os

from databricks.sdk.runtime import spark


def main():
    parser = argparse.ArgumentParser(
        description="Nexum Sales Assistant job",
    )
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    # Entrega catalog/schema às ferramentas (docs/data_model.md §19).
    os.environ["NEXUM_CATALOG"] = args.catalog
    os.environ["NEXUM_SCHEMA"] = args.schema

    # Define o catalog e schema padrão do ambiente de execução.
    spark.sql(f"USE CATALOG {args.catalog}")
    spark.sql(f"USE SCHEMA {args.schema}")


if __name__ == "__main__":
    main()
