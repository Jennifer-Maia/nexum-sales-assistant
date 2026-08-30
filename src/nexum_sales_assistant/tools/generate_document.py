"""Ferramenta `generate_document` do Nexum Sales Assistant.

Contrato: docs/specs/generate_document.md
Persistência: `documents` e atualização de `quotes`
(docs/data_model.md §8, §12).

Documento simulado sem validade fiscal, financeira ou contábil.
Conforme decisão registrada na migração, a ferramenta monta o conteúdo
completo do documento e registra `content_reference` como o caminho
previsto (`documents/simulated_receipt/<quote_id>.<formato>`), sem
gravar fisicamente o arquivo; o local de armazenamento será definido
em etapa posterior (docs/data_model.md §19).
"""

import uuid
from datetime import datetime, timezone
from nexum_sales_assistant.tools._table_ref import qualified_table

ALLOWED_FORMATS = {"html", "txt"}
DEFAULT_FORMAT = "html"

DOCUMENT_WARNING = "DOCUMENTO SIMULADO — SEM VALIDADE FISCAL, FINANCEIRA OU CONTÁBIL"
FINAL_WARNING = (
    "Este documento foi gerado exclusivamente para demonstração. "
    "Não representa nota fiscal, comprovante de pagamento real ou "
    "documento com validade jurídica, fiscal, financeira ou contábil."
)
GENERATED_MESSAGE = (
    "Documento simulado gerado sem validade fiscal, financeira ou contábil."
)


def build_document_content(
    document_id, quote, items, payment, company_name, document_format=DEFAULT_FORMAT
):
    """Monta o conteúdo do documento conforme a estrutura da SPEC §11.

    Parâmetros:
    - `document_id`: identificador do documento;
    - `quote`: dict com quote_id, customer_id, created_at, total_amount,
      currency;
    - `items`: lista de dicts com product_id, sku, product_name,
      quantity, unit_price, subtotal, currency;
    - `payment`: dict com payment_id;
    - `company_name`: nome da empresa cliente, quando disponível;
    - `document_format`: `html` ou `txt`.
    """
    customer_label = company_name if company_name else quote.get("customer_id")

    if document_format == "txt":
        lines = [
            "Nexum Industrial",
            "DOCUMENTO SIMULADO",
            DOCUMENT_WARNING,
            "",
            f"document_id: {document_id}",
            f"quote_id: {quote.get('quote_id')}",
            f"customer_id: {quote.get('customer_id')}",
            f"cliente: {customer_label}",
            f"data de geracao: {_now()}",
            "",
            "Itens:",
        ]
        for item in items:
            lines.append(
                "- {} | sku {} | {} | qtd {} | unit {} {} | subtotal {} {}".format(
                    item.get("product_id"),
                    item.get("sku"),
                    item.get("product_name"),
                    item.get("quantity"),
                    item.get("unit_price"),
                    item.get("currency"),
                    item.get("subtotal"),
                    item.get("currency"),
                )
            )
        lines += [
            "",
            f"total: {quote.get('total_amount')} {quote.get('currency')}",
            f"pagamento simulado: {payment.get('payment_id')}",
            "",
            FINAL_WARNING,
        ]
        return "\n".join(lines)

    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
        "<td>{} {}</td><td>{} {}</td></tr>".format(
            item.get("product_id"),
            item.get("sku"),
            item.get("product_name"),
            item.get("quantity"),
            item.get("unit_price"),
            item.get("currency"),
            item.get("subtotal"),
            item.get("currency"),
        )
        for item in items
    )
    return (
        "<h1>Nexum Industrial</h1>"
        f"<h2>{DOCUMENT_WARNING}</h2>"
        f"<p><strong>document_id:</strong> {document_id}</p>"
        f"<p><strong>quote_id:</strong> {quote.get('quote_id')}</p>"
        f"<p><strong>customer_id:</strong> {quote.get('customer_id')}</p>"
        f"<p><strong>cliente:</strong> {customer_label}</p>"
        f"<p><strong>data de geracao:</strong> {_now()}</p>"
        "<table border='1'><tr><th>product_id</th><th>sku</th><th>produto</th>"
        "<th>quantidade</th><th>preco unitario</th><th>subtotal</th></tr>"
        f"{rows}</table>"
        f"<p><strong>total:</strong> {quote.get('total_amount')} "
        f"{quote.get('currency')}</p>"
        f"<p><strong>pagamento simulado:</strong> {payment.get('payment_id')}</p>"
        f"<p><em>{FINAL_WARNING}</em></p>"
    )


