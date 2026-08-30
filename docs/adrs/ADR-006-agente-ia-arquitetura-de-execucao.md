# ADR-006 — Arquitetura de execução do agente de IA e das métricas

## Status

Aceita.

## Data

2026-08-29

## Contexto

O desafio oficial de vendas exige que o Nexum Sales Assistant:

- compreenda necessidades em linguagem natural;
- recomende produtos sem inventar informações;
- use estoque, preço e prazo dos dados estruturados;
- conduza a venda até o fim (cotação → aprovação humana →
  pagamento simulado → documento simulado);
- mantenha auditoria completa da conversa;
- controle custo e qualidade da IA.

O projeto já possui:

- Bronze, Silver e Gold materializadas em `workspace.dev`;
- seis ferramentas determinísticas (`search_products`,
  `check_inventory`, `create_quote`, `request_human_approval`,
  `simulate_payment`, `generate_document`) que consultam e escrevem
  em tabelas UC via Spark (`saveAsTable`), com catalog/schema
  totalmente qualificados (ADR anterior, `docs/data_model.md` §18);
- job orquestrador `nexum_sales_assistant_job` (pipeline ETL);
- 136 testes unitários locais com Spark fake em memória.

Inspeção do workspace (2026-08-29, perfil `jornada`):

- Foundation Model API endpoints **pré-provisionados** (pay-per-token,
  `system.ai.*`), incluindo modelos chat com suporte a tool calling:
  `databricks-meta-llama-3-3-70b-instruct`,
  `databricks-llama-4-maverick`, `databricks-gpt-oss-120b`,
  `databricks-qwen35-122b-a10b` etc.;
- plataforma Databricks Apps disponível, sem apps implantados;
- jobs serverless já em uso no bundle;
- não há endpoints de serving próprios implantados.

## Problema

Escolher a arquitetura que seja **realmente executável no workspace
atual**, use um LLM real, consiga chamar as seis ferramentas (que
dependem de Spark e escrevem em tabelas UC), registre eventos e
métricas e mantenha custo baixo.

## Alternativas consideradas

### Alternativa A — Agente executado como job Python (escolhida)

Loop de agente em Python executado por `spark_python_task` serverless,
chamando a Foundation Model API via `databricks-sdk`. As seis
ferramentas rodam in-process (têm Spark disponível no job) e o agente
apenas roteia chamadas aprovadas. Eventos e métricas gravados nas
tabelas do catalog/schema configurados.

- ✅ executável hoje (jobs e FM API já existem no workspace);
- ✅ LLM real pay-per-token, com `usage` (tokens) retornado pela API;
- ✅ ferramentas rodam in-process, sem reescrever nada;
- ✅ auditoria completa controlada pelo nosso código;
- ✅ custo baixo e proporcional à demonstração;
- ✅ demonstrável: job on-demand executa uma jornada de conversa
  completa e imprime a transcrição.

### Alternativa B — Agente exposto por endpoint de serving próprio

Criar um serving endpoint com modelo custom (MLflow PyFunc com
LangGraph/ResponsesAgent) que chamasse as seis ferramentas.

Rejeitada porque:

- contêineres de serving **não têm sessão Spark** — as seis ferramentas
  dependem de `spark.table(...)`/`saveAsTable(...)`; seria necessário
  reescrever o acesso a dados para SQL warehouse, alterando contratos
  validados;
- exige provisionar endpoint próprio (infra adicional, maior custo e
  latência de deploy) sem necessidade para o MVP;
- a demonstração não exige API HTTP pública.

### Alternativa C — Agente executado por Databricks App

Backend de app (AppKit) que chamaria as ferramentas e o LLM.

Rejeitada porque:

- o runtime do backend de app também **não oferece sessão Spark** para
  as ferramentas como implementadas;
- adiciona infraestrutura web (host, deploy, segurança de app) que o
  desafio não exige nesta etapa;
