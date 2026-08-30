"""Jornada de demonstração do agente de vendas (ADR-006; SPEC agent §12).

Entry point do job `nexum_sales_assistant_agent_job` (spark_python_task,
serverless). Executa uma conversa completa com LLM real:

```text
busca de produto → consulta de estoque → cotação (draft)
    → solicitação de aprovação → aprovação humana (vendor-001)
    → pagamento simulado → documento simulado
```

As mensagens do cliente são scriptadas; quem interpreta e decide as
chamadas de ferramenta é o modelo (via o loop do agente). O transcript
impresso é a demonstração do desafio. O custo é proporcional aos tokens
(pay-per-token, ADR-006) e os tokens consumidos são registrados em
`agent_events`.

Parâmetros: --catalog, --schema (obrigatórios, repassados pelo bundle);
--session-id, --model-endpoint (opcionais).
"""

import argparse
import os
import uuid
from datetime import datetime, timezone

from nexum_sales_assistant.agent.agent import Agent
from nexum_sales_assistant.agent.schema_bootstrap import ensure_runtime_tables


def _parse_args():
    parser = argparse.ArgumentParser(description="Nexum Sales Assistant — demo do agente")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--model_endpoint", default=None)
    return parser.parse_args()


def _print_turn(actor, text, tool_results=None):
    prefix = {"customer": "CLIENTE", "assistant": "ASSISTENTE", "approver": "APROVADOR"}.get(
        actor, actor.upper()
    )
    print(f"\n=== {prefix} ===")
    print(text)
    for item in tool_results or []:
        result = item["result"]
        if isinstance(result, dict):
            compact = {k: result[k] for k in ("quote_id", "approval_id", "payment_id",
                                              "document_id", "result_count", "inventory_status",
                                              "quote_status", "approval_status", "payment_status",
                                              "document_status", "error_code", "message")
                       if k in result}
            print(f"    [ferramenta {item['name']}] {compact}")
        else:
            print(f"    [ferramenta {item['name']}] {result}")


