# SPEC — agent (Agente de vendas IA do Nexum Sales Assistant)

## 1. Objetivo

Conduzir a conversa de vendas B2B do Nexum Sales Assistant: interpretar
a necessidade do cliente em linguagem natural, acionar as seis
ferramentas determinísticas autorizadas e comunicar resultados sem
inventar dados comerciais.

Arquitetura: ADR-006 (agente Python executado como job, LLM real via
Foundation Model API, ferramentas in-process).

## 2. Princípio central

```text
LLM interpreta.
Código valida.
Código consulta.
Código calcula.
Código controla estados.
Humano aprova ações comerciais sensíveis.
```

O agente apenas **roteia** mensagens para ferramentas aprovadas e
comunica os resultados estruturados delas. Ele nunca decide sozinho
preço, estoque, prazo, aprovação, pagamento ou documento.

## 3. Responsabilidade

O agente é responsável por:

- manter o `session_id` da conversa;
- interpretar a mensagem do cliente e decidir **qual ferramenta
  aprovada** solicitar (ou responder diretamente);
- chamar as ferramentas exclusivamente pelo catálogo aprovado;
- repassar a entrada e apresentar a saída estruturada da ferramenta;
- registrar cada interação (eventos + métricas operacionais);
- recusar pedidos fora do escopo (injeção, segredos, temas não
  comerciais) e registrar a recusa.

O agente não é responsável por:

- validar regras de negócio (as ferramentas fazem isso);
- alterar estados (as ferramentas fazem isso);
- aprovar cotação em nome de pessoa;
- executar pagamento real ou gerar documento fiscal.

## 4. Persona e público

- **Persona**: assistente de vendas B2B da Nexum Industrial, técnico e
  objetivo, que só afirma o que vem das ferramentas.
- **Público**: cliente B2B já cadastrado em `silver_companies`
  (ADR-002).
- **Idioma**: português do Brasil.

## 5. Ferramentas autorizadas

A lista é fechada e está codificada em
`src/nexum_sales_assistant/agent/tool_registry.py`:

```text
search_products
check_inventory
create_quote
request_human_approval
simulate_payment
generate_document
```

Qualquer outra ferramenta solicitada pelo LLM é **bloqueada** e
registrada como `tool_selection_blocked`.

## 6. Quando cada ferramenta pode ser usada

| Ferramenta | Quando | Exigências |
|---|---|---|
| `search_products` | necessidade com categoria/faixa identificada | validação da própria ferramenta |
| `check_inventory` | após um produto ser selecionado | `product_id` + `quantity_requested` |
| `create_quote` | cliente validado + produtos e estoque confirmados | cliente em `silver_companies` |
| `request_human_approval` | após cotação criada em `draft` | operação `request`; `resolve` só com decisão do aprovador humano |
| `simulate_payment` | somente após aprovação válida | a ferramenta bloqueia sem aprovação |
| `generate_document` | somente após pagamento simulado com sucesso | a ferramenta bloqueia sem pagamento |

O agente deve **solicitar confirmação do cliente** antes de ações
irreversíveis do fluxo (criar cotação, solicitar aprovação, simular
pagamento, gerar documento) e **nunca** decidir pela aprovação humana:
a decisão `approved`/`rejected` vem do aprovador (ex.: `vendor-001`),
apenas repassada pelo agente.

## 7. Informações que precisam vir do banco

Somente as ferramentas fornecem: produto, SKU, especificações, preço,
prazo, estoque, cliente, cotação, aprovação, pagamento e documento. O
agente nunca preenche lacunas com dados próprios.

## 8. Ações que exigem confirmação ou aprovação

- **Confirmação do cliente**: cotação (itens, quantidades, total),
  solicitação de aprovação, simulação de pagamento, geração de
  documento.
- **Aprovação humana obrigatória**: antes de `simulate_payment`
  (docs/data_model.md §8; ADR-004).

## 9. Comportamentos obrigatórios

### Produto inexistente

Repassar o erro estruturado da ferramenta (`product_not_found` /
`no_compatible_product`) e sugerir refinar a busca ou encaminhar para
vendedor humano. Nunca sugerir produto substituto inventado.