def run(inputs):
    """Gera o documento simulado conforme a SPEC generate_document.

    Saída: dicionário conforme SPEC §13 (sucesso), §9 (idempotência),
    §14 (falha de pagamento) ou erros §6–§7.
    """
    session_id = inputs.get("session_id")
    quote_id = inputs.get("quote_id")
    requested_by = inputs.get("requested_by")
    document_format = inputs.get("document_format") or DEFAULT_FORMAT

    error = _validate(inputs)
    if error is not None:
        _record_event(session_id, "document_generated", quote_id, _content(error))
        return error

    spark = _spark()

    try:
        quote_rows = spark.table(qualified_table("quotes")).filter(f"quote_id = '{quote_id}'").collect()
    except Exception as exc:
        return _fail_data(f"quotes is not available: {exc}", session_id, quote_id)
    if not quote_rows:
        result = _error("QUOTE_NOT_FOUND", "The quote could not be found", session_id, quote_id)
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result
    quote = quote_rows[0].asDict()

    if quote.get("session_id") != session_id:
        result = _error(
            "SESSION_MISMATCH", "the session does not match the quote", session_id, quote_id
        )
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result

    try:
        item_count = spark.table(qualified_table("quote_items")).filter(f"quote_id = '{quote_id}'").count()
    except Exception as exc:
        return _fail_data(f"quote_items is not available: {exc}", session_id, quote_id)
    if item_count == 0:
        result = _error("QUOTE_WITHOUT_ITEMS", "The quote does not have items", session_id, quote_id)
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result

    if quote.get("total_amount") is None or quote.get("total_amount") <= 0:
        result = _error("INVALID_QUOTE_TOTAL", "the quote total is null or invalid", session_id, quote_id)
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result

    # Idempotência — SPEC §9.
    try:
        document_rows = spark.table(qualified_table("documents")).filter(
            f"quote_id = '{quote_id}'"
        ).collect()
    except Exception as exc:
        return _fail_data(f"documents is not available: {exc}", session_id, quote_id)
    if document_rows:
        existing = document_rows[0].asDict()
        result = {
            "document_status": "already_generated",
            "document_id": existing.get("document_id"),
            "quote_id": quote_id,
            "message": "A simulated document already exists for this quote",
        }
        _record_event(session_id, "document_generated", existing.get("document_id"), _content(result))
        return result

    # Pagamento simulado bem-sucedido obrigatório — SPEC §7.
    try:
        payment_rows = spark.table(qualified_table("payments")).filter(
            f"quote_id = '{quote_id}'"
        ).collect()
    except Exception as exc:
        return _fail_data(f"payments is not available: {exc}", session_id, quote_id)

    if not payment_rows:
        result = {
            "document_status": "payment_required",
            "error_code": "SUCCESSFUL_SIMULATED_PAYMENT_REQUIRED",
            "quote_id": quote_id,
            "message": "A successful simulated payment is required before document generation",
        }
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result

    payment = payment_rows[0].asDict()
    if payment.get("status") == "simulated_failure":
        result = {
            "document_status": "payment_failed",
            "error_code": "PAYMENT_SIMULATION_FAILED",
            "quote_id": quote_id,
            "message": "The simulated payment did not succeed. No document was generated.",
        }
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result
    if not payment.get("simulated"):
        result = {
            "document_status": "payment_required",
            "error_code": "PAYMENT_NOT_SIMULATED",
            "quote_id": quote_id,
            "message": "The related payment is not marked as simulated",
        }
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result
    if payment.get("status") != "simulated_success":
        result = {
            "document_status": "payment_required",
            "error_code": "SUCCESSFUL_SIMULATED_PAYMENT_REQUIRED",
            "quote_id": quote_id,
            "message": "A successful simulated payment is required before document generation",
        }
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result
    if payment.get("amount") is not None and payment.get("amount") != quote.get("total_amount"):
        result = {
            "document_status": "payment_required",
            "error_code": "PAYMENT_AMOUNT_MISMATCH",
            "quote_id": quote_id,
            "message": "The simulated payment amount does not match the quote total",
        }
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result

    # Estado da cotação — SPEC §8.
    if quote.get("status") != "paid":
        result = {
            "document_status": "payment_required",
            "error_code": "QUOTE_NOT_PAID",
            "quote_id": quote_id,
            "message": "The quote must be in status 'paid' before document generation",
        }
        _record_event(session_id, "document_generated", quote_id, _content(result))
        return result

    # Dados do documento — SPEC §10.
    try:
        item_rows = spark.table(qualified_table("quote_items")).filter(f"quote_id = '{quote_id}'").collect()
    except Exception as exc:
        return _fail_data(f"quote_items is not available: {exc}", session_id, quote_id)
    try:
        catalog_rows = spark.table(qualified_table("gold_product_catalog")).collect()
    except Exception as exc:
        return _fail_data(f"gold_product_catalog is not available: {exc}", session_id, quote_id)
    catalog = {r.asDict().get("product_id"): r.asDict() for r in catalog_rows}
    items = []
    for row in item_rows:
        item = row.asDict()
        product = catalog.get(item.get("product_id")) or {}
        items.append(
            {
                "product_id": item.get("product_id"),
                "sku": product.get("sku"),
                "product_name": product.get("product_name"),
                "quantity": item.get("quantity"),
                "unit_price": item.get("unit_price"),
                "subtotal": item.get("subtotal"),
                "currency": quote.get("currency"),
            }
        )
    company_name = _company_name(spark, quote.get("customer_id"))

    document_id = "DOC-" + uuid.uuid4().hex[:8].upper()
    content_reference = f"documents/simulated_receipt/{quote_id}.{document_format}"
    content = build_document_content(
        document_id, quote, items, payment, company_name, document_format
    )

    # Persistência — SPEC §12: documento explicitamente simulado.
    spark.createDataFrame(
        [
            (
                document_id,
                quote_id,
                "simulated_receipt",
                False,
                content_reference,
                datetime.now(timezone.utc),
            )
        ],
        schema=(
            "document_id STRING, quote_id STRING, document_type STRING, "
            "has_fiscal_value BOOLEAN, content_reference STRING, created_at TIMESTAMP"
        ),
    ).write.mode("append").saveAsTable(qualified_table("documents"))
    spark.sql(
        "UPDATE {} SET status = 'completed', document_id = '{}' "
        "WHERE quote_id = '{}'".format(qualified_table("quotes"), document_id, quote_id)
    )

    result = {
        "document_status": "generated",
        "document_id": document_id,
        "quote_id": quote_id,
        "document_type": "simulated_receipt",
        "has_fiscal_value": False,
        "document_format": document_format,
        "content_reference": content_reference,
        "quote_status": "completed",
        "message": GENERATED_MESSAGE,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    # Conteúdo montado conforme a SPEC §11; a gravação física do arquivo
    # será definida quando o local de armazenamento for decidido.
    _record_event(session_id, "document_generated", document_id, _content(result, content))
    return result


def _validate(inputs):
    """Validações de entrada da SPEC §6."""
    session_id = inputs.get("session_id")
    if not session_id:
        return _error("MISSING_SESSION_ID", "session_id is required", None, None)
    quote_id = inputs.get("quote_id")
    if not quote_id:
        return _error("MISSING_QUOTE_ID", "quote_id is required", session_id, None)
    if not inputs.get("requested_by"):
        return _error("MISSING_REQUESTED_BY", "requested_by is required", session_id, quote_id)
    document_format = inputs.get("document_format")
    if document_format is not None and document_format not in ALLOWED_FORMATS:
        return _error(
            "INVALID_DOCUMENT_FORMAT",
            "document_format must be 'html' or 'txt'",
            session_id,
            quote_id,
        )
    return None


def _company_name(spark, customer_id):
    """Nome da empresa cliente em `silver_companies`, quando disponível (SPEC §10)."""
    try:
        rows = spark.table(qualified_table("silver_companies")).filter(
            f"company_id = '{customer_id}'"
        ).collect()
    except Exception:
        return None
    if not rows:
        return None
    row = rows[0].asDict()
    return row.get("company_name") or row.get("name")


def _error(code, message, session_id, quote_id):
    return {
        "session_id": session_id,
        "quote_id": quote_id,
        "document_status": "validation_error",
        "error_code": code,
        "message": message,
    }


def _fail_data(message, session_id, quote_id):
    return {
        "session_id": session_id,
        "quote_id": quote_id,
        "document_status": "data_error",
        "error_code": "DATA_ERROR",
        "message": message,
    }


def _content(result, content=None):
    """Conteúdo do evento de auditoria (SPEC §16)."""
    event = {
        "document_status": result.get("document_status"),
        "document_id": result.get("document_id"),
        "quote_id": result.get("quote_id"),
        "error_code": result.get("error_code"),
        "message": result.get("message"),
    }
    if content is not None:
        event["content_reference"] = result.get("content_reference")
    return event


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _spark():
    try:
        from databricks.sdk.runtime import spark

        return spark
    except Exception:
        from pyspark.sql import SparkSession

        return SparkSession.builder.getOrCreate()


def _record_event(session_id, event_type, tool_reference_id, content):
    """Registra o evento de auditoria em conversation_events (SPEC §16)."""
    spark = _spark()
    row = spark.createDataFrame(
        [
            (
                "EVT-" + uuid.uuid4().hex[:8].upper(),
                session_id,
                event_type,
                "system",
                _json_dumps(content),
                "generate_document",
                tool_reference_id,
                datetime.now(timezone.utc),
            )
        ],
        schema=(
            "event_id STRING, session_id STRING, event_type STRING, actor STRING, "
            "content STRING, tool_name STRING, tool_reference_id STRING, created_at TIMESTAMP"
        ),
    )
    row.write.mode("append").saveAsTable(qualified_table("conversation_events"))


def _json_dumps(content):
    import json

    return json.dumps(content, ensure_ascii=False, default=str)
