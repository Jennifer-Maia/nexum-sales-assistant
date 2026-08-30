"""Chat local do Nexum Sales Assistant (Streamlit).

Interface simples para demonstrar o agente já implementado: usa
Databricks Connect (sessão Spark real no compute serverless do
workspace), o agente de `src/nexum_sales_assistant/agent/` e as seis
ferramentas, gravando nas MESMAS tabelas do Databricks (o dashboard
Lakeview continua funcionando sem alteração).

Como rodar (veja o README):

    set DATABRICKS_CONFIG_PROFILE=jornada
    set NEXUM_CATALOG=workspace
    set NEXUM_SCHEMA=dev
    uv run streamlit run app/chat.py

Uma sessão por execução do app (limitação documentada). O estado do
agente (confirmações pendentes) vive nesta execução.
"""

import uuid

import streamlit as st

from nexum_sales_assistant.agent.agent import Agent
from nexum_sales_assistant.chat import (
    approval_context,
    approver_message,
    pending_confirmation_label,
    summarize_tool_result,
)
from nexum_sales_assistant.runtime_local import (
    ensure_environment,
    get_spark,
    is_expired_session_error,
    reset_spark,
)

st.set_page_config(page_title="Nexum Sales Assistant", page_icon="🤝")

APPROVER = "vendor-001"


@st.cache_resource
def get_agent():
    """Sessão Spark (Connect) + tabelas runtime + agente, uma única vez."""
    spark = get_spark()
    catalog, schema = ensure_environment(spark)
    return Agent(), catalog, schema


def _run_with_session_retry(fn):
    """Executa fn; se a sessão Connect expirou por inatividade, recria a
    sessão Spark e o agente e tenta mais uma vez (limitação conhecida
    do compute serverless, README)."""
    for attempt in (1, 2):
        try:
            return fn()
        except Exception as exc:
            if not is_expired_session_error(exc) or attempt == 2:
                raise
            reset_spark()
            st.session_state.agent = Agent()
            st.session_state.agent.start_session(st.session_state.session_id)


def _send(session_id, message, actor="customer"):
    """Envia a mensagem ao agente e registra o turno no estado."""
    outcome = _run_with_session_retry(
        lambda: st.session_state.agent.process_message(session_id, message, actor=actor)
    )
    st.session_state.messages.append(
        {
            "actor": actor,
            "text": message,
            "tool_results": [],
            "pending": None,
        }
    )
    st.session_state.messages.append(
        {
            "actor": "assistant",
            "text": outcome["reply"],
            "tool_results": outcome.get("tool_results") or [],
            "pending": outcome.get("pending_confirmation"),
        }
    )
    # Contexto de aprovação do turno, para os botões aprovar/rejeitar.
    context = approval_context(outcome.get("tool_results") or [])
    st.session_state.approval = context
    return outcome


def _render_turn(entry):
    """Renderiza um turno do histórico."""
    avatar = {"customer": "🧑‍💼", "assistant": "🤖", "approver": "✅"}.get(entry["actor"])
    with st.chat_message(entry["actor"], avatar=avatar):
        st.markdown(entry["text"])
        if entry["actor"] == "assistant" and entry["tool_results"]:
            with st.expander("Ferramentas chamadas"):
                for item in entry["tool_results"]:
                    st.caption(f"🔧 {summarize_tool_result(item)}")
        if entry.get("pending"):
            st.warning(pending_confirmation_label(entry["pending"]))


# ----------------------------------------------------------------------
# Inicialização da sessão local
# ----------------------------------------------------------------------
if "agent" not in st.session_state:
    st.session_state.agent, catalog, schema = get_agent()
    st.session_state.catalog = catalog
    st.session_state.schema = schema
    st.session_state.session_id = "SES-CHAT-" + uuid.uuid4().hex[:6].upper()
    st.session_state.messages = []
    st.session_state.approval = None
    _run_with_session_retry(
        lambda: st.session_state.agent.start_session(st.session_state.session_id)
    )

st.title("Nexum Sales Assistant")
st.caption("Chat local de demonstração — dados reais do Databricks, pagamento simulado.")

with st.sidebar:
    st.markdown("**Sessão**")
    st.code(st.session_state.session_id)
    st.markdown("**Catálogo/schema**")
    st.code(f"{st.session_state.catalog}.{st.session_state.schema}")
    st.markdown(
        "Aprovação humana obrigatória antes do pagamento simulado. "
        "Os botões abaixo simulam o aprovador `vendor-001`."
    )

# ----------------------------------------------------------------------
# Histórico
# ----------------------------------------------------------------------
for entry in st.session_state.messages:
    _render_turn(entry)

# ----------------------------------------------------------------------
# Botões de demonstração: confirmação pendente e aprovação humana
# ----------------------------------------------------------------------
last = st.session_state.messages[-1] if st.session_state.messages else None

if last and last["actor"] == "assistant" and last.get("pending"):
    if st.button("✅ Confirmar ação pendente", type="primary"):
        _send(st.session_state.session_id, "Sim, confirmo os itens e valores apresentados.")

if st.session_state.approval:
    context = st.session_state.approval
    st.info(
        f"💼 Solicitação de aprovação pendente: **{context['approval_id']}** "
        f"(cotação {context['quote_id']})."
    )
    col_approve, col_reject = st.columns(2)
    with col_approve:
        if st.button("✅ Aprovar (vendor-001)"):
            _send(
                st.session_state.session_id,
                approver_message(context["approval_id"], context["quote_id"], "approved"),
                actor="approver",
            )
            st.rerun()
    with col_reject:
        if st.button("❌ Rejeitar (vendor-001)"):
            _send(
                st.session_state.session_id,
                approver_message(
                    context["approval_id"],
                    context["quote_id"],
                    "rejected",
                    reason="requisitos técnicos não atendidos.",
                ),
                actor="approver",
            )
            st.rerun()

# ----------------------------------------------------------------------
# Entrada do chat
# ----------------------------------------------------------------------
if message := st.chat_input("Descreva a necessidade do cliente…"):
    _send(st.session_state.session_id, message, actor="customer")
    st.rerun()
