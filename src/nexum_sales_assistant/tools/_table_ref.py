"""Resolução de nomes de tabela totalmente qualificados nas ferramentas.

Decisão registrada em docs/data_model.md §19: as ferramentas não podem
depender de `USE CATALOG`/`USE SCHEMA` de sessão, pois não há garantia
de que o entry point (`main.py`) seja executado antes delas. Cada
ferramenta passa a resolver o nome completo `{catalog}.{schema}.{tabela}`.

O catalog e o schema vêm das variáveis do bundle (`databricks.yml`:
`var.catalog`, `var.schema`), entregues ao processo pelas variáveis de
ambiente `NEXUM_CATALOG` e `NEXUM_SCHEMA` (definidas pelo entry point
`src/nexum_sales_assistant/main.py` a partir dos argumentos repassados
pelo bundle). Nenhum nome de catalog/schema é fixado neste código.
"""

import os

CATALOG_ENV = "NEXUM_CATALOG"
SCHEMA_ENV = "NEXUM_SCHEMA"


def qualified_table(table):
    """Retorna o nome totalmente qualificado `{catalog}.{schema}.{tabela}`.

    Falha de forma explícita quando as variáveis de ambiente não estão
    definidas, em vez de escrever ou ler silenciosamente no schema
    default da sessão.
    """
    catalog = os.environ.get(CATALOG_ENV)
    schema = os.environ.get(SCHEMA_ENV)
    if not catalog or not schema:
        raise RuntimeError(
            f"{CATALOG_ENV} and {SCHEMA_ENV} must be set to resolve table "
            f"'{table}' (bundle variables var.catalog and var.schema)"
        )
    return f"{catalog}.{schema}.{table}"
