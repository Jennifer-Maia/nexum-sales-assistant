# Modelo de Dados — Nexum Sales Assistant

## 1. Objetivo

Este documento define o modelo lógico de dados do Nexum Sales Assistant.

O modelo deverá suportar:

- catálogo de produtos;
- consulta de especificações;
- consulta de estoque;
- consulta de preço e prazo;
- criação de cotações;
- aprovação humana;
- pagamento simulado;
- geração de documento simulado;
- auditoria da conversa e das ferramentas utilizadas.

O modelo será implementado no Databricks usando tabelas Delta organizadas
nas camadas Bronze, Silver e Gold.

## 2. Princípios

1. Dados comerciais devem ser consultados de tabelas estruturadas.
2. O agente não pode inventar preço, estoque, prazo ou especificações.
3. Preços utilizados em uma cotação devem ser preservados historicamente.
4. Ações comercialmente sensíveis devem exigir aprovação humana.
5. Eventos importantes devem ser registrados para auditoria.
6. O modelo deve ser pequeno o suficiente para o MVP.
7. Os dados sintéticos devem ser identificados como dados de demonstração.

## 3. Escopo do modelo

### 3.1 Dados existentes

A base atual contém dados de:

- empresas;
- funcionários;
- contatos;
- atributos de contexto comercial.

Esses dados serão tratados como contexto de CRM.

### 3.2 Dados novos

O produto exigirá dados adicionais de:

- produtos;
- estoque;
- cotações;
- itens de cotação;
- aprovações;
- pagamentos simulados;
- documentos simulados;
- eventos de conversa.

## 4. Visão geral das entidades

```text
companies
    │
    └── quotes
            │
            ├── quote_items ─── products ─── inventory
            │
            ├── approvals
            │
            ├── payments
            │
            └── documents

conversation_events
    └── registra eventos relacionados à sessão,
        produtos, cotações, aprovações e pagamentos
```

## 5. Camada de dados

### 5.1 Bronze

Responsável por:

- ingerir os arquivos de origem;
- preservar os dados originais;
- adicionar metadados de ingestão;
- não aplicar regras de negócio;
- não calcular compatibilidade ou recomendação.

Datasets previstos:

- `bronze_companies`;
- `bronze_employees`;
- `bronze_products`;
- `bronze_inventory`;
- `bronze_quotes`;
- `bronze_quote_items`;
- `bronze_approvals`;
- `bronze_payments`;
- `bronze_documents`;
- `bronze_conversation_events`.

### 5.2 Silver

Responsável por:

- padronizar nomes;
- converter tipos;
- tratar valores inválidos;
- validar chaves;
- normalizar categorias;
- garantir consistência entre entidades;
- preparar os dados para as ferramentas do agente.

Datasets previstos:

- `silver_companies`;
- `silver_employees`;
- `silver_products`;
- `silver_inventory`;
- `silver_quotes`;
- `silver_quote_items`;
- `silver_approvals`;
- `silver_payments`;
- `silver_documents`;
- `silver_conversation_events`.

### 5.3 Gold

Responsável por criar modelos prontos para consumo:

- `gold_product_catalog`;
- `gold_product_availability`;
- `gold_quote_summary`;
- `gold_conversation_audit`.

A Gold poderá combinar produtos e estoque para facilitar consultas,
mas não deverá substituir as fontes detalhadas da Silver.

## 6. Entidade `products`

Representa os produtos ativos ou inativos no catálogo da Nexum Industrial.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `product_id` | STRING | Sim | Chave primária |
| `sku` | STRING | Sim | Identificador comercial único |
| `product_name` | STRING | Sim | Nome do produto |
| `category` | STRING | Sim | `temperature`, `pressure` ou `vibration` no MVP |
| `description` | STRING | Sim | Descrição comercial |
| `use_cases` | STRING | Sim | Casos de uso conhecidos |
| `technical_specs` | STRING | Sim | Especificações em JSON ou texto estruturado |
| `measurement_unit` | STRING | Sim | Unidade principal, como `C`, `bar` ou `mm/s` |
| `min_operating_value` | DECIMAL(10,2) | Não | Limite inferior da faixa |
| `max_operating_value` | DECIMAL(10,2) | Não | Limite superior da faixa |
| `price` | DECIMAL(10,2) | Sim | Preço atual de referência |
| `currency` | STRING | Sim | `BRL` no MVP |
| `lead_time_days` | INT | Sim | Prazo estimado em dias |
| `active` | BOOLEAN | Sim | Indica se pode ser recomendado |
| `created_at` | TIMESTAMP | Sim | Data de criação |
| `updated_at` | TIMESTAMP | Sim | Última atualização |