- custo operacional maior sem ganho demonstrável imediato.

### Alternativa D — Supervisor Agent (Agent Bricks / MAS)

Supervisor gerenciado com ferramentas nativas (Genie space, Knowledge
Assistant, UC functions, MCP).

Rejeitada porque:

- as seis ferramentas determinísticas não são representáveis como UC
  functions/Genie sem perder o controle transacional (escrita em
  `quotes`, `approvals`, `payments` com transições de estado) e a
  separação "LLM interpreta, código decide" (ADR-004);
- menos controle sobre auditoria por interação (latência, tokens,
  bloqueios) no formato exigido pelo desafio;
- recurso em Beta com endpoint próprio adicional.

## Decisão

Usar a **Alternativa A**: agente em Python executado como job
(`spark_python_task`, serverless), com:

- LLM real: Foundation Model API, endpoint padrão
  `databricks-meta-llama-3-3-70b-instruct` (chat com tool calling),
  parametrizado pela variável de bundle `model_endpoint`;
- loop próprio e determinístico de tool calling em
  `src/nexum_sales_assistant/agent/` (sem framework externo de agente —
  menos dependências, mais auditável);
- catálogo de ferramentas (`tool_registry.py`) que expõe somente as seis
  ferramentas aprovadas; qualquer outra ferramenta solicitada pelo LLM
  é bloqueada e registrada;
- guardrails determinísticos: recusa de prompt injection e de pedidos de
  segredos/configuração, com registro em evento;
- auditoria em dois níveis:
  - `conversation_events` (schema existente): eventos padrão do fluxo
    (session_started, message_received, question_asked, tool events,
    error, handoff_to_human), mantendo `gold_conversation_audit`
    compatível;
  - `agent_events` (nova tabela runtime, ADR-007): registro operacional
    por interação com latência, tokens de entrada/saída, modelo e
    custo estimado (NULL quando a API não fornecer);
- job de demonstração `nexum_sales_assistant_agent_job` (on-demand, sem
  agendamento) que executa uma jornada completa de conversa usando o
  agente e imprime a transcrição.

## Consequências positivas

- executável com o que já existe no workspace, sem infra nova;
- mantém ADR-004: o LLM interpreta e solicita ferramentas; o código
  valida, decide e controla estados;
- custo proporcional ao uso (pay-per-token) e mensurável (tokens
  registrados por interação);
- auditoria e métricas totalmente sob nosso controle;
- testável localmente com LLM fake determinístico (sem API externa).

## Consequências negativas

- sem interface conversacional interativa (web/chat) nesta etapa — a
  demonstração é por job com transcrição;
- cold start do serverless a cada execução do job (aceitável para demo);
- o custo financeiro exato não é retornado pela FM API — registrado como
  NULL/indisponível até haver fonte documentada de preço;
- o agente é "single-model" (endpoint configurável por variável).

## Limitações honestas

- não há avaliação automatizada de qualidade das respostas nesta etapa
  (ex.: MLflow Evals) — o contrato é garantido pelas ferramentas e pelos
  guardrails, não pela qualidade textual do modelo;
- métricas de custo estimado dependem de fonte externa de preços.

## Plano de evolução para produção

1. avaliação de qualidade (mlflow.genai.evaluate) sobre turnos
   gravados;
2. interface conversacional (Databricks App ou chat externo) reutilizando
   o mesmo loop de agente;
3. servir o agente como API (endpoint próprio) somente quando houver
   necessidade de latência/HTTP, reavaliando então o acesso das
   ferramentas a dados;
4. mover o endpoint do LLM para provisioned throughput se o volume
   justificar;
5. alertas sobre métricas (erros, custo) via SQL alerts.

## Critérios para reconsiderar

- exigência de conversa interativa de baixa latência;
- volume que torne o pay-per-token mais caro que throughput
  provisionado;
- necessidade de multi-agentes especializados.
