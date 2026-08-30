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


def resolve_profile():
    """Perfil do Databricks usado pela sessão local (configurável).

    Precedência: `NEXUM_DATABRICKS_PROFILE` > `DATABRICKS_CONFIG_PROFILE`
    > `"jornada"`. O perfil é SEMPRE explícito — nunca depende do
    default do `.databrickscfg` (o `[__settings__]` deste workspace
    aponta para um perfil antigo com token inválido).
    """
    return (
        os.environ.get("NEXUM_DATABRICKS_PROFILE")
        or os.environ.get("DATABRICKS_CONFIG_PROFILE")
        or "jornada"
    )


def _enable_serverless_fallback():
    """Habilita compute serverless quando nenhum cluster está configurado.

    Mesma lógica do conftest dos testes: o SDK do Connect lê
    `DATABRICKS_SERVERLESS_COMPUTE_ID`; `auto` usa serverless.
    """
    if os.environ.get("SPARK_REMOTE") or os.environ.get("DATABRICKS_SERVERLESS_COMPUTE_ID"):
        return
    try:
        from databricks.sdk import WorkspaceClient

        conf = WorkspaceClient(profile=resolve_profile()).config
        if conf.serverless_compute_id or conf.cluster_id:
            return
    except Exception:
        pass
    os.environ["DATABRICKS_SERVERLESS_COMPUTE_ID"] = "auto"


def get_spark():
    """Sessão Spark via Databricks Connect (serverless).

    O perfil é passado explicitamente ao builder e também fixado no
    ambiente (os providers de auth do SDK spawnam o CLI com o perfil
    do Config); sem isso, o Connect resolve o default do
    `.databrickscfg` e pode falhar com perfil errado.
    """
    _enable_serverless_fallback()
    profile = resolve_profile()
    os.environ["DATABRICKS_CONFIG_PROFILE"] = profile
    from databricks.connect import DatabricksSession

    try:
        return DatabricksSession.builder.profile(profile).getOrCreate()
    except AttributeError:
        # Versões do builder sem .profile() usam o env var já fixado.
        return DatabricksSession.builder.getOrCreate()


def is_expired_session_error(exc):
    """Detecta expiração da sessão Connect por inatividade.

    O compute serverless encerra sessões ociosas; o erro típico é
    `session_id is no longer usable (INACTIVITY_TIMEOUT)`. A UI do
    chat usa esta checagem para recriar a sessão e repetir.
    """
    text = str(exc)
    return "INACTIVITY_TIMEOUT" in text or "session_id is no longer usable" in text


def reset_spark():
    """Encerra a sessão Connect atual para forçar uma nova.

    A próxima chamada a `get_spark()` (ou ao `getOrCreate()` das
    ferramentas) cria uma sessão nova com outro session_id, o que
    reanexa o compute serverless.
    """
    from pyspark.sql import SparkSession

    session = SparkSession.getActiveSession() or SparkSession.builder.getOrCreate()
    try:
        session.stop()
    except Exception:
        pass


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
