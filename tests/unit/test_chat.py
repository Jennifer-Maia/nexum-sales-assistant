"""Testes dos helpers do chat local (app/chat.py), sem Streamlit/Connect.

Cobrem a integração entre o chat e o tool_registry com LLM fake
determinístico (sem custo real, sem API externa): exibição compacta de
resultados, contexto de aprovação, mensagem do aprovador e o fluxo de
confirmação do agente usado pela UI.
"""

import json

from nexum_sales_assistant.agent.agent import Agent
from nexum_sales_assistant.chat import (
    approval_context,
    approver_message,
    pending_confirmation_label,
    summarize_tool_result,
)
from nexum_sales_assistant.tools._table_ref import qualified_table


class FakeLLM:
    """LLM fake determinístico para o fluxo de confirmação do chat."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat_completion(self, messages, tools=None, max_tokens=1024, temperature=0.0):
        self.calls.append({"messages": messages, "tools": tools})
        if not self.responses:
            return {
                "content": "",
                "tool_calls": [],
                "usage": None,
                "model": None,
                "finish_reason": "stop",
            }
        return self.responses.pop(0)


def _call(name, arguments, call_id="call-1"):
    return {"id": call_id, "name": name, "arguments": json.dumps(arguments)}


def _completion(tool_calls=(), content=None):
    return {
        "content": content,
        "tool_calls": list(tool_calls),
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "model": "fake-model",
        "finish_reason": "tool_calls" if tool_calls else "stop",
    }


class TestSummarizeToolResult:
    def test_dict_result_compacted(self):
        line = summarize_tool_result(
            {"name": "create_quote", "result": {"quote_id": "QTE-1", "quote_status": "created"}}
        )
        assert "create_quote" in line
        assert "QTE-1" in line
        assert "quote_status" in line

    def test_non_dict_result(self):
        line = summarize_tool_result({"name": "x", "result": 42})
        assert line == "x: 42"


class TestApprovalContext:
    def test_request_result_with_approval_id(self):
        context = approval_context(
            [
                {"name": "search_products", "result": {}},
                {
                    "name": "request_human_approval",
                    "result": {"approval_id": "APR-1", "quote_id": "QTE-1", "approval_status": "requested"},
                },
            ]
        )
        assert context == {"approval_id": "APR-1", "quote_id": "QTE-1"}

    def test_without_approval_result(self):
        assert approval_context([]) is None
        assert approval_context([{"name": "search_products", "result": {}}]) is None
        assert approval_context(
            [{"name": "request_human_approval", "result": {"error_code": "QUOTE_NOT_FOUND"}}]
        ) is None


class TestApproverMessage:
    def test_approve(self):
        message = approver_message("APR-1", "QTE-1", "approved")
        assert "vendor-001" in message
        assert "APR-1" in message
        assert "QTE-1" in message
        assert "Aprovo" in message

    def test_reject_requires_reason(self):
        message = approver_message("APR-1", "QTE-1", "rejected", reason="escopo errado")
        assert "Rejeito" in message
        assert "escopo errado" in message
        default = approver_message("APR-1", "QTE-1", "rejected")
        assert "requisitos não atendidos" in default


class TestPendingConfirmationLabel:
    def test_label_names_tool(self):
        assert "simulate_payment" in pending_confirmation_label("simulate_payment")


class TestChatFlowIntegration:
    def test_confirmation_flow_via_agent(self, fake_spark):
        # Fluxo usado pelos botões da UI: pedido sensível → aviso de
        # confirmação → "Sim, confirmo." → execução.
        fake_spark.tables[qualified_table("silver_companies")] = [{"company_id": "C0001"}]
        fake_spark.tables[qualified_table("gold_product_catalog")] = []
        llm = FakeLLM(
            [
                _completion(tool_calls=[_call("create_quote", {"customer_id": "C0001", "items": []})]),
                _completion(content="Cotação criada."),
            ]
        )
        agent = Agent(llm=llm)
        first = agent.process_message("SES-1", "Crie uma cotação para C0001")
        assert first["pending_confirmation"] == "create_quote"
        second = agent.process_message("SES-1", "Sim, confirmo os itens e valores apresentados.")
        assert [r["name"] for r in second["tool_results"]] == ["create_quote"]

    def test_approval_buttons_flow_via_agent(self, fake_spark):
        # Após uma solicitação de aprovação, o botão do aprovador envia
        # a mensagem de aprovação e o agente repassa a decisão.
        fake_spark.tables[qualified_table("quotes")] = [
            {
                "quote_id": "QTE-1",
                "customer_id": "C0001",
                "session_id": "SES-1",
                "status": "pending_approval",
                "total_amount": 100.0,
                "currency": "BRL",
                "created_at": None,
                "approved_at": None,
                "approved_by": None,
                "rejection_reason": None,
                "payment_status": "not_started",
                "document_id": None,
            }
        ]
        fake_spark.tables[qualified_table("quote_items")] = [
            {
                "quote_item_id": "QTI-1",
                "quote_id": "QTE-1",
                "product_id": "P",
                "quantity": 1,
                "unit_price": 100.0,
                "subtotal": 100.0,
            }
        ]
        fake_spark.tables[qualified_table("approvals")] = [
            {
                "approval_id": "APR-1",
                "quote_id": "QTE-1",
                "requested_by": "assistant",
                "resolved_by": None,
                "status": "pending",
                "reason": None,
                "created_at": None,
                "resolved_at": None,
            }
        ]
        llm = FakeLLM(
            [
                _completion(
                    tool_calls=[
                        _call(
                            "request_human_approval",
                            {"operation": "resolve", "approval_id": "APR-1", "decision": "approved", "resolved_by": "vendor-001"},
                        )
                    ]
                ),
                _completion(content="Aprovação registrada."),
            ]
        )
        agent = Agent(llm=llm)
        outcome = agent.process_message(
            "SES-1",
            approver_message("APR-1", "QTE-1", "approved"),
            actor="approver",
        )
        result = outcome["tool_results"][0]["result"]
        assert result["approval_status"] == "approved"