### Regras de `products`

- `sku` deve ser único.
- `price` não pode ser negativo.
- `lead_time_days` não pode ser negativo.
- `min_operating_value` deve ser menor ou igual a
  `max_operating_value`.
- Somente produtos com `active = true` podem ser recomendados.
- Um produto sem especificações essenciais não deve ser recomendado
  automaticamente.
- `technical_specs` deve ser rastreável ao arquivo de origem.

## 7. Entidade `inventory`

Representa a disponibilidade de produtos.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `inventory_id` | STRING | Sim | Chave primária |
| `product_id` | STRING | Sim | Chave estrangeira para `products` |
| `warehouse_id` | STRING | Sim | Identificador do estoque |
| `available_quantity` | INT | Sim | Quantidade disponível |
| `reserved_quantity` | INT | Sim | Quantidade reservada |
| `updated_at` | TIMESTAMP | Sim | Momento da atualização |

### Regras de `inventory`

- `product_id` deve existir em `products`.
- `available_quantity` não pode ser negativo.
- `reserved_quantity` não pode ser negativo.
- No MVP, será utilizado um único estoque principal.
- A consulta de disponibilidade deverá considerar
  `available_quantity`.
- A consulta de estoque não deverá alterar a quantidade disponível.
- Reserva física de estoque está fora do MVP.

## 8. Entidade `quotes`

Representa a cotação e, após aprovação, o pedido simulado.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `quote_id` | STRING | Sim | Chave primária |
| `customer_id` | STRING | Sim | Referência a `silver_companies.company_id` |
| `session_id` | STRING | Não | Sessão que originou a cotação |
| `status` | STRING | Sim | Estado atual da cotação |
| `total_amount` | DECIMAL(10,2) | Sim | Total congelado da cotação |
| `currency` | STRING | Sim | `BRL` no MVP |
| `created_at` | TIMESTAMP | Sim | Data de criação |
| `approved_at` | TIMESTAMP | Não | Data da aprovação |
| `approved_by` | STRING | Não | Usuário que aprovou |
| `rejection_reason` | STRING | Não | Motivo da rejeição |
| `payment_status` | STRING | Sim | Estado do pagamento simulado |
| `document_id` | STRING | Não | Documento relacionado |

### Estados possíveis

```text
draft
pending_approval
approved
rejected
paid
completed
```

### Regras de transição

```text
draft → pending_approval
pending_approval → approved
pending_approval → rejected
approved → paid
paid → completed
```

Transições inválidas:

- `draft → paid`;
- `draft → completed`;
- `pending_approval → paid`;
- `rejected → approved`;
- `completed → draft`.

### Regras de `quotes`

- Uma cotação deve possuir pelo menos um item.
- `total_amount` deve ser igual à soma dos subtotais dos itens.
- A cotação deve iniciar como `draft`.
- A cotação só pode ser enviada para pagamento após aprovação.
- `approved_by` é obrigatório quando `status = approved`.
- `rejection_reason` é obrigatório quando `status = rejected`.
- `payment_status` deve indicar explicitamente que o pagamento é simulado.
- O preço total não deve ser recalculado retroativamente se o catálogo mudar.

### Valores de `payment_status`

Os valores aceitos são:

```text
not_started
simulated_success
simulated_failure
```

A cotação deve iniciar com:

```text
payment_status = not_started
```

Após uma simulação bem-sucedida:

```text
payment_status = simulated_success
```

Após uma simulação malsucedida:

