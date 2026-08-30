# Nexum Sales Assistant

Assistente de vendas B2B com agente de IA que transforma uma
necessidade descrita em linguagem natural em recomendação de produto,
cotação aprovada por humano, pagamento simulado e documento simulado —
executado sobre Databricks (Delta, Declarative Automation Bundles e
Foundation Model API).

> Projeto de portfólio com dados sintéticos, aprovação humana
> obrigatória e pagamento exclusivamente simulado.

---

## 1. Objetivo

O **Nexum Sales Assistant** é o assistente de vendas da **Nexum
Industrial**, empresa fictícia de equipamentos para manutenção,
operação e monitoramento industrial. Ele demonstra ponta a ponta a
engenharia de um assistente comercial com IA: engenharia de dados
(Bronze → Silver → Gold), ferramentas determinísticas, agente com LLM
real, aprovação humana, auditoria completa e métricas operacionais.

## 2. Problema de negócio

Vendedores B2B gastam tempo traduzindo a necessidade do cliente em
produtos adequados, consultando especificações, disponibilidade, preço
e prazo. O assistente reduz essa fricção: o LLM **interpreta** a
conversa, e o código **valida, consulta, calcula e controla estados** —
o modelo nunca inventa dados comerciais.

## 3. Funcionalidades

- busca determinística de produtos por categoria, faixa e unidade;
- consulta de estoque somente-leitura (com sinalização de dado
  desatualizado);
- criação de cotação com congelamento de preço;
- aprovação humana obrigatória antes do pagamento simulado;
- pagamento exclusivamente simulado (sem dinheiro real);
- documento simulado sem validade fiscal, financeira ou contábil;
- auditoria completa da conversa e das ferramentas;
- agente de IA conversacional com LLM real e tool calling controlado;
- chat local (Streamlit) e job de demonstração;
- dashboard Lakeview de funil, operação, qualidade, custo e
  atualização dos dados.

## 4. Arquitetura de dados — Bronze → Silver → Gold

```text
fixtures/CSV (dados sintéticos)
        ↓
Bronze   dados de origem preservados + metadados de ingestão
        ↓
Silver   dados padronizados, tipados e validados (_quality_status)
        ↓
Gold     modelos de consumo das ferramentas e do dashboard
```

Datasets implementados:

```text
bronze_companies · bronze_products · bronze_inventory
silver_companies (fonte canônica de clientes — ADR-002)
silver_products · silver_inventory
gold_product_catalog        ← search_products
gold_product_availability   ← check_inventory
gold_quote_summary          ← visão de cotações (ADR-002)
gold_conversation_audit     ← auditoria por sessão
gold_agent_operations       ← operação do agente (ADR-008)
gold_data_freshness         ← atualização dos dados (ADR-008)
```

Registros inválidos são sinalizados em `_quality_status` e nunca
corrigidos silenciosamente (ADR-005). As entidades transacionais
(`quotes`, `quote_items`, `approvals`, `payments`, `documents`,
`conversation_events`, `agent_events`) são criadas em tempo de execução
pelas ferramentas e pelo agente; o dashboard lê **somente Gold**
(ADR-008).

## 5. Agente com LLM

O agente (`src/nexum_sales_assistant/agent/`) usa a **Foundation Model
API** do Databricks (pay-per-token; endpoint configurável via
`model_endpoint` do bundle, padrão
`databricks-meta-llama-3-3-70b-instruct`). O loop de tool calling é
próprio e determinístico (ADR-006):

- o LLM só pode solicitar as **seis ferramentas aprovadas**;
- ferramenta fora do catálogo → bloqueada e registrada
  (`tool_selection_blocked`);
- ações sensíveis (cotação, aprovação, pagamento, documento) exigem
  **confirmação explícita** do cliente (gate determinístico);
- prompt injection e pedidos de segredos → recusa registrada
  (`refusal`);
- cada turno registra latência, tokens, modelo, status e erro em
  `agent_events` (custo permanece 0/NULL — a API não retorna custo;
  nenhum valor é inventado — ADR-007);
- o histórico de cada turno é reconstruído da trilha de auditoria
  (`conversation_events`) — a conversa é retomável pelo `session_id`.

