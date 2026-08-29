"""Ferramenta `request_human_approval` do Nexum Sales Assistant.

Contrato: docs/specs/request_human_approval.md
Persistência: `quotes` e `approvals` (docs/data_model.md §8, §10;
ADR-003 separa `quotes.approved_by` de `approvals.resolved_by`).

A aprovação humana é obrigatória antes do pagamento simulado. O
assistente não pode aprovar uma cotação em seu próprio nome.
"""

import uuid
from datetime import datetime, timezone

# Lista simples de aprovadores da demonstração (SPEC §9). Placeholder
# temporário: será substituída pela lista documentada nos dados
# sintéticos (etapa 01-bronze). O id usado nos exemplos das SPECs é
# `vendor-001`.
APPROVERS = {"vendor-001"}

ALLOWED_DECISIONS = {"approved", "rejected"}


def run(inputs):
    """Executa a operação `request` ou `resolve` conforme a SPEC.

    Saída: dicionário conforme SPEC §7 (solicitação), §11 (aprovação),
    §12 (rejeição) ou erros de validação §5/§9.
    """
    operation = inputs.get("operation")
    if operation == "request":
        return _request(inputs)
    if operation == "resolve":
        return _resolve(inputs)
    return _error(
        "INVALID_OPERATION", "operation must be 'request' or 'resolve'", inputs.get("session_id")
    )


def _request(inputs):
    session_id = inputs.get("session_id")
    quote_id = inputs.get("quote_id")
    requested_by = inputs.get("requested_by")

    if not session_id:
        return _error("MISSING_SESSION_ID", "session_id is required", None)
    if not quote_id:
        return _error("MISSING_QUOTE_ID", "quote_id is required", session_id)
    if not requested_by:
        return _error("MISSING_REQUESTED_BY", "requested_by is required", session_id)

    spark = _spark()

    # Validações da SPEC §5.
    try:
        quote_rows = spark.table("quotes").filter(f"quote_id = '{quote_id}'").collect()
    except Exception as exc:
        return _fail_data(f"quotes is not available: {exc}", session_id)
    if not quote_rows:
        result = _error("QUOTE_NOT_FOUND", "The quote could not be found", session_id)
        _record_event(session_id, "approval_requested", quote_id, _content(result))
        return result
    quote = quote_rows[0].asDict()

    try:
        item_count = spark.table("quote_items").filter(f"quote_id = '{quote_id}'").count()
    except Exception as exc:
        return _fail_data(f"quote_items is not available: {exc}", session_id)
    if item_count == 0:
        result = _error("QUOTE_WITHOUT_ITEMS", "The quote does not have items", session_id)
        _record_event(session_id, "approval_requested", quote_id, _content(result))
        return result

    if quote.get("status") != "draft":
        result = _error(
            "INVALID_QUOTE_STATUS",
            f"quote status must be 'draft' to request approval, found '{quote.get('status')}'",
            session_id,
        )
        _record_event(session_id, "approval_requested", quote_id, _content(result))
        return result

    # Consistência de preço e estoque dos itens (SPEC §5).
    try:
        item_rows = spark.table("quote_items").filter(f"quote_id = '{quote_id}'").collect()
    except Exception as exc:
        return _fail_data(f"quote_items is not available: {exc}", session_id)
    invalid_item = next(
        (
            r.asDict().get("product_id")
            for r in item_rows
            if r.asDict().get("unit_price") is None
            or r.asDict().get("unit_price") < 0
            or r.asDict().get("quantity") is None
            or r.asDict().get("quantity") <= 0
            or r.asDict().get("subtotal") is None
            or r.asDict().get("subtotal") < 0
        ),
        None,
    )
    if invalid_item is not None:
        result = _error(
            "INCONSISTENT_ITEM",
            f"quote has an item with inconsistent price or quantity: {invalid_item}",
            session_id,
        )
        _record_event(session_id, "approval_requested", quote_id, _content(result))
        return result

    total_amount = quote.get("total_amount")
    if total_amount is None or total_amount <= 0:
        result = _error("INVALID_QUOTE_TOTAL", "quote total is invalid", session_id)
        _record_event(session_id, "approval_requested", quote_id, _content(result))
        return result

    # Transição draft → pending_approval e criação da solicitação (SPEC §6).
    approval_id = "APR-" + uuid.uuid4().hex[:8].upper()
    now = datetime.now(timezone.utc)
    spark.createDataFrame(
        [
            (
                approval_id,
                quote_id,
                requested_by,
                None,
                "pending",
                inputs.get("reason"),
                now,
                None,
            )
        ],
        schema=(
            "approval_id STRING, quote_id STRING, requested_by STRING, resolved_by STRING, "
            "status STRING, reason STRING, created_at TIMESTAMP, resolved_at TIMESTAMP"
        ),
    ).write.mode("append").saveAsTable("approvals")
    _update_quote_status(spark, quote_id, "pending_approval")

    result = {
        "approval_status": "requested",
        "approval_id": approval_id,
        "quote_id": quote_id,
        "quote_status": "pending_approval",
        "session_id": session_id,
        "next_action": "human_review",
    }
    _record_event(session_id, "approval_requested", approval_id, _content(result))
    return result


