"""Camada de conexão local do chat (Databricks Connect + serverless).

Arquitetura local do chat (README): o processo local abre uma sessão
Spark real via Databricks Connect apontando para o compute serverless
do workspace (perfil configurado no Databricks CLI). O agente e as seis
ferramentas continuam usando a mesma sessão — as ferramentas chamam
`SparkSession.builder.getOrCreate()`, que devolve a sessão Connect já
criada quando o databricks-connect está instalado.

Catalog/schema vêm das variáveis de ambiente `NEXUM_CATALOG` e
`NEXUM_SCHEMA` (mesmo padrão documentado em docs/data_model.md §19) —
nada é fixado aqui. A autenticação vem do perfil do Databricks CLI
(`DATABRICKS_CONFIG_PROFILE`), nunca de segredos em arquivo.
"""

import os


def _enable_serverless_fallback():
    """Habilita compute serverless quando nenhum cluster está configurado.

    Mesma lógica do conftest dos testes: o SDK do Connect lê
    `DATABRICKS_SERVERLESS_COMPUTE_ID`; `auto` usa serverless.
    """
    if os.environ.get("SPARK_REMOTE") or os.environ.get("DATABRICKS_SERVERLESS_COMPUTE_ID"):
        return
    try:
        from databricks.sdk import WorkspaceClient

        conf = WorkspaceClient().config
        if conf.serverless_compute_id or conf.cluster_id:
            return
    except Exception:
        pass
    os.environ["DATABRICKS_SERVERLESS_COMPUTE_ID"] = "auto"


def get_spark():
    """Sessão Spark via Databricks Connect (serverless)."""
    _enable_serverless_fallback()
    from databricks.connect import DatabricksSession

    return DatabricksSession.builder.getOrCreate()


def ensure_environment(spark):
    """Valida catalog/schema e garante as tabelas runtime.

    Reusa `ensure_runtime_tables` do agente (nenhuma lógica duplicada);
    retorna (catalog, schema).
    """
    catalog = os.environ.get("NEXUM_CATALOG")
    schema = os.environ.get("NEXUM_SCHEMA")
    if not catalog or not schema:
        raise RuntimeError(
            "NEXUM_CATALOG e NEXUM_SCHEMA não estão definidas. "
            "Defina-as no ambiente antes de iniciar o chat (veja o README)."
        )
    from nexum_sales_assistant.agent.schema_bootstrap import ensure_runtime_tables

    ensure_runtime_tables(spark)
    return catalog, schema
