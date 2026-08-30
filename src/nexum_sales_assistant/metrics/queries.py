"""Queries SQL e referências testáveis das métricas do Nexum (ADR-007).

As queries usam nomes de tabela **nus**: o dashboard Lakeview supre o
catalog/schema pela configuração do recurso (nada de `sample_*`, nada
de tabelas de outros projetos). Para validação via CLI, as mesmas
queries são executadas com nomes totalmente qualificados — a semântica
é idêntica.

Fontes das métricas (cada query declara a sua):

- funil: conversation_events (sessões), quotes, approvals, payments,
  documents;
- operação: agent_events (latência, tokens, modelo, status) e
  conversation_events (mensagens);
- qualidade/segurança: conversation_events (recusas, bloqueios),
  approvals (pendentes/rejeições), agent_events (erros, validação);
- custo: agent_events (tokens; custo permanece 0/NULL — a FM API não
  retorna custo financeiro, ADR-007);
- atualização: contagens e _ingestion_timestamp das camadas
  Bronze/Silver e contagens das Golds.
"""

# Tabelas permitidas nas queries (isolamento de catalog/schema e de
# projeto: nada de sample_*, grid_* ou legados).
ALLOWED_TABLES = {
    "conversation_events",
    "agent_events",
    "quotes",
    "approvals",
    "payments",
    "documents",
    "bronze_companies",
    "bronze_products",
    "bronze_inventory",
    "silver_companies",
    "silver_products",
    "silver_inventory",
    "gold_product_catalog",
    "gold_product_availability",
    "gold_quote_summary",
    "gold_conversation_audit",
}

DATASET_QUERIES = {
    # Eventos da conversa — base de sessões, mensagens, recusas e erros.
    "ds_sessions": [
        "SELECT session_id, event_type, actor, tool_name, created_at ",
        "FROM conversation_events",
    ],
    # Funil de vendas — uma linha por etapa, com ordem explícita.
    "ds_funnel": [
        "SELECT 'sessoes' AS etapa, 1 AS ordem, COUNT(DISTINCT session_id) AS total ",
        "FROM conversation_events ",
        "UNION ALL SELECT 'cotacoes', 2, COUNT(*) FROM quotes ",
        "UNION ALL SELECT 'aprovacoes', 3, COUNT(*) FROM approvals WHERE status = 'approved' ",
        "UNION ALL SELECT 'pagamentos_simulados', 4, COUNT(*) FROM payments ",
        "WHERE status = 'simulated_success' ",
        "UNION ALL SELECT 'documentos_simulados', 5, COUNT(*) FROM documents ",
        "ORDER BY ordem",
    ],
    # Operação — chamadas de ferramenta com latência e status.
    "ds_tool_calls": [
        "SELECT session_id, tool_name, status, duration_ms, created_at ",
        "FROM agent_events ",
        "WHERE event_type = 'tool_call'",
    ],
    # Operação — turnos do agente (tokens, modelo, duração, erros).
    "ds_agent_turns": [
        "SELECT session_id, event_type, tool_name, status, duration_ms, ",
        "input_tokens, output_tokens, model, cost_estimated, error_message, created_at ",
        "FROM agent_events",
    ],
    # Qualidade e segurança — indicadores agregados com origem declarada.
    "ds_quality": [
        "SELECT 'aprovacoes_pendentes' AS indicador, COUNT(*) AS total ",
        "FROM approvals WHERE status = 'pending' ",
        "UNION ALL SELECT 'rejeicoes', COUNT(*) FROM approvals WHERE status = 'rejected' ",
        "UNION ALL SELECT 'recusas', COUNT(*) FROM conversation_events ",
        "WHERE event_type = 'refusal' ",
        "UNION ALL SELECT 'bloqueios_ferramenta', COUNT(*) FROM conversation_events ",
        "WHERE event_type = 'tool_selection_blocked' ",
        "UNION ALL SELECT 'falhas_validacao', COUNT(*) FROM agent_events ",
        "WHERE status IN ('validation_error', 'data_error') ",
        "UNION ALL SELECT 'erros_agente', COUNT(*) FROM agent_events ",
        "WHERE event_type = 'agent_error' ",
        "ORDER BY indicador",
    ],
    # Custo — por sessão; custo_estimado permanece 0 quando NULL (ADR-007).
    "ds_cost": [
        "SELECT session_id, ",
        "COUNT(*) AS interacoes, ",
        "COALESCE(SUM(input_tokens), 0) AS tokens_entrada, ",
        "COALESCE(SUM(output_tokens), 0) AS tokens_saida, ",
        "COALESCE(SUM(cost_estimated), 0) AS custo_estimado, ",
        "MIN(created_at) AS primeira_interacao ",
        "FROM agent_events ",
        "GROUP BY session_id ",
        "ORDER BY session_id",
    ],
    # Atualização dos dados — contagens e último timestamp de ingestão.
    "ds_update": [
        "SELECT 'bronze_companies' AS tabela, COUNT(*) AS registros, ",
        "MAX(_ingestion_timestamp) AS atualizado_em FROM bronze_companies ",
        "UNION ALL SELECT 'bronze_products', COUNT(*), MAX(_ingestion_timestamp) FROM bronze_products ",
        "UNION ALL SELECT 'bronze_inventory', COUNT(*), MAX(_ingestion_timestamp) FROM bronze_inventory ",
        "UNION ALL SELECT 'silver_companies', COUNT(*), MAX(_ingestion_timestamp) FROM silver_companies ",
        "UNION ALL SELECT 'silver_products', COUNT(*), MAX(_ingestion_timestamp) FROM silver_products ",
        "UNION ALL SELECT 'silver_inventory', COUNT(*), MAX(_ingestion_timestamp) FROM silver_inventory ",
        "UNION ALL SELECT 'gold_product_catalog', COUNT(*), CAST(NULL AS TIMESTAMP) FROM gold_product_catalog ",
        "UNION ALL SELECT 'gold_product_availability', COUNT(*), CAST(NULL AS TIMESTAMP) FROM gold_product_availability ",
        "UNION ALL SELECT 'gold_quote_summary', COUNT(*), CAST(NULL AS TIMESTAMP) FROM gold_quote_summary ",
        "UNION ALL SELECT 'gold_conversation_audit', COUNT(*), CAST(NULL AS TIMESTAMP) FROM gold_conversation_audit ",
        "UNION ALL SELECT 'conversation_events', COUNT(*), MAX(created_at) FROM conversation_events ",
        "UNION ALL SELECT 'agent_events', COUNT(*), MAX(created_at) FROM agent_events ",
        "ORDER BY tabela",
    ],
}


def funnel_counts(sessions, quotes, approvals_approved, payments_success, documents):
    """Referência testável do funil de vendas (mesma semântica do SQL).

    Entradas: coleções/contagens de cada etapa. Dados vazios produzem
    zeros (COUNT sobre tabelas vazias), sem erro.
    """
    return {
        "sessoes": len(sessions),
        "cotacoes": len(quotes),
        "aprovacoes": len(approvals_approved),
        "pagamentos_simulados": len(payments_success),
        "documentos_simulados": len(documents),
    }


def safe_rate(numerator, denominator):
    """Taxa sem divisão por zero (ADR-007): denominador zero → 0.0."""
    if not denominator:
        return 0.0
    return numerator / denominator