def _resolve(inputs):
    session_id = inputs.get("session_id")
    approval_id = inputs.get("approval_id")
    decision = inputs.get("decision")
    resolved_by = inputs.get("resolved_by")
    reason = inputs.get("reason")

    if not session_id:
        return _error("MISSING_SESSION_ID", "session_id is required", None)
    if not approval_id:
        return _error("MISSING_APPROVAL_ID", "approval_id is required", session_id)
    if decision not in ALLOWED_DECISIONS:
        return _error(
            "INVALID_DECISION",
            "decision must be 'approved' or 'rejected'",
            session_id,
        )
    if not resolved_by:
        return _error("MISSING_RESOLVED_BY", "resolved_by is required", session_id)
    if decision == "rejected" and not reason:
        return _error(
            "MISSING_REJECTION_REASON",
            "reason is required when the decision is 'rejected'",
            session_id,
        )
    if resolved_by not in APPROVERS:
        return _error(
            "UNAUTHORIZED_APPROVER",
            "the approver is not authorized in the demo context",
            session_id,
        )

    spark = _spark()

    # Validações da SPEC §9.
    try:
        approval_rows = spark.table("approvals").filter(
            f"approval_id = '{approval_id}'"
        ).collect()
    except Exception as exc:
        return _fail_data(f"approvals is not available: {exc}", session_id)
    if not approval_rows:
        return _error("APPROVAL_NOT_FOUND", "The approval request could not be found", session_id)
    approval = approval_rows[0].asDict()

    if approval.get("status") != "pending":
        return _error(
            "APPROVAL_ALREADY_RESOLVED",
            "the approval request has already been resolved",
            session_id,
        )

    quote_id = approval.get("quote_id")
    try:
        quote_rows = spark.table("quotes").filter(f"quote_id = '{quote_id}'").collect()
    except Exception as exc:
        return _fail_data(f"quotes is not available: {exc}", session_id)
    if not quote_rows:
        return _error("QUOTE_NOT_FOUND", "The related quote could not be found", session_id)
    quote = quote_rows[0].asDict()

    if quote.get("status") != "pending_approval":
        return _error(
            "INVALID_QUOTE_STATUS",
            "the related quote is not in pending_approval",
            session_id,
        )
    if quote.get("session_id") != session_id:
        return _error(
            "SESSION_MISMATCH",
            "the session does not match the quote",
            session_id,
        )

    now = datetime.now(timezone.utc)

    # Aplicação da decisão (SPEC §10; ADR-003).
    _update_approval(spark, approval_id, decision, resolved_by, reason, now)
    if decision == "approved":
        _update_quote_fields(spark, quote_id, status="approved", approved_by=resolved_by, approved_at=now)
        result = {
            "approval_status": "approved",
            "approval_id": approval_id,
            "quote_id": quote_id,
            "quote_status": "approved",
            "resolved_by": resolved_by,
            "resolved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "next_action": "simulate_payment",
        }
        _record_event(session_id, "approval_resolved", approval_id, _content(result))
        return result

    _update_quote_fields(spark, quote_id, status="rejected", rejection_reason=reason)
    result = {
        "approval_status": "rejected",
        "approval_id": approval_id,
        "quote_id": quote_id,
        "quote_status": "rejected",
        "resolved_by": resolved_by,
        "reason": reason,
        "resolved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_action": "human_follow_up",
    }
    _record_event(session_id, "approval_resolved", approval_id, _content(result))
    return result


def _update_quote_status(spark, quote_id, status):
    spark.sql(
        f"UPDATE quotes SET status = '{status}' WHERE quote_id = '{quote_id}'"
    )


def _update_approval(spark, approval_id, decision, resolved_by, reason, resolved_at):
    reason_sql = "NULL" if reason is None else f"'{reason}'"
    spark.sql(
        "UPDATE approvals SET status = '{}', resolved_by = '{}', reason = {}, "
        "resolved_at = '{}' WHERE approval_id = '{}'".format(
            decision, resolved_by, reason_sql, resolved_at.isoformat(), approval_id
        )
    )


def _update_quote_fields(
    spark, quote_id, status=None, approved_by=None, approved_at=None, rejection_reason=None
):
    """Atualiza os campos de resumo da cotação (SPEC §6; ADR-003).

    Na aprovação, `approved_by`/`approved_at` são copiados da aprovação.
    Na rejeição, esses campos não são preenchidos.
    """
    if status == "approved":
        spark.sql(
            "UPDATE quotes SET status = 'approved', approved_by = '{}', "
            "approved_at = '{}' WHERE quote_id = '{}'".format(
                approved_by, approved_at.isoformat(), quote_id
            )
        )
    elif status == "rejected":
        reason_sql = "NULL" if rejection_reason is None else f"'{rejection_reason}'"
        spark.sql(
            "UPDATE quotes SET status = 'rejected', rejection_reason = {} "
            "WHERE quote_id = '{}'".format(reason_sql, quote_id)
        )


def _error(code, message, session_id):
    return {
        "session_id": session_id,
        "approval_status": "validation_error",
        "error_code": code,
        "message": message,
    }


def _fail_data(message, session_id):
    return {
        "session_id": session_id,
        "approval_status": "data_error",
        "error_code": "DATA_ERROR",
        "message": message,
    }


def _content(result):
    """Conteúdo do evento de auditoria (SPEC §14)."""
    return {
        "approval_status": result.get("approval_status"),
        "approval_id": result.get("approval_id"),
        "quote_id": result.get("quote_id"),
        "quote_status": result.get("quote_status"),
        "resolved_by": result.get("resolved_by"),
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
    """Registra o evento de auditoria em conversation_events (SPEC §14)."""
    spark = _spark()
    row = spark.createDataFrame(
        [
            (
                "EVT-" + uuid.uuid4().hex[:8].upper(),
                session_id,
                event_type,
                "system",
                _json_dumps(content),
                "request_human_approval",
                tool_reference_id,
                datetime.now(timezone.utc),
            )
        ],
        schema=(
            "event_id STRING, session_id STRING, event_type STRING, actor STRING, "
            "content STRING, tool_name STRING, tool_reference_id STRING, created_at TIMESTAMP"
        ),
    )
    row.write.mode("append").saveAsTable("conversation_events")


def _json_dumps(content):
    import json

    return json.dumps(content, ensure_ascii=False, default=str)
