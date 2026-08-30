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
            "produtos existentes nos dados estruturados. Não confirma estoque. "
            "measurement_unit deve ser exatamente um dos valores aceitos: "
            "'C' para temperatura (nunca 'celsius' ou '°C'), 'bar' ou 'psi' "
            "para pressure e 'mm/s' para vibration. NÃO use esta ferramenta "
            "quando a mensagem do cliente já cita um product_id específico "
            "(formato PRD-XXXX-###): nesse caso, a disponibilidade é "
            "verificada com check_inventory."
        ),
        "parameters": _schema(
            {
                "session_id": _STRING,
                "category": {"type": "string", "enum": ["temperature", "pressure", "vibration"]},
                "min_required_value": _NUMBER,
                "max_required_value": _NUMBER,
                "measurement_unit": {"type": "string", "enum": ["C", "bar", "psi", "mm/s"]},
                "quantity": _INTEGER,
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
            "solicitada. Somente leitura: nunca altera o estoque. product_id "
            "tem o formato PRD-XXXX-### e deve ser copiado da saída de "
            "search_products. O depósito é sempre o padrão do sistema "
            "(WH-MAIN): NÃO informe warehouse_id."
        ),
        "parameters": _schema(
            {
                "session_id": _STRING,
                "product_id": _STRING,
                "quantity_requested": _INTEGER,
            },
            ["session_id", "product_id", "quantity_requested"],
        ),
        "call": lambda inputs: check_inventory.run(inputs),
    },
    "create_quote": {
        "description": (
            "Cria uma cotação em estado draft para um cliente cadastrado, "
            "congelando os preços do catálogo nos itens. Valida cliente, "
            "produtos e estoque. Não aprova e não reserva estoque. Cada "
            "product_id dos itens tem o formato PRD-XXXX-### e deve ser "
            "copiado da saída de search_products. Não informe valid_until "
            "nem currency: o sistema usa os padrões documentados (validade "
            "de 7 dias e moeda BRL)."
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
            },
            ["session_id", "customer_id", "items"],
        ),
        "call": lambda inputs: create_quote.run(inputs),
    },
    "request_human_approval": {
        "description": (
            "Operação 'request': move a cotação de draft para pending_approval "
            "e cria a solicitação de aprovação humana (usa quote_id). "
            "Operação 'resolve': registra a decisão de um aprovador humano "
            "autorizado (approved/rejected); exige o approval_id exato "
            "retornado pela operação request (formato APR-XXXX) e "
            "resolved_by com o identificador do aprovador. O agente nunca "
            "decide a aprovação por conta própria."
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
