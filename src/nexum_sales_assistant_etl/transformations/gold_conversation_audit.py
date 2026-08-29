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


def _existing_tables():
    """Nomes das tabelas do catalog/schema atuais da pipeline.

    `spark.catalog.tableExists` não é permitido no runtime DLT
    (PY4J_BLOCKED_API); `SHOW TABLES` via `spark.sql` é a API permitida
    e não fixa nomes de catalog/schema no código.
    """
    return {row["tableName"] for row in spark.sql("SHOW TABLES").collect()}


# Camada Gold — gold_conversation_audit (docs/data_model.md §16).
#
# Visão de auditoria da conversa e das ferramentas, uma linha por
# session_id, agregando os eventos de `conversation_events` — tabela
# persistida em tempo de execução pelas ferramentas (docs/data_model.md
# §13; docs/agent_harness.md §20).
#
# Mapeamento dos campos de docs/data_model.md §16 para os tipos de
# evento documentados em docs/data_model.md §13:
#   - quantidade de mensagens ............ message_received
#   - quantidade de perguntas ............ question_asked
#   - produtos consultados ............... product_search
#   - recomendações realizadas ........... recommendation_created
#   - cotação criada ..................... quote_created
#   - aprovação (solicitada/resolvida) ... approval_requested /
#                                         approval_resolved
#   - pagamento simulado ................. payment_simulated
#   - documento gerado ................... document_generated
#   - encaminhamento humano .............. handoff_to_human
#   - erros .............................. error
#
# Eventos com session_id ausente ou com event_type fora do mapeamento
# não entram na agregação (nada é inventado). Comportamento sem dados:
# enquanto `conversation_events` não existir no catálogo, a Gold
# materializa vazia com o schema documentado.

# event_type (docs/data_model.md §13) → coluna da Gold (docs/data_model.md §16).
EVENT_TYPE_MAPPING = {
    "message_received": "message_count",
    "question_asked": "question_count",
    "product_search": "products_consulted",
    "recommendation_created": "recommendations_created",
    "quote_created": "quotes_created",
    "approval_requested": "approvals_requested",
    "approval_resolved": "approvals_resolved",
    "payment_simulated": "payments_simulated",
    "document_generated": "documents_generated",
    "handoff_to_human": "handoffs_to_human",
    "error": "errors",
}

SCHEMA = (
    "session_id STRING, message_count INT, question_count INT, products_consulted INT, "
    "recommendations_created INT, quotes_created INT, approvals_requested INT, "
    "approvals_resolved INT, payments_simulated INT, documents_generated INT, "
    "handoffs_to_human INT, errors INT"
)


def build_rows(events):
    """Agrega eventos de conversa por sessão.

    Entrada: lista de dicts no schema de conversation_events.
    Saída: lista de dicts no schema da Gold, uma linha por session_id,
    ordenada por session_id (determinística).
    """
    sessions = {}
    for event in events:
        session_id = event.get("session_id")
        if session_id is None:
            continue
        column = EVENT_TYPE_MAPPING.get(event.get("event_type"))
        if column is None:
            continue
        stats = sessions.setdefault(
            session_id, {name: 0 for name in EVENT_TYPE_MAPPING.values()}
        )
        stats[column] += 1
    rows = [{"session_id": session_id, **stats} for session_id, stats in sessions.items()]
    rows.sort(key=lambda row: row["session_id"])
    return rows


@_materialized_view(
    comment="Gold: auditoria da conversa e das ferramentas por sessão (docs/data_model.md §16)",
)
def gold_conversation_audit():
    events = (
        [r.asDict() for r in spark.read.table("conversation_events").collect()]
        if "conversation_events" in _existing_tables()
        else []
    )
    return spark.createDataFrame(build_rows(events), schema=SCHEMA)
