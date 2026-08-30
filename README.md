# Nexum Sales Assistant

Assistente de vendas B2B que transforma uma necessidade descrita em
linguagem natural em recomendação de produto e cotação preliminar,
executado sobre Databricks e Declarative Automation Bundles.

> Projeto de demonstração com dados sintéticos, aprovação humana
> obrigatória e pagamento exclusivamente simulado.

---

## Visão geral

O **Nexum Sales Assistant** é o assistente de vendas da **Nexum
Industrial**, empresa fictícia que fornece equipamentos e soluções para
manutenção, operação e monitoramento industrial.

Vendedores B2B gastam tempo significativo traduzindo a necessidade do
cliente em produtos adequados, consultando especificações técnicas,
disponibilidade, preço e prazo. O assistente reduz essa fricção:

- interpreta a necessidade descrita pelo cliente;
- faz perguntas de esclarecimento quando faltam informações;
- consulta um catálogo estruturado de produtos;
- verifica a disponibilidade de estoque;
- monta uma cotação preliminar;
- encaminha a cotação para aprovação humana;
- simula o pagamento após a aprovação;
- gera um documento simulado, sem validade fiscal.

Todos os dados comerciais (produtos, preços, estoque e prazos) vêm de
tabelas estruturadas. O modelo de linguagem não pode inventá-los.

---

## Princípio central

```text
LLM interpreta.
Código valida.
Código consulta.
Código calcula.
Código controla estados.
Humano aprova ações comerciais sensíveis.
```

O LLM conduz a conversa, extrai requisitos e explica resultados. As
ferramentas determinísticas consultam os dados, aplicam as regras e
controlam as transições. A aprovação humana é obrigatória antes do
pagamento simulado.

---

## Fluxo principal

```text
search_products
        ↓
check_inventory
        ↓
create_quote
        ↓
request_human_approval
        ↓
simulate_payment
        ↓
generate_document
```

### Ferramentas do MVP

| Ferramenta | Responsabilidade | Fonte de dados |
|---|---|---|
| `search_products` | Buscar produtos ativos e compatíveis com os requisitos extraídos da conversa | `gold_product_catalog` |
| `check_inventory` | Informar se a quantidade disponível atende à quantidade solicitada, sem alterar o estoque | `gold_product_availability` |
| `create_quote` | Validar cliente e produtos, congelar preços e criar a cotação em estado `draft` | `silver_companies`, Golds de catálogo e disponibilidade |
| `request_human_approval` | Solicitar aprovação humana e registrar a decisão (`approved` ou `rejected`) | `quotes`, `approvals` |
| `simulate_payment` | Registrar um pagamento exclusivamente simulado, somente após aprovação válida | `quotes`, `approvals`, `payments` |
| `generate_document` | Gerar documento simulado sem validade fiscal, somente após pagamento simulado bem-sucedido | `quotes`, `quote_items`, `products`, `payments`, `silver_companies` |

Cada ferramenta possui um contrato formal em `docs/specs/`, incluindo
entradas, saídas, códigos de erro, regras de negócio, auditoria e
critérios de aceite.

---

## Máquina de estados de `quotes`

A entidade comercial principal do MVP é `quotes`. Não existe uma
entidade `orders`.

Estados permitidos:

```text
draft
pending_approval
approved
rejected
paid
completed
```

Transições permitidas:

```text
draft → pending_approval
pending_approval → approved
pending_approval → rejected
approved → paid
paid → completed
```

Transições inválidas devem ser bloqueadas pelo código, não apenas
descritas na resposta textual do agente.

---

## Domínio do MVP

O MVP atende inicialmente três categorias de necessidade:

```text
temperature
pressure
vibration
```

O catálogo é pequeno, controlado e sintético, com produtos que cobrem
casos positivos e negativos (compatível, incompatível, inativo, com ou
sem estoque). O objetivo é demonstrar a jornada completa com qualidade
de engenharia de dados, não representar um catálogo industrial real.

---

## Arquitetura de dados

Os dados são organizados nas camadas Bronze, Silver e Gold, conforme
`docs/data_model.md`.

```text
Bronze
dados de origem preservados, com metadados de ingestão
        ↓
Silver
dados padronizados, tipados e validados
        ↓
Gold
modelos preparados para consumo pelas ferramentas
```

### Bronze

Ingere os arquivos de origem sem aplicar regras de negócio.
Datasets previstos:

```text
bronze_companies
bronze_products
bronze_inventory
bronze_quotes
bronze_quote_items
bronze_approvals
bronze_payments
bronze_documents
bronze_conversation_events
```

