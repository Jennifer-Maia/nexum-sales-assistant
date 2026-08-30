# Etapa 04 — Ferramentas do agente

## Objetivo

Implementar as seis ferramentas determinísticas do Nexum Sales
Assistant, seguindo os contratos das SPECs em `docs/specs/`.

Princípio obrigatório (ADR-004):

```text
LLM interpreta.
Código valida.
Código consulta.
Código calcula.
Código controla estados.
Humano aprova ações comerciais sensíveis.
```

As ferramentas decidem; o LLM não pode substituir a saída estruturada
de uma ferramenta por uma afirmação própria.

## Documentos obrigatórios

Antes de alterar qualquer arquivo, leia:

- `AGENTS.md`;
- `CLAUDE.md`;
- `docs/prd.md`;
- `docs/data_model.md` (§6–§14);
- `docs/agent_harness.md` (§9–§12);
- `docs/specs/search_products.md`;
- `docs/specs/check_inventory.md`;
- `docs/specs/create_quote.md`;
- `docs/specs/request_human_approval.md`;
- `docs/specs/simulate_payment.md`;
- `docs/specs/generate_document.md`;
- `docs/adrs/ADR-001-fusao-quotes-orders.md`;
- `docs/adrs/ADR-003-separacao-approved-by-resolved-by.md`;
- `docs/adrs/ADR-004-llm-interpreta-codigo-decide.md`;
- `README.md`.

## Ferramentas a implementar

| Ferramenta | SPEC | Fonte de dados |
|---|---|---|
| `search_products` | `docs/specs/search_products.md` | `gold_product_catalog` |
| `check_inventory` | `docs/specs/check_inventory.md` | `gold_product_availability` |
| `create_quote` | `docs/specs/create_quote.md` | `silver_companies`, `gold_product_catalog`, `gold_product_availability` |
| `request_human_approval` | `docs/specs/request_human_approval.md` | `quotes`, `approvals` |
| `simulate_payment` | `docs/specs/simulate_payment.md` | `quotes`, `approvals`, `payments` |
| `generate_document` | `docs/specs/generate_document.md` | `quotes`, `quote_items`, `products`, `payments`, `silver_companies` |

Cada SPEC define entradas, saídas, validações, códigos de erro, regras
de negócio, auditoria e critérios de aceite. A implementação deve
atender também aos casos de erro, limite e bloqueio — não apenas ao
caso feliz (`docs/agent_harness.md` §9).

## Regras transversais

### Estados e transições

A entidade comercial do MVP é `quotes`; não criar `orders` (ADR-001).

Estados permitidos: `draft`, `pending_approval`, `approved`,
`rejected`, `paid`, `completed`.

Transições permitidas conforme `docs/data_model.md` §8 e ADR-001:

```text
draft → pending_approval
pending_approval → approved
pending_approval → rejected
approved → paid
paid → completed
```

Transições inválidas devem ser bloqueadas pelo código, não apenas
descritas em texto.

### Aprovação humana

- obrigatória antes de `simulate_payment` (`docs/agent_harness.md` §12);
- separação entre `quotes.approved_by`/`approved_at` e
  `approvals.resolved_by`/`resolved_at` (ADR-003);
- o agente não pode aprovar uma cotação em seu próprio nome.

### Auditoria

Cada execução deve registrar evento em `conversation_events`, com os
campos e tipos definidos em `docs/data_model.md` §13 e na SPEC
correspondente.

### Pagamento e documento simulados

- `payments.simulated = true` em todas as situações; nenhuma
  integração financeira;
- `documents.has_fiscal_value = false` sempre; aviso visível de
  documento simulado;
- mensagem obrigatória de simulação conforme as SPECs.

## Implementação

- seguir o contrato de cada SPEC sem acrescentar campos, efeitos ou
  regras não documentados;
- persistir em `quotes`, `quote_items`, `approvals`, `payments`,
  `documents` e `conversation_events` conforme `docs/data_model.md`;
- congelar preços na cotação (`docs/specs/create_quote.md` §9);
- consultar estoque sem alterar quantidades
  (`docs/specs/check_inventory.md` §16);
- idempotência de pagamento e documento bem-sucedidos, conforme as
  SPECs;
- validar o cliente em `silver_companies` (ADR-002).

Questões de orquestração ou runtime sem decisão registrada devem ser
sinalizadas e aguardar decisão, não resolvidas por suposição
(`docs/data_model.md` §18).

## Regras de segurança

- Não processar pagamento real.
- Não gerar documento com validade fiscal.
- Não remover a aprovação humana antes do pagamento simulado.
- Não criar entidade comercial não prevista.
- Não alterar `docs/` sem aprovação.
- Não fazer deploy nem commit automaticamente.

## Processo obrigatório

Antes de modificar qualquer arquivo:

1. apresentar o plano de implementação por ferramenta;
2. indicar a SPEC e os ADRs aplicáveis a cada ferramenta;
3. listar arquivos a criar, alterar e remover;
4. listar os testes previstos para cada ferramenta;
5. explicar riscos;
6. aguardar aprovação explícita.

Depois da aprovação:

1. implementar conforme as SPECs aprovadas;
2. criar ou atualizar testes para as regras críticas;
3. executar os testes locais possíveis;
4. executar:

```bash
databricks bundle validate --profile <perfil>
```

5. mostrar o diff produzido;
6. informar os comandos que foram executados;
7. não fazer commit automaticamente.

## Critérios de aceite

A etapa estará concluída quando:

- cada ferramenta atender à SPEC correspondente, incluindo casos de
  erro e bloqueio;
- as transições de `quotes` forem controladas pelo código (ADR-001);
- a aprovação humana for exigida antes do pagamento simulado;
- todo pagamento e documento forem explicitamente simulados;
- toda execução gerar evento em `conversation_events`;
- o bundle passar na validação;
- o README documentar as ferramentas.
