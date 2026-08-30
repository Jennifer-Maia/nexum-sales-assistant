"""Criação idempotente das tabelas runtime do agente e das ferramentas.

As seis ferramentas gravam em tabelas runtime (quotes, quote_items,
approvals, payments, documents, conversation_events) criadas em tempo
de execução (docs/data_model.md §8–§13). Este módulo garante que elas
existem com o schema documentado antes do primeiro uso
(`CREATE TABLE IF NOT EXISTS` — idempotente, sem apagar dados).

`agent_events` é a tabela operacional do agente (ADR-007): registra
latência, tokens, modelo, status e erro por interação — campos que o
schema de `conversation_events` não comporta sem alterar o contrato
das ferramentas.

Todos os nomes usam catalog/schema totalmente qualificados
(docs/data_model.md §19).
"""

from nexum_sales_assistant.tools._table_ref import qualified_table

RUNTIME_SCHEMAS = {
    "conversation_events": (
        "event_id STRING, session_id STRING, event_type STRING, actor STRING, "
        "content STRING, tool_name STRING, tool_reference_id STRING, created_at TIMESTAMP"
    ),
    "quotes": (
        "quote_id STRING, customer_id STRING, session_id STRING, status STRING, "
        "total_amount DECIMAL(10,2), currency STRING, created_at TIMESTAMP, "
        "approved_at TIMESTAMP, approved_by STRING, rejection_reason STRING, "
        "payment_status STRING, document_id STRING"
    ),
    "quote_items": (
        "quote_item_id STRING, quote_id STRING, product_id STRING, "
        "quantity INT, unit_price DECIMAL(10,2), subtotal DECIMAL(10,2)"
    ),
    "approvals": (
        "approval_id STRING, quote_id STRING, requested_by STRING, resolved_by STRING, "
        "status STRING, reason STRING, created_at TIMESTAMP, resolved_at TIMESTAMP"
    ),
    "payments": (
        "payment_id STRING, quote_id STRING, status STRING, amount DECIMAL(10,2), "
        "currency STRING, simulated BOOLEAN, created_at TIMESTAMP"
    ),
    "documents": (
        "document_id STRING, quote_id STRING, document_type STRING, "
        "has_fiscal_value BOOLEAN, content_reference STRING, created_at TIMESTAMP"
    ),
    "agent_events": (
        "event_id STRING, session_id STRING, conversation_event_id STRING, "
        "created_at TIMESTAMP, event_type STRING, tool_name STRING, "
        "result_summary STRING, status STRING, duration_ms BIGINT, "
        "input_tokens INT, output_tokens INT, model STRING, "
        "cost_estimated DECIMAL(18,6), error_message STRING"
    ),
}


def ensure_runtime_tables(spark):
    """Cria as tabelas runtime, se ainda não existirem."""
    for table, schema in RUNTIME_SCHEMAS.items():
        spark.sql(
            f"CREATE TABLE IF NOT EXISTS {qualified_table(table)} ({schema})"
        )
    return list(RUNTIME_SCHEMAS)
