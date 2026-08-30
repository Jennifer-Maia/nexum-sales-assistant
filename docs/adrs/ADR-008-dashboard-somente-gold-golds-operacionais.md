# ADR-008 — Dashboard lê somente Gold: `gold_agent_operations` e
`gold_data_freshness`

## Status

Aceita.

## Data

2026-08-30

## Contexto

Na preparação do projeto para publicação como portfólio, foi definida
a regra de consumo:

> O dashboard Lakeview deve consultar **exclusivamente** tabelas Gold.
> O runtime do agente continua gravando `agent_events` e as tabelas
> transacionais; o dashboard não lê essas tabelas diretamente.

Auditoria das queries atuais do dashboard mostrou leituras diretas de:

- `conversation_events` (sessões, recusas, bloqueios, mensagens);
- `agent_events` (latência, tokens, modelo, erros);
- `quotes`, `approvals`, `payments`, `documents` (funil);
- `bronze_*`/`silver_*` (atualização dos dados).

As quatro Golds previstas (`gold_product_catalog`,
`gold_product_availability`, `gold_quote_summary`,
`gold_conversation_audit`) têm contratos fechados em
docs/data_model.md e não cobrem:

- a granularidade operacional de `agent_events` (uma linha por chamada
  de ferramenta e por turno, com latência, tokens, modelo e custo);
- os eventos de segurança de `conversation_events` (`refusal`,
  `tool_selection_blocked`, `error`, `handoff_to_human`) — fora do
  mapeamento de `gold_conversation_audit`;
- a atualização/contagem das camadas Bronze/Silver/Gold.

## Problema

Como atender à regra "dashboard somente Gold" sem alterar o contrato
das quatro Golds existentes?

## Alternativas consideradas

### Alternativa 1 — Liberar leitura direta do runtime no dashboard

Rejeitada: viola a regra definida para a publicação; acopla o
dashboard ao schema do runtime.

### Alternativa 2 — Estender as quatro Golds existentes

Rejeitada: alteraria o contrato documentado das Golds de consumo das
ferramentas (prompts/03-gold.md: criar Golds adicionais exige decisão
registrada em ADR; alterar as existentes é pior).

### Alternativa 3 — Duas novas Golds operacionais (escolhida)

Materializar na pipeline:

1. `gold_agent_operations` — visão granular das operações do agente:
   projeção de `agent_events` (turnos e chamadas de ferramenta com
   latência/tokens/modelo/custo) unida aos eventos de segurança e
   qualidade de `conversation_events` (`refusal`,
   `tool_selection_blocked`, `error`, `handoff_to_human`)
   normalizados no mesmo schema, com coluna `source` de
   rastreabilidade;
2. `gold_data_freshness` — contagens de registros e último timestamp
   de ingestão por tabela das camadas Bronze/Silver/Gold, mais
   `conversation_events` e `agent_events` (coluna `atualizado_em`
   nula onde a tabela não possui timestamp próprio).

## Decisão

Criar as duas Golds acima na pipeline (`src/nexum_sales_assistant_etl/
transformations/`), documentadas em docs/data_model.md, e migrar TODAS
as queries do dashboard Lakeview para ler somente as seis Golds. O
runtime do agente e das ferramentas permanece inalterado.

As Golds leem `agent_events` e `conversation_events` com linhagem DLT;
essas tabelas são garantidas pela task `bootstrap_runtime` do job
orquestrador, que roda antes do refresh da pipeline.

## Consequências positivas

- dashboard desacoplado do schema do runtime;
- contratos das quatro Golds de consumo intactos;
- rastreabilidade explícita (`source`) nos dados operacionais;
- atualização dos dados visível por camada.

## Consequências negativas

- mais duas Golds para manter (materialização barata no volume atual);
- o dashboard depende do refresh da pipeline para refletir eventos
  novos do agente.

## Limitações

- `gold_data_freshness.atualizado_em` é NULL para as Golds (não têm
  timestamp próprio) — documentado no dashboard;
- custo estimado permanece 0/NULL (FM API não retorna custo — ADR-007).

## Plano de evolução

- substituir as duas Golds por views incrementais se o volume crescer;
- alertas SQL sobre erros e custo a partir de `gold_agent_operations`.
