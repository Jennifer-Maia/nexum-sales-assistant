"""Helpers da interface de chat (app/chat.py), testáveis sem Streamlit.

A lógica de negócio continua exclusivamente no agente e nas seis
ferramentas; este módulo só formata e coordena a exibição e os botões
da UI local. Nenhuma regra comercial é duplicada aqui.
"""

SUMMARY_KEYS = (
    "quote_id",
    "approval_id",
    "payment_id",
    "document_id",
    "result_count",
    "inventory_status",
    "quote_status",
    "approval_status",
    "payment_status",
    "document_status",
    "search_status",
    "error_code",
    "message",
)


def summarize_tool_result(item):
    """Linha compacta de exibição para um resultado de ferramenta."""
    result = item.get("result")
    if not isinstance(result, dict):
        return f"{item.get('name')}: {result}"
    compact = {key: result[key] for key in SUMMARY_KEYS if key in result}
    return f"{item.get('name')} {compact}"


def approval_context(tool_results):
    """Extrai {approval_id, quote_id} de uma solicitação de aprovação.

    Retorna None quando o turno não contém uma solicitação de aprovação
    com approval_id (ex.: a solicitação falhou).
    """
    for item in tool_results or []:
        if item.get("name") != "request_human_approval":
            continue
        result = item.get("result") or {}
        approval_id = result.get("approval_id")
        quote_id = result.get("quote_id")
        if approval_id and quote_id:
            return {"approval_id": approval_id, "quote_id": quote_id}
    return None


def approver_message(approval_id, quote_id, decision, reason=None):
    """Mensagem do aprovador humano (vendor-001) para o agente.

    `decision` é "approved" ou "rejected"; a rejeição exige motivo
    (SPEC request_human_approval).
    """
    base = f"Sou o aprovador vendor-001. A solicitação {approval_id} da cotação {quote_id}."
    if decision == "approved":
        return f"{base} Aprovo."
    return f"{base} Rejeito. Motivo: {reason or 'requisitos não atendidos'}."


def pending_confirmation_label(tool_name):
    """Texto do aviso de confirmação exibido no chat (SPEC agent §8)."""
    return (
        f"Ação sensível pendente: **{tool_name}**. O agente só executará "
        "após a sua confirmação explícita."
    )