### Silver

Padroniza nomes, converte tipos, trata valores inválidos e valida
chaves. A fonte canônica de clientes do MVP é `silver_companies`
(`quotes.customer_id` referencia `silver_companies.company_id`).

Datasets implementados (etapa 02-silver, em
`src/nexum_sales_assistant_etl/transformations/`):

```text
silver_companies   ← bronze_companies  (fonte canônica de clientes)
silver_products    ← bronze_products   (regras de qualidade do ADR-005)
silver_inventory   ← bronze_inventory  (referencia silver_products)
```

Registros inválidos são sinalizados na coluna técnica
`_quality_status` (`valid` ou `invalid:<regra>[;<regra>]`) e nunca são
corrigidos silenciosamente (ADR-005). As colunas técnicas de origem
(`_ingestion_timestamp`, `_source_file`, `_source_system`) são
preservadas para rastreabilidade Bronze → Silver.

As entidades transacionais (`quotes`, `quote_items`, `approvals`,
`payments`, `documents`, `conversation_events`) são criadas em tempo de
execução pelas ferramentas e não possuem Bronze de origem; por isso
não existem datasets `silver_*` correspondentes nesta etapa
(prompts/01-bronze.md).

### Gold

Modelos prontos para consumo pelas ferramentas, implementados na
etapa 03-gold (derivados exclusivamente das camadas tratadas, nunca de
CSV consultado diretamente):

```text
gold_product_catalog        ← silver_products (somente registros válidos)
gold_product_availability   ← silver_products + silver_inventory
                              (is_available = available_quantity > 0)
gold_quote_summary          ← quotes + quote_items + approvals
                              (tabelas runtime das ferramentas) +
                              silver_companies (cliente canônico)
gold_conversation_audit     ← conversation_events, agregado por sessão
```

`gold_quote_summary` e `gold_conversation_audit` materializam vazias com
o schema documentado enquanto as tabelas transacionais ainda não
existirem no catálogo (nenhum dado é inventado).

As ferramentas não devem consultar arquivos CSV diretamente quando
existir uma camada estruturada apropriada.

---

## Entidades principais

```text
companies
products
inventory
quotes
quote_items
approvals
payments
documents
conversation_events
```

Principais relacionamentos:

```text
products.product_id
    ├── inventory.product_id
    └── quote_items.product_id

silver_companies.company_id
    └── quotes.customer_id

quotes.quote_id
    ├── quote_items.quote_id
    ├── approvals.quote_id
    ├── payments.quote_id
    └── documents.quote_id
```

---

## Regras de segurança e negócio

- não há pagamento real nem integração com instituições financeiras;
- não há documento com validade fiscal;
- todo pagamento é registrado com `simulated = true`;
- todo documento é registrado com `has_fiscal_value = false`;
- os dados são sintéticos e identificados como dados de demonstração;
- a consulta de estoque não altera as quantidades disponíveis;
- a aprovação humana é obrigatória antes do pagamento simulado;
- o agente não pode aprovar uma cotação em seu próprio nome.

---

## Documentação de referência

A fonte de verdade do produto está em `docs/`:

```text
docs/discovery.md          # Descoberta do problema e escopo
docs/prd.md                # Requisitos do produto
docs/data_model.md         # Modelo lógico de dados
docs/agent_harness.md      # Uso de agentes no desenvolvimento
docs/specs/                # Contratos das ferramentas do MVP
docs/adrs/                 # Decisões arquiteturais registradas
```

---

## Estrutura do projeto

```text
nexum_sales_assistant/
├── .claude/                         # Configurações locais do agente
├── docs/                            # Fonte de verdade do produto
├── fixtures/                        # Dados sintéticos de entrada
├── prompts/                         # Prompts de implementação
├── resources/                       # Recursos Databricks declarados em YAML
├── src/                             # Código executado no Databricks
├── tests/                           # Testes automatizados
├── AGENTS.md                        # Instruções para agentes de IA
├── CLAUDE.md                        # Instruções específicas do Claude
├── databricks.yml                   # Configuração principal do bundle
├── pyproject.toml                   # Configuração do projeto Python
└── README.md
```

---

## Chat local (demonstração do agente)

Interface de chat simples (Streamlit) que reusa o agente de IA, as seis
ferramentas e as mesmas tabelas do Databricks (o dashboard Lakeview
continua funcionando sem alteração). A conexão usa **Databricks
Connect** com compute **serverless** do workspace — nenhum token ou
segredo fica em arquivo; a autenticação vem do perfil do Databricks CLI.