def main():
    args = _parse_args()

    # Catalog/schema totalmente qualificados (docs/data_model.md §19).
    os.environ["NEXUM_CATALOG"] = args.catalog
    os.environ["NEXUM_SCHEMA"] = args.schema
    if args.model_endpoint:
        os.environ["NEXUM_MODEL_ENDPOINT"] = args.model_endpoint

    from databricks.sdk.runtime import spark

    ensure_runtime_tables(spark)

    session_id = args.session_id or ("SES-DEMO-" + uuid.uuid4().hex[:6].upper())
    agent = Agent()
    agent.start_session(session_id)

    print(f"# Nexum Sales Assistant — demonstração da jornada de vendas")
    print(f"# session_id: {session_id}")
    print(f"# iniciada em: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")

    quote_id = None

    # 1. Necessidade do cliente → busca de produtos.
    outcome = agent.process_message(
        session_id,
        "Preciso monitorar 20 máquinas com temperatura entre 0 °C e 150 °C. "
        "Que sensores vocês têm?",
    )
    _print_turn("customer",
                "Preciso monitorar 20 máquinas com temperatura entre 0 °C e 150 °C. "
                "Que sensores vocês têm?")
    _print_turn("assistant", outcome["reply"], outcome["tool_results"])

    # 2. Seleção de produto → consulta de estoque.
    outcome = agent.process_message(
        session_id,
        "O sensor PRD-TEMP-001 parece adequado. "
        "Tem 20 unidades disponíveis?",
    )
    _print_turn("customer", "O sensor PRD-TEMP-001 parece adequado. "
                "Tem 20 unidades disponíveis?")
    _print_turn("assistant", outcome["reply"], outcome["tool_results"])

    # 3. Cotação para o cliente cadastrado → gate de confirmação.
    outcome = agent.process_message(
        session_id,
        "Quero uma cotação para a empresa C0001 com 20 unidades do produto PRD-TEMP-001.",
    )
    _print_turn("customer", "Quero uma cotação para a empresa C0001 com 20 unidades "
                "do produto PRD-TEMP-001.")
    _print_turn("assistant", outcome["reply"], outcome["tool_results"])
    if outcome.get("pending_confirmation"):
        _print_turn("customer", "Sim, confirmo os itens e valores apresentados.")
        outcome = agent.process_message(
            session_id, "Sim, confirmo os itens e valores apresentados."
        )
        _print_turn("assistant", outcome["reply"], outcome["tool_results"])
    for item in outcome["tool_results"]:
        if item["name"] == "create_quote" and item["result"].get("quote_id"):
            quote_id = item["result"]["quote_id"]

    if not quote_id:
        print("\n# A cotação não foi criada pela conversa; encerrando a demonstração "
              "para inspeção humana (nenhum dado foi inventado).")
        return

    # 3.5. Tentativa de pagamento ANTES da aprovação → bloqueio
    # determinístico (SPEC simulate_payment §7; ADR-004): a ferramenta
    # rejeita com approval_required e nada é alterado.
    outcome = agent.process_message(
        session_id,
        f"Quero simular o pagamento da cotação {quote_id} com sucesso.",
        actor="customer",
    )
    _print_turn("customer", f"Quero simular o pagamento da cotação {quote_id} com sucesso.")
    _print_turn("assistant", outcome["reply"], outcome["tool_results"])
    if outcome.get("pending_confirmation"):
        _print_turn("customer", "Sim, confirmo a simulação do pagamento.")
        outcome = agent.process_message(session_id, "Sim, confirmo a simulação do pagamento.")
        _print_turn("assistant", outcome["reply"], outcome["tool_results"])

    # 4. Solicitação de aprovação humana → gate de confirmação.
    outcome = agent.process_message(
        session_id, f"Encaminhe a cotação {quote_id} para aprovação humana.", actor="customer"
    )
    _print_turn("customer", f"Encaminhe a cotação {quote_id} para aprovação humana.")
    _print_turn("assistant", outcome["reply"], outcome["tool_results"])
    if outcome.get("pending_confirmation"):
        _print_turn("customer", "Sim, confirmo o encaminhamento para aprovação.")
        outcome = agent.process_message(
            session_id, "Sim, confirmo o encaminhamento para aprovação."
        )
        _print_turn("assistant", outcome["reply"], outcome["tool_results"])

    # 5. Decisão do aprovador humano (vendor-001) — repassada pelo agente.
    # O approval_id vem da solicitação criada no turno anterior.
    approval_id = None
    for item in outcome["tool_results"]:
        if item["name"] == "request_human_approval" and item["result"].get("approval_id"):
            approval_id = item["result"]["approval_id"]
    if not approval_id:
        print("\n# A solicitação de aprovação não foi criada; encerrando a "
              "demonstração para inspeção humana.")
        return
    approval_message = (
        f"Sou o aprovador vendor-001. Aprovo a solicitação {approval_id} "
        f"da cotação {quote_id}."
    )
    outcome = agent.process_message(session_id, approval_message, actor="approver")
    _print_turn("approver", f"Aprovo a solicitação {approval_id} da cotação {quote_id} "
                "(vendor-001).")
    _print_turn("assistant", outcome["reply"], outcome["tool_results"])

    # 6. Pagamento simulado após aprovação → gate de confirmação.
    outcome = agent.process_message(
        session_id,
        f"Quero simular o pagamento da cotação {quote_id} com sucesso.",
        actor="customer",
    )
    _print_turn("customer", f"Quero simular o pagamento da cotação {quote_id} com sucesso.")
    _print_turn("assistant", outcome["reply"], outcome["tool_results"])
    if outcome.get("pending_confirmation"):
        _print_turn("customer", "Sim, confirmo a simulação do pagamento.")
        outcome = agent.process_message(session_id, "Sim, confirmo a simulação do pagamento.")
        _print_turn("assistant", outcome["reply"], outcome["tool_results"])

    # 7. Documento simulado após pagamento → gate de confirmação.
    outcome = agent.process_message(
        session_id, f"Quero o documento simulado da cotação {quote_id}.", actor="customer"
    )
    _print_turn("customer", f"Quero o documento simulado da cotação {quote_id}.")
    _print_turn("assistant", outcome["reply"], outcome["tool_results"])
    if outcome.get("pending_confirmation"):
        _print_turn("customer", "Sim, confirmo a geração do documento.")
        outcome = agent.process_message(session_id, "Sim, confirmo a geração do documento.")
        _print_turn("assistant", outcome["reply"], outcome["tool_results"])

    print("\n# Fim da demonstração. Os eventos e métricas estão registrados em "
          "conversation_events e agent_events.")


if __name__ == "__main__":
    main()