## 6. As seis ferramentas

| Ferramenta | Responsabilidade | Fonte de dados |
|---|---|---|
| `search_products` | Buscar produtos ativos e compatíveis | `gold_product_catalog` |
| `check_inventory` | Disponibilidade sem alterar o estoque | `gold_product_availability` |
| `create_quote` | Cotação em `draft` com preços congelados | `silver_companies` + Golds |
| `request_human_approval` | Solicitar/registrar aprovação humana | `quotes`, `approvals` |
| `simulate_payment` | Pagamento exclusivamente simulado | `quotes`, `approvals`, `payments` |
| `generate_document` | Documento simulado sem validade fiscal | `quotes`, `quote_items`, `payments`, `silver_companies` |

Contratos formais em `docs/specs/` (entradas, saídas, erros, auditoria,
critérios de aceite).

## 7. Aprovação humana

Obrigatória antes do pagamento simulado (ADR-004). O agente solicita e
repassa a decisão de um aprovador autorizado (demo: `vendor-001`);
nunca decide `approved`/`rejected` por conta própria. Transições
inválidas da máquina de estados de `quotes` são bloqueadas pelo código:

```text
draft → pending_approval → approved → paid → completed
                       ↘ rejected
```

## 8. Interface Streamlit (chat local)

Chat local em `app/chat.py` que reusa o agente e as ferramentas,
gravando nas mesmas tabelas do Databricks (o dashboard funciona sem
alteração). Conexão via **Databricks Connect** com compute
**serverless**; recupera automaticamente de sessões expiradas por
inatividade.

```text
Chat Streamlit (app/chat.py)
        ↓
Databricks Connect (sessão Spark serverless)
        ↓
Agente (LLM real) → seis ferramentas determinísticas
        ↓
Tabelas em workspace.dev (runtime + Bronze/Silver/Gold)
        ↓
Dashboard Lakeview (Nexum Sales Metrics)
```

## 9. Dashboard Lakeview

`Nexum Sales Metrics` (deployado pelo bundle) com páginas de funil de
vendas, operação do agente, qualidade e segurança, custo e atualização
dos dados. Todas as queries leem exclusivamente tabelas Gold
(ADR-008); sem dados operacionais, mostra zero — nenhum valor fictício.

## 10. Instruções de configuração

Pré-requisitos: Git, Python 3.12, `uv`, Databricks CLI autenticada com
o perfil `jornada` (workspace de demonstração).

```bash
uv sync --dev
```

Variáveis de ambiente (PowerShell):

```powershell
$env:DATABRICKS_CONFIG_PROFILE = "jornada"
$env:NEXUM_CATALOG = "workspace"
$env:NEXUM_SCHEMA = "dev"
```

(Git Bash: `export DATABRICKS_CONFIG_PROFILE=jornada` etc.) A
autenticação vem do perfil do Databricks CLI — nenhum token ou segredo
fica em arquivo do repositório.

## 11. Execução do pipeline

```bash
databricks bundle validate -t dev --profile jornada
databricks bundle deploy -t dev --profile jornada
databricks bundle run nexum_sales_assistant_job -t dev --profile jornada
```

O job orquestrador executa `bootstrap_runtime` (garante as tabelas
runtime) e `refresh_pipeline` (Bronze → Silver → Gold), com trigger
diário pausado no dev.

## 12. Execução do chat

```bash
uv run streamlit run app/chat.py
```

Cada execução do app usa uma sessão nova (`SES-CHAT-*`, exibida na
barra lateral). Alternativa sem interface: o job de demonstração
executa a jornada completa com LLM real:

```bash
databricks bundle run nexum_sales_assistant_agent_job -t dev --profile jornada
```

## 13. Roteiro de demonstração

1. **Busca**: "Preciso monitorar 20 máquinas com temperatura entre
   0 °C e 150 °C. Que sensores vocês têm?" → `search_products`;
2. **Estoque**: "O sensor PRD-TEMP-001 parece adequado. Tem 20
   unidades disponíveis?" → `check_inventory`;
3. **Cotação** (gate de confirmação): "Quero uma cotação para a
   empresa C0001 com 20 unidades do produto PRD-TEMP-001." → botão
   "✅ Confirmar" → `create_quote`;
