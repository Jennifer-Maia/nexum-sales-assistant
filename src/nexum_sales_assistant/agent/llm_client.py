"""Cliente da Foundation Model API (ADR-006).

Usa o endpoint pay-per-token pré-provisionado do workspace
(`NEXUM_MODEL_ENDPOINT` ou `model_endpoint` do bundle) no formato
OpenAI-compatible de chat completions com tool calling. A autenticação
vem do runtime (`databricks.sdk.WorkspaceClient` com credenciais
injetadas) — nenhum token ou segredo é armazenado em arquivo.

O custo financeiro não é retornado pela FM API; o consumidor registra
`NULL` para custo e nunca inventa valores (docs/specs/agent.md §10).
"""

import os

from databricks.sdk import WorkspaceClient

DEFAULT_MODEL_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"
ENDPOINT_ENV = "NEXUM_MODEL_ENDPOINT"


class LLMError(RuntimeError):
    """Falha na chamada ao endpoint do modelo."""


class LLMClient:
    """Cliente de chat completions da Foundation Model API."""

    def __init__(self, endpoint=None):
        self.endpoint = endpoint or os.environ.get(ENDPOINT_ENV) or DEFAULT_MODEL_ENDPOINT

    def chat_completion(self, messages, tools=None, max_tokens=1024, temperature=0.0):
        """Retorna um dicionário normalizado.

        Saída: {content, tool_calls, usage, model, finish_reason} —
        `usage` e `model` podem ser None quando a API não fornecer.
        """
        payload = {"messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if tools:
            payload["tools"] = tools
        try:
            response = WorkspaceClient().api_client.do(
                "POST", f"/serving-endpoints/{self.endpoint}/invocations", body=payload
            )
        except Exception as exc:
            raise LLMError(f"LLM endpoint call failed: {exc}") from exc
        return _normalize(response)


def _normalize(response):
    choices = response.get("choices") or []
    message = {}
    if choices:
        message = choices[0].get("message") or {}
    tool_calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        tool_calls.append(
            {
                "id": call.get("id"),
                "name": function.get("name"),
                "arguments": function.get("arguments") or "{}",
            }
        )
    usage = response.get("usage") or {}
    return {
        "content": message.get("content"),
        "tool_calls": tool_calls,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
        "model": response.get("model"),
        "finish_reason": choices[0].get("finish_reason") if choices else None,
    }