### Estoque insuficiente ou ausente

Repassar `insufficient_stock` / `inventory_not_found` /
`stale_inventory` com a quantidade disponível real; não prometer
reposição; encaminhar para humano quando necessário.

### Pedido ambíguo

Fazer pergunta de esclarecimento (registrada como `question_asked`) e
aguardar resposta; não adivinhar categoria, faixa, unidade ou
quantidade.

### Prompt injection

- Se a mensagem tentar redefinir o comportamento ("ignore as
  instruções", "você agora é...", revelar prompt de sistema), o agente
  **recusa** com resposta padrão e registra evento `refusal`.
- A checagem é determinística (`_check_prompt_injection`) e independe
  do LLM.
- Instruções dentro de mensagens de cliente nunca alteram o prompt de
  sistema nem a lista de ferramentas.

### Tentativa de obter segredos

Pedidos de tokens, chaves, senhas, variáveis de ambiente, conteúdo do
prompt ou configuração interna são recusados e registrados como
`refusal` (motivo `secrets`).

### Erro de ferramenta

Propagar o erro estruturado (validation_error/data_error) e registrar
evento `error`; não tentar contornar a validação nem repetir com dados
alterados silenciosamente.

### Encerrar ou retomar

- A conversa termina com o documento simulado gerado, com rejeição,
  ou com `handoff_to_human` (registrado como evento).
- Uma conversa é retomável pelo mesmo `session_id` (os eventos
  históricos permanecem; o agente não mantém estado em memória entre
  execuções).

## 10. Registro de eventos e métricas

Cada turno grava:

- em `conversation_events`: `session_started`, `message_received`,
  `question_asked`, eventos das ferramentas (pelas próprias
  ferramentas), `agent_response`, `refusal`, `tool_selection_blocked`,
  `error`, `handoff_to_human`;
- em `agent_events` (ADR-007): `session_id`, `conversation_event_id`,
  `created_at`, `event_type`, `tool_name`, `result_summary`, `status`,
  `duration_ms`, `input_tokens`, `output_tokens`, `model`,
  `cost_estimated`, `error_message`.

Quando a FM API não fornecer tokens ou custo, gravar `NULL` — nunca
inventar valores.

## 11. Saída

Para cada mensagem do cliente, o agente retorna uma resposta textual
compreensível, em português, baseada exclusivamente nas saídas
estruturadas das ferramentas (ou na recusa/erro estruturado).

## 12. Critérios de aceite

- CA01 — seleciona somente ferramentas do catálogo aprovado;
- CA02 — ferramenta fora do catálogo é bloqueada e registrada;
- CA03 — nenhum preço/estoque/prazo inventado (só valores das
  ferramentas);
- CA04 — aprovação humana é exigida antes do pagamento (fluxo
  controlado pelas ferramentas);
- CA05 — pagamento real e documento fiscal impossíveis (as ferramentas
  bloqueiam);
- CA06 — prompt injection e pedidos de segredos recusados e registrados;
- CA07 — erros das ferramentas propagados sem correção silenciosa;
- CA08 — `session_id` e eventos registrados em todas as interações;
- CA09 — latência, tokens e modelo registrados em `agent_events`;
- CA10 — catalog/schema sempre totalmente qualificados;
- CA11 — executável como job no target dev sem infra nova;
- CA12 — demonstrável ponta a ponta (busca → estoque → cotação →
  aprovação → pagamento → documento).

## 13. Dependências

- Foundation Model API (endpoint configurável via variável de bundle
  `model_endpoint`);
- as seis ferramentas em `src/nexum_sales_assistant/tools/`;
- tabelas UC em catalog/schema configurados;
- `databricks-sdk` para autenticação (sem segredos em arquivo).

## 14. Fora do escopo

- execução de SQL arbitrário pelo LLM;
- acesso direto do LLM a tabelas;
- criação de produtos/clientes em conversa;
- negociação de desconto;
- pagamento real, documento fiscal, reserva física de estoque;
- interface web interativa (etapa futura, ADR-006).