```text
payment_status = simulated_failure
```

Somente uma cotação com `payment_status = simulated_success` pode
seguir para a geração do documento simulado.

## 9. Entidade `quote_items`

Representa os produtos incluídos em uma cotação.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `quote_item_id` | STRING | Sim | Chave primária |
| `quote_id` | STRING | Sim | Chave estrangeira para `quotes` |
| `product_id` | STRING | Sim | Chave estrangeira para `products` |
| `quantity` | INT | Sim | Quantidade solicitada |
| `unit_price` | DECIMAL(10,2) | Sim | Preço no momento da cotação |
| `subtotal` | DECIMAL(10,2) | Sim | `quantity * unit_price` |

### Regras de `quote_items`

- `quantity` deve ser maior que zero.
- `product_id` deve existir em `products`.
- `unit_price` deve ser copiado do preço consultado no momento da cotação.
- `subtotal` deve ser calculado deterministicamente.
- O item deve preservar o preço mesmo se o preço atual do catálogo mudar.

## 10. Entidade `approvals`

Registra a aprovação humana necessária antes da confirmação comercial.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `approval_id` | STRING | Sim | Chave primária |
| `quote_id` | STRING | Sim | Cotação aprovada ou rejeitada |
| `requested_by` | STRING | Sim | Sistema ou assistente |
| `resolved_by` | STRING | Não | Usuário que resolveu a solicitação |
| `status` | STRING | Sim | `pending`, `approved` ou `rejected` |
| `reason` | STRING | Não | Justificativa |
| `created_at` | TIMESTAMP | Sim | Data da solicitação |
| `resolved_at` | TIMESTAMP | Não | Data da resolução |

### Regras de `approvals`

- Toda cotação deve possuir aprovação antes do pagamento.
- `resolved_by` é obrigatório quando `status = approved` ou
  `status = rejected`.
- `resolved_at` é obrigatório quando o status não for `pending`.
- Uma aprovação rejeitada não pode ser usada para liberar pagamento.
- A aprovação deve estar relacionada à mesma `quote_id` do pagamento.

## 11. Entidade `payments`

Representa exclusivamente pagamentos simulados.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `payment_id` | STRING | Sim | Chave primária |
| `quote_id` | STRING | Sim | Cotação relacionada |
| `status` | STRING | Sim | `simulated_success` ou `simulated_failure` |
| `amount` | DECIMAL(10,2) | Sim | Valor simulado |
| `currency` | STRING | Sim | `BRL` no MVP |
| `simulated` | BOOLEAN | Sim | Deve ser sempre `true` |
| `created_at` | TIMESTAMP | Sim | Data da simulação |

### Regras de `payments`

- `simulated` deve ser sempre `true`.
- Não haverá integração com instituição financeira.
- O pagamento só poderá ser simulado após aprovação.
- `amount` deve ser igual ao total aprovado da cotação.
- Um pagamento real está fora do escopo.

## 12. Entidade `documents`

Representa o documento simulado gerado após o pagamento simulado.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `document_id` | STRING | Sim | Chave primária |
| `quote_id` | STRING | Sim | Cotação relacionada |
| `document_type` | STRING | Sim | `simulated_receipt` |
| `has_fiscal_value` | BOOLEAN | Sim | Deve ser sempre `false` |
| `content_reference` | STRING | Não | Caminho ou referência do arquivo |
| `created_at` | TIMESTAMP | Sim | Data de geração |

### Regras de `documents`

- O documento deve ser explicitamente identificado como simulado.
- `has_fiscal_value` deve ser sempre `false`.
- O documento só poderá ser gerado após pagamento simulado.
- Não será emitida nota fiscal real.
- O documento deverá informar que não possui validade fiscal.

## 13. Entidade `conversation_events`