### Arquitetura local

```text
Chat Streamlit (app/chat.py)
        ↓
Databricks Connect (sessão Spark serverless)
        ↓
Agente (src/nexum_sales_assistant/agent/)
        ↓
Seis ferramentas determinísticas
        ↓
Tabelas em workspace.dev (runtime + Bronze/Silver/Gold)
        ↓
Dashboard Lakeview (Nexum Sales Metrics)
```

### Instalar dependências

```bash
uv sync --dev
```

### Configurar a conexão (sem expor segredos)

Use o perfil já configurado no Databricks CLI (`jornada`) e as variáveis
de ambiente do projeto:

```bash
# PowerShell
$env:DATABRICKS_CONFIG_PROFILE = "jornada"
$env:NEXUM_CATALOG = "workspace"
$env:NEXUM_SCHEMA = "dev"

# Git Bash
export DATABRICKS_CONFIG_PROFILE=jornada
export NEXUM_CATALOG=workspace
export NEXUM_SCHEMA=dev
```

O endpoint do modelo já tem padrão documentado (`model_endpoint` do
bundle); para trocar, defina `NEXUM_MODEL_ENDPOINT`.

### Rodar o chat

```bash
uv run streamlit run app/chat.py
```

Abra a URL exibida no navegador. Cada execução do app usa uma sessão
nova (`SES-CHAT-XXXXXX`), exibida na barra lateral.

### Roteiro sugerido de demonstração

1. **Busca**: "Preciso monitorar 20 máquinas com temperatura entre
   0 °C e 150 °C. Que sensores vocês têm?" → `search_products`;
2. **Estoque**: "O sensor PRD-TEMP-001 parece adequado. Tem 20
   unidades disponíveis?" → `check_inventory`;
3. **Cotação** (gate de confirmação): "Quero uma cotação para a
   empresa C0001 com 20 unidades do produto PRD-TEMP-001." → o chat
   pede confirmação → botão "✅ Confirmar ação pendente" →
   `create_quote`;
4. **Aprovação humana**: "Encaminhe a cotação para aprovação humana."
   → confirmar → botões "✅ Aprovar (vendor-001)" / "❌ Rejeitar" →
   `request_human_approval`;
5. **Pagamento simulado**: "Quero simular o pagamento da cotação com
   sucesso." → confirmar → `simulate_payment` (bloqueado sem
   aprovação — demonstre o bloqueio antes de aprovar);
6. **Documento simulado**: "Quero o documento simulado da cotação."
   → confirmar → `generate_document`;
7. Depois, abra o dashboard **Nexum Sales Metrics** para mostrar o
   funil, as métricas do agente e o custo reais.

### Limitações conhecidas do chat local

- uma sessão por execução do app (sem multi-sessão);
- o estado de confirmação pendente vive na execução do app;
- sem autenticação de usuário (demonstração local);
- primeira mensagem pode levar alguns segundos (cold start do
  serverless).

## Desenvolvimento local

### Pré-requisitos

- Git;
- Python compatível com o projeto (ver `.python-version`);
- Databricks CLI autenticada;
- `uv`.

### Instalar dependências

```bash
uv sync --dev
```

### Executar testes

```bash
uv run pytest
```

### Verificar estilo

```bash
uv run ruff check .
```

### Validar o bundle

```bash
databricks bundle validate --profile <perfil>
```

### Deploy no target `dev`

```bash
databricks bundle deploy --target dev --profile <perfil>
databricks bundle run --target dev --profile <perfil>
```

Os targets configurados são `dev` e `prod`, com catálogo `workspace`.
O target `prod` só deverá ser utilizado após a validação completa do
MVP.

---

## Estado atual

O repositório implementa o escopo ativo do MVP (Nexum Sales Assistant):

- ingestão Bronze dos dados sintéticos (`bronze_companies`,
  `bronze_products`, `bronze_inventory`);
- camada Silver tratada e validada (`silver_companies`,
  `silver_products`, `silver_inventory`);
- camada Gold de consumo (`gold_product_catalog`,
  `gold_product_availability`, `gold_quote_summary`,
  `gold_conversation_audit`);
- as seis ferramentas do MVP com contratos em `docs/specs/`.

A documentação em `docs/` define o escopo ativo; as etapas de dados
seguem a arquitetura Bronze → Silver → Gold descrita em
`docs/data_model.md`.

---

## Licença e origem dos dados

Este projeto é destinado a fins educacionais e de portfólio.

Os dados utilizados são sintéticos e não representam empresas,
produtos ou transações reais.
