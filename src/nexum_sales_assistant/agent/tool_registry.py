"""Catálogo fechado de ferramentas do agente (docs/specs/agent.md §5).

O LLM pode solicitar somente as seis ferramentas listadas aqui; o loop
do agente bloqueia qualquer outro nome e registra `tool_selection_blocked`.
As validações de negócio continuam dentro de cada ferramenta
(ADR-004: LLM interpreta, código decide).
"""

from nexum_sales_assistant.tools import (
    check_inventory,
    create_quote,
    generate_document,
    request_human_approval,
    search_products,
    simulate_payment,
)

# Solicitante padrão injetado pelo agente quando a ferramenta exige
# `requested_by` e o LLM não forneceu (o solicitante é o assistente,
# conforme docs/data_model.md §10).
DEFAULT_REQUESTED_BY = "assistant"


def _schema(properties, required):
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


_STRING = {"type": "string"}
_NUMBER = {"type": "number"}
_INTEGER = {"type": "integer"}

TOOL_REGISTRY = {
    "search_products": {
        "description": (
            "Busca produtos ativos do catálogo compatíveis com os requisitos "
            "técnicos (categoria, faixa operacional, unidade). Retorna somente "
            "produtos existentes nos dados estruturados. Não confirma estoque."
        ),
        "parameters": _schema(
            {
                "session_id": _STRING,
                "category": {"type": "string", "enum": ["temperature", "pressure", "vibration"]},
                "min_required_value": _NUMBER,
                "max_required_value": _NUMBER,
                "measurement_unit": _STRING,
                "quantity": _INTEGER,
                "use_case": _STRING,
                "limit": _INTEGER,
                "product_ids": {"type": "array", "items": _STRING},
            },
            ["session_id", "category"],
        ),
        "call": lambda inputs: search_products.run(inputs),
    },
    "check_inventory": {
        "description": (
            "Consulta a disponibilidade de um produto para uma quantidade "
            "solicitada. Somente leitura: nunca altera o estoque."
        ),
        "parameters": _schema(
            {
                "session_id": _STRING,
                "product_id": _STRING,
                "quantity_requested": _INTEGER,
                "warehouse_id": _STRING,
            },
            ["session_id", "product_id", "quantity_requested"],
        ),
        "call": lambda inputs: check_inventory.run(inputs),
    },
    "create_quote": {
        "description": (
            "Cria uma cotação em estado draft para um cliente cadastrado, "
            "congelando os preços do catálogo nos itens. Valida cliente, "
            "produtos e estoque. Não aprova e não reserva estoque."
        ),
        "parameters": _schema(
            {
                "session_id": _STRING,
                "customer_id": _STRING,
                "requested_by": _STRING,
                "items": {
                    "type": "array",
                    "items": _schema(
                        {"product_id": _STRING, "quantity": _INTEGER},
                        ["product_id", "quantity"],
                    ),
                },
                "currency": _STRING,
                "valid_until": _STRING,
            },
            ["session_id", "customer_id", "items"],
        ),
        "call": lambda inputs: create_quote.run(inputs),
    },
    "request_human_approval": {
        "description": (
            "Operação 'request': move a cotação de draft para pending_approval "
            "e cria a solicitação de aprovação humana. Operação 'resolve': "
            "registra a decisão de um aprovador humano autorizado "
            "(approved/rejected). O agente nunca decide a aprovação por conta "
            "própria."
        ),
        "parameters": _schema(
            {
                "operation": {"type": "string", "enum": ["request", "resolve"]},
                "session_id": _STRING,
                "quote_id": _STRING,
                "approval_id": _STRING,
                "requested_by": _STRING,
                "decision": {"type": "string", "enum": ["approved", "rejected"]},
                "resolved_by": _STRING,
                "reason": _STRING,
            },
            ["operation", "session_id"],
        ),
        "call": lambda inputs: request_human_approval.run(inputs),
    },
    "simulate_payment": {
        "description": (
            "Registra um pagamento exclusivamente simulado (success/failure) "
            "para uma cotação aprovada. Nunca processa pagamento real; exige "
            "aprovação humana válida."
        ),
        "parameters": _schema(
            {
                "session_id": _STRING,
                "quote_id": _STRING,
                "requested_by": _STRING,
                "simulation_result": {"type": "string", "enum": ["success", "failure"]},
                "simulation_reference": _STRING,
            },
            ["session_id", "quote_id"],
        ),
        "call": lambda inputs: simulate_payment.run(inputs),
    },
    "generate_document": {
        "description": (
            "Gera o documento simulado (sem validade fiscal, financeira ou "
            "contábil) para uma cotação com pagamento simulado bem-sucedido."
        ),
        "parameters": _schema(
            {
                "session_id": _STRING,
                "quote_id": _STRING,
                "requested_by": _STRING,
                "document_format": {"type": "string", "enum": ["html", "txt"]},
            },
            ["session_id", "quote_id"],
        ),
        "call": lambda inputs: generate_document.run(inputs),
    },
}


def openai_tools():
    """Ferramentas no formato esperado pela Foundation Model API (OpenAI)."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
        for name, spec in TOOL_REGISTRY.items()
    ]
