"""Ferramenta `simulate_payment` do Nexum Sales Assistant.

Contrato: docs/specs/simulate_payment.md
Persistência: `payments` e atualização de `quotes`
(docs/data_model.md §8, §11).

Pagamento exclusivamente simulado: nenhum valor financeiro, fiscal ou
contábil é movimentado. A aprovação humana é obrigatória antes da
simulação (ADR-004).
"""

import uuid
from datetime import datetime, timezone
from nexum_sales_assistant.tools._table_ref import qualified_table

ALLOWED_RESULTS = {"success", "failure"}
FORBIDDEN_RESULTS = {"approved", "confirmed", "real", "completed", "paid"}
MVP_CURRENCY = "BRL"

SIMULATION_MESSAGE = (
    "Este pagamento é uma simulação sem valor financeiro, fiscal ou contábil."
)


def default_simulation_result(inputs):
    """Resultado padrão quando não informado (SPEC §5): `success`."""
    return inputs.get("simulation_result") or "success"


def run(inputs):
    """Executa a simulação de pagamento conforme a SPEC simulate_payment.

    Saída: dicionário conforme SPEC §10 (sucesso), §11 (falha),
    §14 (idempotência) ou erros §6–§7.
    """
    session_id = inputs.get("session_id")
    quote_id = inputs.get("quote_id")
    requested_by = inputs.get("requested_by")
    simulation_result = inputs.get("simulation_result")

    error = _validate(inputs)
    if error is not None:
        _record_event(session_id, "payment_simulated", quote_id, _content(error))
        return error

    spark = _spark()

    try:
        quote_rows = spark.table(qualified_table("quotes")).filter(f"quote_id = '{quote_id}'").collect()
    except Exception as exc:
        return _fail_data(f"quotes is not available: {exc}", session_id, quote_id)
    if not quote_rows:
        result = _error("QUOTE_NOT_FOUND", "The quote could not be found", session_id, quote_id)
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result
    quote = quote_rows[0].asDict()

    if quote.get("session_id") != session_id:
        result = _error(
            "SESSION_MISMATCH", "the session does not match the quote", session_id, quote_id
        )
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result

    try:
        item_count = spark.table(qualified_table("quote_items")).filter(f"quote_id = '{quote_id}'").count()
    except Exception as exc:
        return _fail_data(f"quote_items is not available: {exc}", session_id, quote_id)
    if item_count == 0:
        result = _error("QUOTE_WITHOUT_ITEMS", "The quote does not have items", session_id, quote_id)
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result

    total_amount = quote.get("total_amount")
    if total_amount is None or total_amount <= 0:
        result = _error(
            "INVALID_QUOTE_TOTAL", "the quote total is null or negative", session_id, quote_id
        )
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result

    if quote.get("currency") != MVP_CURRENCY:
        result = _error(
            "INVALID_CURRENCY",
            f"the quote currency must be '{MVP_CURRENCY}' in the MVP",
            session_id,
            quote_id,
        )
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result

    # Idempotência — SPEC §14.
    try:
        payment_rows = spark.table(qualified_table("payments")).filter(
            f"quote_id = '{quote_id}' AND status = 'simulated_success'"
        ).collect()
    except Exception as exc:
        return _fail_data(f"payments is not available: {exc}", session_id, quote_id)
    if payment_rows:
        result = {
            "payment_status": "already_simulated",
            "quote_id": quote_id,
            "message": "A successful simulated payment already exists for this quote",
            "next_action": "generate_document",
        }
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result

    # Aprovação humana obrigatória — SPEC §7 (ADR-004).
    if quote.get("status") != "approved":
        result = _approval_required(quote_id)
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result
    if not quote.get("approved_by") or not quote.get("approved_at"):
        result = _approval_required(quote_id)
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result
    try:
        approval_rows = spark.table(qualified_table("approvals")).filter(
            f"quote_id = '{quote_id}' AND status = 'approved' "
            "AND resolved_by IS NOT NULL AND resolved_at IS NOT NULL"
        ).collect()
    except Exception as exc:
        return _fail_data(f"approvals is not available: {exc}", session_id, quote_id)
    if not approval_rows:
        result = _approval_required(quote_id)
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result

    # Consistência — SPEC §15.
    try:
        item_rows = spark.table(qualified_table("quote_items")).filter(f"quote_id = '{quote_id}'").collect()
    except Exception as exc:
        return _fail_data(f"quote_items is not available: {exc}", session_id, quote_id)
    computed_total = round(
        sum(
            float(r.asDict().get("quantity") or 0) * float(r.asDict().get("unit_price") or 0)
            for r in item_rows
        ),
        2,
    )
    if computed_total != float(total_amount):
        result = _fail_data(
            "the quote total does not match the sum of its items",
            session_id,
            quote_id,
        )
        _record_event(session_id, "payment_simulated", quote_id, _content(result))
        return result

    payment_id = "PAY-" + uuid.uuid4().hex[:8].upper()
    simulation_reference = inputs.get("simulation_reference") or (
        "SIM-PAY-" + uuid.uuid4().hex[:8].upper()
    )
    now = datetime.now(timezone.utc)

    if simulation_result == "failure":
        # SPEC §11: a cotação permanece `approved`.
        spark.createDataFrame(
            [
                (
                    payment_id,
                    quote_id,
                    "simulated_failure",
                    total_amount,
                    quote.get("currency"),
                    True,
                    now,
                )
            ],
            schema=(
                "payment_id STRING, quote_id STRING, status STRING, "
                "amount DECIMAL(10,2), currency STRING, simulated BOOLEAN, created_at TIMESTAMP"
            ),
        ).write.mode("append").saveAsTable(qualified_table("payments"))
        spark.sql(
            f"UPDATE {qualified_table('quotes')} SET payment_status = 'simulated_failure' "
            f"WHERE quote_id = '{quote_id}'"
        )
        result = {
            "payment_status": "simulated_failure",
            "payment_id": payment_id,
            "quote_id": quote_id,
            "quote_status": "approved",
            "amount": total_amount,
            "currency": quote.get("currency"),
            "simulated": True,
            "simulation_reference": simulation_reference,
            "message": "A simulação de pagamento falhou. Nenhum valor real foi movimentado.",
            "next_action": "human_follow_up",
        }
        _record_event(session_id, "payment_simulated", payment_id, _content(result))
        return result

    # SPEC §10: sucesso — registra o pagamento e move a cotação para `paid`.
    spark.createDataFrame(
        [
            (
                payment_id,
                quote_id,
                "simulated_success",
                total_amount,
                quote.get("currency"),
                True,
                now,
            )
        ],
        schema=(
            "payment_id STRING, quote_id STRING, status STRING, "
            "amount DECIMAL(10,2), currency STRING, simulated BOOLEAN, created_at TIMESTAMP"
        ),
    ).write.mode("append").saveAsTable(qualified_table("payments"))
    spark.sql(
        "UPDATE {} SET payment_status = 'simulated_success', status = 'paid' ".format(
            qualified_table("quotes")
        )
        + f"WHERE quote_id = '{quote_id}'"
    )
    result = {
        "payment_status": "simulated_success",
        "payment_id": payment_id,
        "quote_id": quote_id,
        "quote_status": "paid",
        "amount": total_amount,
        "currency": quote.get("currency"),
        "simulated": True,
        "simulation_reference": simulation_reference,
        "message": SIMULATION_MESSAGE,
        "next_action": "generate_document",
    }
    _record_event(session_id, "payment_simulated", payment_id, _content(result))
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
    simulation_result = inputs.get("simulation_result")
    if simulation_result is not None:
        if simulation_result in FORBIDDEN_RESULTS:
            return _error(
                "INVALID_SIMULATION_RESULT",
                "simulation_result must be 'success' or 'failure'",
                session_id,
                quote_id,
            )
        if simulation_result not in ALLOWED_RESULTS:
            return _error(
                "INVALID_SIMULATION_RESULT",
                "simulation_result must be 'success' or 'failure'",
                session_id,
                quote_id,
            )
    return None


def _approval_required(quote_id):
    return {
        "payment_status": "approval_required",
        "error_code": "QUOTE_NOT_APPROVED",
        "quote_id": quote_id,
        "message": "A human-approved quote is required before payment simulation",
    }


def _error(code, message, session_id, quote_id):
    return {
        "session_id": session_id,
        "quote_id": quote_id,
        "payment_status": "validation_error",
        "error_code": code,
        "message": message,
    }


def _fail_data(message, session_id, quote_id):
    return {
        "session_id": session_id,
        "quote_id": quote_id,
        "payment_status": "data_error",
        "error_code": "DATA_ERROR",
        "message": message,
    }


def _content(result):
    """Conteúdo do evento de auditoria (SPEC §16)."""
    return {
        "payment_status": result.get("payment_status"),
        "payment_id": result.get("payment_id"),
        "quote_id": result.get("quote_id"),
        "quote_status": result.get("quote_status"),
        "amount": result.get("amount"),
        "currency": result.get("currency"),
        "simulation_reference": result.get("simulation_reference"),
        "error_code": result.get("error_code"),
        "message": result.get("message"),
    }


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
                "simulate_payment",
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