4. **Bloqueio**: "Quero simular o pagamento da cotação com sucesso."
   → confirmar → a ferramenta rejeita com `approval_required` (nada é
   alterado);
5. **Aprovação humana**: "Encaminhe a cotação para aprovação humana."
   → confirmar → botões "✅ Aprovar (vendor-001)" / "❌ Rejeitar" →
   `request_human_approval`;
6. **Pagamento simulado**: repetir o passo 4 → agora `simulated_success`
   (com o aviso de simulação);
7. **Documento simulado**: "Quero o documento simulado da cotação." →
   confirmar → `generate_document`;
8. Rodar `bundle run nexum_sales_assistant_job` e abrir o dashboard
   **Nexum Sales Metrics** (funil, operação e custo reais).

## 14. Testes

```bash
uv run pytest
```

175+ testes unitários em memória (ferramentas, Silver/Gold, agente com
LLM fake determinístico, métricas, chat) — sem API externa, segredo ou
custo de LLM. Estilo: `uv run ruff check .`

## 15. Segurança

- sem pagamento real nem integração financeira;
- sem documento fiscal; todo documento tem `has_fiscal_value = false`;
- sem tokens/segredos em arquivos versionados (`.env`, `.env.*`,
  `.claude/settings*.json` no `.gitignore`);
- o LLM não executa SQL arbitrário nem acessa tabelas diretamente —
  somente pelas seis ferramentas;
- prompt injection e pedidos de segredos são recusados e registrados;
- auditoria de cada ferramenta e de cada turno do agente.

## 16. Limitações

- dados sintéticos (ver §17) — não representam catálogo industrial
  real;
- chat local com uma sessão por execução, sem autenticação de usuário;
- custo financeiro estimado do LLM não é retornado pela FM API
  (registrado como 0/NULL);
- respostas textuais do modelo podem variar entre execuções (as
  garantias do contrato estão nas ferramentas e nos guardrails, não no
  texto do modelo);
- primeira mensagem do chat pode levar alguns segundos (cold start do
  serverless); sessões Connect expiram por inatividade e são
  recuperadas automaticamente.

## 17. Dados sintéticos

Todos os dados são sintéticos e identificados como demonstração:
catálogo pequeno e controlado cobrindo `temperature`, `pressure` e
`vibration` (ADR-005), com casos de produto compatível, incompatível,
inativo, estoque suficiente/insuficiente/ausente/desatualizado e
registros inválidos de propósito (qualidade de dados). Nenhuma empresa,
produto ou transação real.

## 18. Pagamentos e documentos simulados

`simulate_payment` registra exclusivamente simulações
(`simulated = true`) e `generate_document` produz um documento marcado
como **sem validade fiscal, financeira ou contábil** — não há nota
fiscal, dinheiro real ou efeito contábil em nenhum ponto do fluxo.

---

## Documentação de referência

```text
docs/discovery.md      # Descoberta do problema e escopo
docs/prd.md            # Requisitos do produto
docs/data_model.md     # Modelo lógico de dados
docs/agent_harness.md  # Uso de agentes no desenvolvimento
docs/specs/            # Contratos das ferramentas e do agente
docs/adrs/             # Decisões arquiteturais registradas
```

## Estrutura do projeto

```text
nexum_sales_assistant/
├── app/                # Chat local Streamlit
├── docs/               # Fonte de verdade do produto
├── fixtures/           # Dados sintéticos de entrada
├── prompts/            # Prompts de implementação por etapa
├── resources/          # Recursos Databricks (jobs, pipeline, dashboard, volume)
├── src/
│   ├── nexum_sales_assistant/            # Ferramentas, agente, métricas, chat
│   └── nexum_sales_assistant_etl/        # Transformações Bronze → Silver → Gold
├── tests/              # Testes automatizados
├── databricks.yml      # Configuração principal do bundle
└── pyproject.toml      # Configuração do projeto Python
```

## Licença e origem dos dados

Projeto destinado a fins educacionais e de portfólio. Os dados
utilizados são sintéticos e não representam empresas, produtos ou
transações reais.
