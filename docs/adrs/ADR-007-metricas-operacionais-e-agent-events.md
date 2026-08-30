# ADR-007 — Métricas operacionais do agente e `agent_events`

## Status

Aceita.

## Data

2026-08-29

## Contexto

O desafio exige métricas de operação do agente (latência por
ferramenta, tokens consumidos, custo estimado, erros por tipo, funil de
vendas, atualização das camadas) e um dashboard de acompanhamento.

As tabelas existentes cobrem o fluxo comercial:

- `conversation_events` — eventos padrão do fluxo
  (docs/data_model.md §13), schema fixo das seis ferramentas;
- `quotes`, `approvals`, `payments`, `documents` — entidades
  transacionais;
- as quatro Golds de consumo (contrato fechado — não alterar).

O que falta é o registro **operacional** das interações do agente:
latência, tokens de entrada/saída, modelo usado e custo estimado.

## Problema

Onde registrar as métricas operacionais do agente sem alterar o
contrato das seis ferramentas nem o contrato das quatro Golds?

## Alternativas consideradas

### Alternativa 1 — Estender `conversation_events`

Adicionar colunas de latência/tokens/modelo ao schema de
`conversation_events`.

Rejeitada: o schema é gravado pelas seis ferramentas (SPECs e testes
validados); alterá-lo mudaria o contrato das ferramentas sem
necessidade.

### Alternativa 2 — Novas Golds de métricas materializadas

Criar `gold_agent_metrics` etc. na pipeline.

Rejeitada nesta etapa: as métricas são deriváveis por SQL das tabelas
existentes (eventos + entidades transacionais); novas Golds exigiriam
mudar o contrato das quatro Golds previstas (docs/data_model.md §5.3)
e adicionariam materialização sem ganho para o volume do MVP.

### Alternativa 3 — Tabela runtime `agent_events` + métricas via SQL
(escolhida)

O agente grava seu registro operacional em `agent_events` (tabela
runtime com schema próprio) e as métricas do dashboard são queries SQL
sobre `agent_events` + tabelas existentes.

## Decisão

1. Criar a tabela runtime `agent_events` (criada de forma idempotente
   por `schema_bootstrap.py` — usado pelo job do agente e pela task
   `bootstrap_runtime` do job orquestrador, que roda antes do refresh
   da pipeline), junto das demais tabelas runtime:

```text
event_id, session_id, conversation_event_id, created_at, event_type,
tool_name, result_summary, status, duration_ms, input_tokens,
output_tokens, model, cost_estimated, error_message
```

2. Registrar em `agent_events`, por interação: `turn` (status, duração,
   tokens, modelo), `tool_call` (ferramenta, status da ferramenta,
   duração), `refusal`, `agent_error`.

3. `cost_estimated` permanece NULL: a Foundation Model API não retorna
   custo financeiro e não há fonte documentada de preço por token no
   projeto. Não inventar valores (docs/specs/agent.md §10).

4. As métricas do dashboard (funil, operação, qualidade, custo,
   atualização) são **queries SQL** sobre as tabelas existentes — sem
   novas Golds e sem alterar as quatro Golds atuais. Cada query
   declara sua fonte. Nomes de tabela nas queries do dashboard são
   nus (o catalog/schema é suprido pela configuração do dashboard,
   conforme o mecanismo Lakeview).

5. O dashboard Lakeview (`nexum_sales_metrics`) é versionado no bundle
   e implantado no target dev, usando as tabelas de `workspace.dev`
   (catalog/schema configurados), nunca tabelas de outros projetos.

## Consequências positivas

- contratos existentes intactos (ferramentas, Golds, SPECs);
- rastreabilidade completa: `conversation_events` para auditoria do
  fluxo e `agent_events` para métricas operacionais;
- dashboard mostra zero quando não há dados operacionais (COUNT sobre
  tabelas vazias), sem dados fictícios;
- nenhuma infraestrutura nova além do dashboard.

## Consequências negativas

- custo financeiro por interação permanece NULL até existir fonte de
  preço documentada;
- as métricas dependem de o agente gravar `agent_events` corretamente;
- `agent_events` é tabela runtime: não passa pela pipeline Bronze/Silver.

## Limitações

- o dashboard não substitui as Golds de consumo das ferramentas;
- taxas de funil usam divisão segura (denominador zero → zero).

## Plano de evolução

- quando houver fonte oficial de preço por token por modelo, preencher
  `cost_estimated`;
- migrar métricas para Gold materializada somente se o volume exigir;
- adicionar SQL alerts sobre erros e custo.
