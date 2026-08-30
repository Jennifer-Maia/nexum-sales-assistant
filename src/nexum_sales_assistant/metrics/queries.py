"""Queries SQL e referências testáveis das métricas do Nexum (ADRs 007/008).

Regra vigente: o dashboard lê **somente Gold** (ADR-008). As queries
usam nomes de tabela **nus** (o dashboard Lakeview supre catalog/schema
pela configuração do recurso) e referenciam exclusivamente:

- gold_conversation_audit — sessões e contagens por sessão;
- gold_quote_summary — funil comercial (cotações, aprovações,
  pagamentos e documentos simulados);
- gold_agent_operations — operação do agente (latência, tokens, modelo,
  status, erros, recusas e bloqueios);
- gold_data_freshness — contagens e atualização por camada.

O runtime do agente continua gravando `agent_events` e as tabelas
transacionais; elas não aparecem nas queries do dashboard.

Para validação via CLI, as mesmas queries são executadas com nomes
totalmente qualificados — a semântica é idêntica.
"""

# Tabelas permitidas nas queries: SOMENTE as Golds (ADR-008).
ALLOWED_TABLES = {
    "gold_product_catalog",
    "gold_product_availability",
    "gold_quote_summary",
    "gold_conversation_audit",
    "gold_agent_operations",
    "gold_data_freshness",
}

DATASET_QUERIES = {
    # Sessões e contagens por sessão — fonte: gold_conversation_audit.
    "ds_sessions": [
        "SELECT session_id, message_count, question_count, products_consulted, ",
        "quotes_created, approvals_requested, approvals_resolved, ",
        "payments_simulated, documents_generated, errors ",
        "FROM gold_conversation_audit",
    ],
    # Funil de vendas — fontes: gold_conversation_audit (sessões) e
    # gold_quote_summary (cotações, aprovações, pagamentos, documentos).
    "ds_funnel": [
        "SELECT 'sessoes' AS etapa, 1 AS ordem, COUNT(*) AS total ",
        "FROM gold_conversation_audit ",
        "UNION ALL SELECT 'cotacoes', 2, COUNT(*) FROM gold_quote_summary ",
        "UNION ALL SELECT 'aprovacoes', 3, COUNT(*) FROM gold_quote_summary ",
        "WHERE approval_status = 'approved' ",
        "UNION ALL SELECT 'pagamentos_simulados', 4, COUNT(*) FROM gold_quote_summary ",
        "WHERE payment_status = 'simulated_success' ",
        "UNION ALL SELECT 'documentos_simulados', 5, COUNT(*) FROM gold_quote_summary ",
        "WHERE status = 'completed' ",
        "ORDER BY ordem",
    ],
    # Operação — chamadas de ferramenta com latência e status.
    # Fonte: gold_agent_operations.
    "ds_tool_calls": [
        "SELECT session_id, tool_name, status, duration_ms, created_at ",
        "FROM gold_agent_operations ",
        "WHERE event_type = 'tool_call'",
    ],
    # Operação — atividade completa do agente. Fonte:
    # gold_agent_operations.
    "ds_agent_turns": [
        "SELECT session_id, event_type, tool_name, status, duration_ms, ",
        "input_tokens, output_tokens, model, cost_estimated, error_message, ",
        "created_at, source ",
        "FROM gold_agent_operations",
    ],
    # Qualidade e segurança — fontes: gold_agent_operations (recusas,
    # bloqueios, falhas de validação, erros do agente) e
    # gold_quote_summary (aprovações pendentes e rejeições).
    "ds_quality": [
        "SELECT 'aprovacoes_pendentes' AS indicador, COUNT(*) AS total ",
        "FROM gold_quote_summary WHERE approval_status = 'pending' ",
        "UNION ALL SELECT 'rejeicoes', COUNT(*) FROM gold_quote_summary ",
        "WHERE approval_status = 'rejected' ",
        "UNION ALL SELECT 'recusas', COUNT(*) FROM gold_agent_operations ",
        "WHERE event_type = 'refusal' ",
        "UNION ALL SELECT 'bloqueios_ferramenta', COUNT(*) FROM gold_agent_operations ",
        "WHERE event_type = 'tool_selection_blocked' ",
        "UNION ALL SELECT 'falhas_validacao', COUNT(*) FROM gold_agent_operations ",
        "WHERE status IN ('validation_error', 'data_error') ",
        "UNION ALL SELECT 'erros_agente', COUNT(*) FROM gold_agent_operations ",
        "WHERE event_type = 'agent_error' ",
        "ORDER BY indicador",
    ],
    # Custo — tokens e custo por sessão, a partir dos turnos do agente.
    # Fonte: gold_agent_operations (custo permanece 0 quando NULL —
    # ADR-007).
    "ds_cost": [
        "SELECT session_id, ",
        "COUNT(*) AS interacoes, ",
        "COALESCE(SUM(input_tokens), 0) AS tokens_entrada, ",
        "COALESCE(SUM(output_tokens), 0) AS tokens_saida, ",
        "COALESCE(SUM(cost_estimated), 0) AS custo_estimado, ",
        "MIN(created_at) AS primeira_interacao ",
        "FROM gold_agent_operations ",
        "WHERE event_type = 'turn' ",
        "GROUP BY session_id ",
        "ORDER BY session_id",
    ],
    # Atualização dos dados — fonte: gold_data_freshness (ADR-008).
    "ds_update": [
        "SELECT tabela, camada, registros, atualizado_em ",
        "FROM gold_data_freshness ",
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