Registra eventos da conversa e das ferramentas utilizadas.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `event_id` | STRING | Sim | Chave primária |
| `session_id` | STRING | Sim | Sessão da conversa |
| `event_type` | STRING | Sim | Tipo do evento |
| `actor` | STRING | Sim | `customer`, `assistant`, `vendor` ou `system` |
| `content` | STRING | Não | Conteúdo ou resumo do evento |
| `tool_name` | STRING | Não | Ferramenta utilizada |
| `tool_reference_id` | STRING | Não | ID relacionado ao evento |
| `created_at` | TIMESTAMP | Sim | Momento do evento |

### Tipos de evento previstos

```text
session_started
message_received
question_asked
requirements_extracted
product_search
inventory_checked
price_checked
recommendation_created
quote_created
approval_requested
approval_resolved
payment_simulated
document_generated
handoff_to_human
error
```

### Regras de `conversation_events`

- Toda sessão deve possuir um evento `session_started`.
- Consultas de produto, estoque e preço devem ser registradas.
- Ações de aprovação, pagamento e geração de documento devem ser registradas.
- Eventos de erro e encaminhamento humano também devem ser registrados.
- O conteúdo não deve armazenar dados financeiros reais.

## 14. Relacionamento com o CRM existente

A tabela `quotes.customer_id` deverá referenciar:

```text
silver_silver_companies.company_id
```

O MVP trabalhará com clientes B2B previamente cadastrados na base de
empresas.

A tabela de funcionários poderá ser utilizada futuramente para:

- identificar compradores;
- recomendar contatos;
- associar aprovadores da empresa cliente;
- enriquecer o contexto comercial.

Essa funcionalidade não é obrigatória para a primeira implementação
do assistente.

## 15. Chaves e integridade

### Chaves primárias

- `products.product_id`;
- `inventory.inventory_id`;
- `quotes.quote_id`;
- `quote_items.quote_item_id`;
- `approvals.approval_id`;
- `payments.payment_id`;
- `documents.document_id`;
- `conversation_events.event_id`.

### Relacionamentos principais

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

## 16. Gold views

### `gold_product_catalog`

Modelo pronto para consulta do catálogo:

- `product_id`;
- `sku`;
- `product_name`;
- `category`;
- `description`;
- `use_cases`;
- `technical_specs`;
- `measurement_unit`;
- `min_operating_value`;
- `max_operating_value`;
- `price`;
- `currency`;
- `lead_time_days`;
- `active`.

### `gold_product_availability`

Modelo que combina catálogo e estoque:

- campos principais de `products`;
- `warehouse_id`;
- `available_quantity`;
- `reserved_quantity`;
- `inventory_updated_at`;
- `is_available`.

A coluna `is_available` deverá indicar se existe quantidade disponível,
mas não deverá considerar uma reserva física no MVP.

### `gold_quote_summary`

Modelo para acompanhamento das cotações:

- `quote_id`;
- `customer_id`;
- `status`;
- `total_amount`;
- `currency`;
- `created_at`;
- `approved_at`;
- `approved_by`;
- `payment_status`;
- quantidade de itens;
- quantidade total de produtos;
- status da aprovação.

### `gold_conversation_audit`

Modelo para auditoria:

- `session_id`;
- quantidade de mensagens;
- quantidade de perguntas;
- produtos consultados;
- recomendações realizadas;
- cotação criada;
- aprovação;
- pagamento simulado;
- documento gerado;
- encaminhamento humano;
- erros.

## 17. Dados sintéticos

Os dados sintéticos deverão:

- possuir identificadores consistentes;
- conter produtos compatíveis com as três categorias do MVP;
- incluir casos com estoque suficiente;
- incluir casos com estoque insuficiente;
- incluir casos sem produto compatível;
- incluir ao menos uma cotação aprovada;
- incluir ao menos uma cotação rejeitada;
- incluir ao menos um pagamento simulado;
- incluir ao menos um documento simulado;
- ser claramente identificados como dados de demonstração.

## 18. Decisões pendentes

As seguintes decisões serão detalhadas nas SPECs e ADRs:

- formato de `technical_specs`;
- quantidade inicial de produtos;
- regras exatas de compatibilidade;
- formato da interface de conversa;
- ferramenta utilizada pelo agente;
- estratégia de persistência das atualizações;
- formato do documento simulado;
- política de expiração da cotação.