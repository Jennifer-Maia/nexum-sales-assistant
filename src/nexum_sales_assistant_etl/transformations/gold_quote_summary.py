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


# Camada Gold — gold_quote_summary (docs/data_model.md §16; ADR-002).
#
# Visão resumida das cotações, uma linha por quote_id. Combina:
#   - `quotes` e `quote_items`: tabelas transacionais persistidas em
#     tempo de execução pelas ferramentas (create_quote documenta a
#     persistência em `quotes`/`quote_items` conforme docs/data_model.md
#     §8–§9); não existem tabelas silver_quotes/silver_quote_items no
#     MVP, pois essas entidades são criadas em tempo de execução
#     (prompts/01-bronze.md);
#   - `approvals`: registra solicitação/resolução da aprovação
#     (docs/data_model.md §10; ADR-003) — fonte do `approval_status`;
#   - `silver_companies`: fonte canônica de clientes (ADR-002) — fornece
#     `customer_name`; a chave canônica permanece
#     `silver_companies.company_id`, exposta como `customer_id`.
#
# Campos conforme docs/data_model.md §16 e ADR-002:
#   quote_id, customer_id, customer_name, status, total_amount, currency,
#   created_at, approved_at, approved_by, payment_status, item_count
#   (quantidade de itens), total_quantity (quantidade total de produtos)
#   e approval_status (status da aprovação).
#
# Comportamento sem dados: enquanto as tabelas transacionais ainda não
# existirem no catálogo (nenhuma cotação criada), a Gold materializa
# vazia com o schema documentado; nenhuma linha é inventada.
# `approval_status` é o status da resolução mais recente registrada em
# `approvals` para a cotação (por created_at).

SCHEMA = (
    "quote_id STRING, customer_id STRING, customer_name STRING, status STRING, "
    "total_amount DECIMAL(10,2), currency STRING, created_at TIMESTAMP, "
    "approved_at TIMESTAMP, approved_by STRING, payment_status STRING, "
    "item_count INT, total_quantity INT, approval_status STRING"
)


def build_rows(quotes, items, approvals, companies):
    """Monta o resumo de cotações a partir das camadas/runtimes de origem.

    Entrada: listas de dicts de quotes, quote_items, approvals (tabelas
    runtime das ferramentas) e silver_companies.
    Saída: lista de dicts no schema da Gold, uma linha por quote_id
    (nenhum dado é inventado).
    """
    company_names = {
        row["company_id"]: row["company_name"]
        for row in companies
        if row.get("_quality_status") == "valid"
    }

    items_by_quote = {}
    for item in items:
        quote_id = item.get("quote_id")
        if quote_id is None:
            continue
        count, total_quantity = items_by_quote.get(quote_id, (0, 0))
        quantity = item.get("quantity")
        total_quantity += quantity if quantity is not None else 0
        items_by_quote[quote_id] = (count + 1, total_quantity)

    # Status da resolução mais recente por cotação (por created_at).
    latest_approval = {}
    for approval in approvals:
        quote_id = approval.get("quote_id")
        if quote_id is None:
            continue
        created_at = approval.get("created_at")
        previous = latest_approval.get(quote_id)
        if previous is None or (created_at is not None and created_at >= previous[0]):
            latest_approval[quote_id] = (created_at, approval.get("status"))

    rows = []
    for quote in quotes:
        quote_id = quote.get("quote_id")
        if quote_id is None:
            continue
        item_count, total_quantity = items_by_quote.get(quote_id, (0, 0))
        approval_status = latest_approval.get(quote_id, (None, None))[1]
        rows.append(
            {
                "quote_id": quote_id,
                "customer_id": quote.get("customer_id"),
                "customer_name": company_names.get(quote.get("customer_id")),
                "status": quote.get("status"),
                "total_amount": quote.get("total_amount"),
                "currency": quote.get("currency"),
                "created_at": quote.get("created_at"),
                "approved_at": quote.get("approved_at"),
                "approved_by": quote.get("approved_by"),
                "payment_status": quote.get("payment_status"),
                "item_count": item_count,
                "total_quantity": total_quantity,
                "approval_status": approval_status,
            }
        )
    return rows


@_materialized_view(
    comment="Gold: resumo de cotações com itens, aprovação e cliente canônico (ADR-002)",
)
def gold_quote_summary():
    companies = [r.asDict() for r in spark.read.table("silver_companies").collect()]
    quotes = (
        [r.asDict() for r in spark.read.table("quotes").collect()]
        if spark.catalog.tableExists("quotes")
        else []
    )
    items = (
        [r.asDict() for r in spark.read.table("quote_items").collect()]
        if spark.catalog.tableExists("quote_items")
        else []
    )
    approvals = (
        [r.asDict() for r in spark.read.table("approvals").collect()]
        if spark.catalog.tableExists("approvals")
        else []
    )
    return spark.createDataFrame(build_rows(quotes, items, approvals, companies), schema=SCHEMA)
