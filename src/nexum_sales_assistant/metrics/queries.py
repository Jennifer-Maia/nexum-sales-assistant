"""Queries SQL e referências testáveis das métricas do Nexum (ADRs 007/008).

Regra vigente: o dashboard lê **somente Gold** (ADR-008). As queries
usam nomes de tabela **nus** (o dashboard Lakeview supre catalog/schema
pela configuração do recurso) e referenciam exclusivamente:

- gold_conversation_audit — sessões (com first_event_at/last_event_at);
- gold_quote_summary — funil comercial;
- gold_agent_operations — operação do agente;
- gold_data_freshness — atualização por camada.

Datasets com agregação/CTE declaram o parâmetro `:data_range` (RANGE
de datas) no dashboard para permitir o filtro global de período;
`ds_agent_turns`/`ds_tool_calls`/`ds_sessions` são seleções simples e
usam filtro por campo (auto-injetado pelo Lakeview). Para validação
via CLI, as mesmas queries são executadas com nomes totalmente
qualificados e datas literais — a semântica é idêntica.

Cada taxa de conversão é UMA query que retorna UMA linha com UMA
coluna numérica `taxa` (DOUBLE 0-1, sem formatação em texto) — o
formato mais simples e compatível com KPI no Lakeview.
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


def _conversion_sql(numerator_stage, denominator_stage):
    """Query de taxa de conversão: 1 linha, 1 coluna numérica `taxa`.

    Fonte: somente Golds (gold_conversation_audit e
    gold_quote_summary). Divisão por zero segura (NULLIF/COALESCE,
    ADR-007); o valor permanece numérico (0-1) para o Lakeview
    formatar como percentual.
    """
    return [
        "WITH funil AS ( ",
        "SELECT 'sessoes' AS etapa, first_event_at AS data FROM gold_conversation_audit ",
        "WHERE first_event_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'cotacoes', created_at FROM gold_quote_summary ",
        "WHERE created_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'aprovacoes', created_at FROM gold_quote_summary ",
        "WHERE approval_status = 'approved' AND created_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'pagamentos_simulados', created_at FROM gold_quote_summary ",
        "WHERE payment_status = 'simulated_success' AND created_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'documentos_simulados', created_at FROM gold_quote_summary ",
        "WHERE status = 'completed' AND created_at BETWEEN :data_range.min AND :data_range.max ",
        "), ",
        "contagens AS (SELECT etapa, COUNT(*) AS total FROM funil GROUP BY etapa) ",
        f"SELECT COALESCE(MAX(CASE WHEN etapa='{numerator_stage}' THEN total END) / ",
        f"NULLIF(MAX(CASE WHEN etapa='{denominator_stage}' THEN total END), 0), 0) AS taxa ",
        "FROM contagens",
    ]


DATASET_QUERIES = {
    # Sessões e contagens por sessão — fonte: gold_conversation_audit.
    # Seleção simples: o filtro de período do dashboard é por campo
    # (first_event_at), auto-injetado pelo Lakeview.
    "ds_sessions": [
        "SELECT session_id, message_count, question_count, products_consulted, ",
        "quotes_created, approvals_requested, approvals_resolved, ",
        "payments_simulated, documents_generated, errors, ",
        "first_event_at, last_event_at ",
        "FROM gold_conversation_audit",
    ],
    # Funil de vendas em granularidade de evento, com a data de cada
    # etapa e rótulos amigáveis para exibição (ordem explícita via
    # coluna `ordem` — o gráfico usa custom-order em `etapa_label`).
    # Fonte do filtro de período (parâmetro :data_range) e dos
    # KPIs/gráficos da página do funil.
    "ds_funnel": [
        "SELECT 'sessoes' AS etapa, 'Sessões' AS etapa_label, 1 AS ordem, first_event_at AS data ",
        "FROM gold_conversation_audit ",
        "WHERE first_event_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'cotacoes', 'Cotações', 2, created_at FROM gold_quote_summary ",
        "WHERE created_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'aprovacoes', 'Aprovações', 3, created_at FROM gold_quote_summary ",
        "WHERE approval_status = 'approved' AND created_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'pagamentos_simulados', 'Pagamentos simulados', 4, created_at FROM gold_quote_summary ",
        "WHERE payment_status = 'simulated_success' AND created_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'documentos_simulados', 'Documentos simulados', 5, created_at FROM gold_quote_summary ",
        "WHERE status = 'completed' AND created_at BETWEEN :data_range.min AND :data_range.max",
    ],
    # Taxas de conversão do funil: UMA query por métrica, UMA linha,
    # UMA coluna numérica (compatível com KPI).
    "ds_conversion_cotacao": _conversion_sql("cotacoes", "sessoes"),
    "ds_conversion_aprovacao": _conversion_sql("aprovacoes", "cotacoes"),
    "ds_conversion_pagamento": _conversion_sql("pagamentos_simulados", "aprovacoes"),
    "ds_conversion_documento": _conversion_sql("documentos_simulados", "pagamentos_simulados"),
    # Funil detalhado: uma linha por etapa com nome amigável,
    # quantidade e percentual numérico (0-1) sobre o total de sessões
    # — tabela simples e compatível com o Lakeview. Percentual com
    # divisão segura (NULLIF — ADR-007) via função de janela; ordem
    # explícita pela coluna `ordem`.
    "ds_funnel_detailed": [
        "WITH funil AS ( ",
        "SELECT 'sessoes' AS etapa, 'Sessões' AS etapa_label, 1 AS ordem, first_event_at AS data ",
        "FROM gold_conversation_audit ",
        "WHERE first_event_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'cotacoes', 'Cotações', 2, created_at FROM gold_quote_summary ",
        "WHERE created_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'aprovacoes', 'Aprovações', 3, created_at FROM gold_quote_summary ",
        "WHERE approval_status = 'approved' AND created_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'pagamentos_simulados', 'Pagamentos simulados', 4, created_at FROM gold_quote_summary ",
        "WHERE payment_status = 'simulated_success' AND created_at BETWEEN :data_range.min AND :data_range.max ",
        "UNION ALL SELECT 'documentos_simulados', 'Documentos simulados', 5, created_at FROM gold_quote_summary ",
        "WHERE status = 'completed' AND created_at BETWEEN :data_range.min AND :data_range.max ",
        "), ",
        "contagens AS ( ",
        "SELECT etapa, etapa_label, ordem, COUNT(*) AS quantidade FROM funil ",
        "GROUP BY etapa, etapa_label, ordem ",
        ") ",
        "SELECT etapa_label, quantidade, ",
        "quantidade / NULLIF(MAX(quantidade) OVER (), 0) AS percentual ",
        "FROM contagens ",
        "ORDER BY ordem",
    ],
    # Operação — chamadas de ferramenta com latência e status.
    # Seleção simples: filtro de período por campo (created_at).
    "ds_tool_calls": [
        "SELECT session_id, tool_name, status, duration_ms, created_at ",
        "FROM gold_agent_operations ",
        "WHERE event_type = 'tool_call'",
    ],
    # Operação — atividade completa do agente.
    # Seleção simples: filtro de período por campo (created_at).
    "ds_agent_turns": [
        "SELECT session_id, event_type, tool_name, status, duration_ms, ",
        "input_tokens, output_tokens, model, cost_estimated, error_message, ",
        "created_at, source ",
        "FROM gold_agent_operations",
    ],
    # Qualidade e segurança — indicadores agregados (estado atual; sem
    # filtro de período: pendentes/rejeições são o estado corrente).
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
    # Custo — tokens e custo por sessão (turnos do agente), com
    # tokens por interação sem divisão por zero. Agregação: filtro de
    # período via parâmetro :data_range.
    "ds_cost": [
        "SELECT session_id, ",
        "COUNT(*) AS interacoes, ",
        "COALESCE(SUM(input_tokens), 0) AS tokens_entrada, ",
        "COALESCE(SUM(output_tokens), 0) AS tokens_saida, ",
        "COALESCE(SUM(cost_estimated), 0) AS custo_estimado, ",
        "(COALESCE(SUM(input_tokens), 0) + COALESCE(SUM(output_tokens), 0)) / NULLIF(COUNT(*), 0) AS tokens_por_interacao, ",
        "MIN(created_at) AS primeira_interacao ",
        "FROM gold_agent_operations ",
        "WHERE event_type = 'turn' ",
        "AND created_at BETWEEN :data_range.min AND :data_range.max ",
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
