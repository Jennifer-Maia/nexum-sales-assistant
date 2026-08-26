# ADR-001 — Fusão de Quotes e Orders no MVP

## Status

Aceita.

## Data

2026-08-26

## Contexto

O Nexum Sales Assistant precisa representar o fluxo comercial entre:

1. criação de uma cotação;
2. revisão humana;
3. aprovação;
4. pagamento simulado;
5. geração de documento simulado.

No projeto inicial, foi considerada a criação de duas entidades:

- `quotes`, para representar cotações;
- `orders`, para representar pedidos confirmados.

Entretanto, o MVP não terá:

- pedido real;
- integração com ERP;
- faturamento;
- baixa de estoque;
- logística;
- pagamento real;
- emissão fiscal;
- reserva física de estoque.

O fluxo comercial será totalmente simulado e terá uma única jornada
controlada por estados.

## Decisão

No MVP, será utilizada uma única entidade comercial:

```text
quotes
```

A tabela `quotes` representará tanto a cotação preliminar quanto o
registro comercial simulado após aprovação e pagamento.

Não será criada uma tabela `orders` no MVP.

## Máquina de estados

A entidade `quotes` utilizará os seguintes estados:

```text
draft
pending_approval
approved
rejected
paid
completed
```

Fluxo principal:

```text
draft
   ↓
pending_approval
   ↓
approved
   ↓
paid
   ↓
completed
```

Fluxo de rejeição:

```text
pending_approval
   ↓
rejected
```

## Transições permitidas

```text
draft → pending_approval
pending_approval → approved
pending_approval → rejected
approved → paid
paid → completed
```

## Transições proibidas

Não serão permitidas as seguintes transições:

```text
draft → approved
draft → paid
draft → completed
pending_approval → paid
pending_approval → completed
rejected → approved
rejected → paid
completed → draft
completed → paid
```

## Justificativa

A fusão foi escolhida porque:

- reduz a quantidade de entidades no MVP;
- evita duplicação de dados entre cotação e pedido;
- simplifica a máquina de estados;
- mantém o fluxo comercial explícito;
- facilita a implementação das ferramentas;
- reduz a quantidade de joins;
- torna a demonstração mais fácil de entender;
- está alinhada ao escopo simulado do projeto.

A cotação não será apenas um documento comercial estático. Ela
representará o registro da jornada comercial desde a criação até a
conclusão simulada.

## Modelo relacionado

A entidade `quotes` será relacionada a:

```text
quotes
   ├── quote_items
   ├── approvals
   ├── payments
   └── documents
```

Relacionamento com o cliente:

```text
silver_companies.company_id
   └── quotes.customer_id
```

## Campos relevantes de `quotes`

A tabela deverá conter, no mínimo:

```text
quote_id
customer_id
session_id
status
total_amount
currency
created_at
approved_at
approved_by
rejection_reason
payment_status
document_id
```

## Preservação histórica

Embora a entidade seja única, os dados históricos serão preservados:

- `quote_items.unit_price` manterá o preço no momento da cotação;
- `quote_items.subtotal` manterá o valor calculado;
- `quotes.total_amount` manterá o total da cotação;
- `approvals` manterá o histórico da decisão humana;
- `payments` manterá a tentativa de pagamento simulado;
- `documents` manterá a referência do documento gerado.

Alterações futuras no catálogo não deverão modificar uma cotação
já criada.

## Regras de aprovação

Uma cotação só poderá avançar para pagamento quando:

```text
quotes.status = approved
```

e existir uma aprovação válida:

```text
approvals.status = approved
approvals.resolved_by IS NOT NULL
approvals.resolved_at IS NOT NULL
```

Quando a aprovação for positiva, a cotação deverá registrar:

```text
quotes.approved_by
quotes.approved_at
```

## Regras de pagamento

O pagamento será exclusivamente simulado.

Uma cotação poderá avançar de:

```text
approved → paid
```

somente quando houver um pagamento com:

```text
payments.status = simulated_success
payments.simulated = true
```

## Regras de conclusão

Uma cotação poderá avançar de:

```text
paid → completed
```

somente após a geração bem-sucedida do documento simulado.

O documento deverá possuir:

```text
documents.document_type = simulated_receipt
documents.has_fiscal_value = false
```

## Alternativas consideradas

### Alternativa 1 — Criar tabelas separadas `quotes` e `orders`

Essa alternativa representaria:

```text
quotes
   ↓
orders
```

A cotação seria convertida em pedido após aprovação.

#### Motivos para não escolher

- adiciona complexidade ao MVP;
- exige regras de conversão entre entidades;
- cria duplicação de informações;
- exige mais chaves e relacionamentos;
- não existe pedido real no escopo atual;
- pode sugerir uma integração comercial que ainda não existe.

Essa alternativa poderá ser considerada futuramente caso o projeto
passe a representar pedidos reais.

### Alternativa 2 — Usar uma tabela genérica `commercial_transactions`

Essa alternativa usaria uma entidade abstrata para representar
cotações, pedidos e outros eventos comerciais.

#### Motivos para não escolher

- torna o modelo menos intuitivo;
- aumenta a quantidade de estados genéricos;
- dificulta a leitura por usuários não técnicos;
- não oferece benefício necessário para o MVP;
- pode esconder diferenças importantes entre cotação e pagamento.

### Alternativa 3 — Manter somente `quotes` sem estados posteriores

Essa alternativa manteria a cotação apenas como uma entidade de
pré-venda, sem representar aprovação, pagamento e conclusão.

#### Motivos para não escolher

- não representaria a jornada completa;
- dificultaria a demonstração do human-in-the-loop;
- não registraria claramente a progressão comercial;
- exigiria outras entidades para controlar o fluxo.

## Consequências positivas

- modelo de dados menor;
- menor quantidade de tabelas;
- fluxo mais simples;
- implementação mais rápida;
- demonstração mais clara;
- menos duplicação;
- validações centralizadas;
- transições de estado explícitas.

## Consequências negativas

- `quotes` terá responsabilidade maior;
- o significado de `quote` dependerá do estado atual;
- uma futura separação entre cotação e pedido exigirá migração;
- o modelo não representa pedidos reais de forma independente;
- relatórios futuros poderão precisar filtrar os estados da cotação.

## Impacto nas ferramentas

### `create_quote`

Cria:

```text
quotes.status = draft
```

### `request_human_approval`

Transiciona:

```text
draft → pending_approval
```

Depois registra:

```text
pending_approval → approved
```

ou:

```text
pending_approval → rejected
```

### `simulate_payment`

Quando bem-sucedido:

```text
approved → paid
```

### `generate_document`

Quando bem-sucedido:

```text
paid → completed
```

## Impacto nas camadas de dados

### Bronze

Serão ingeridos dados de:

```text
bronze_quotes
bronze_quote_items
```

Não haverá:

```text
bronze_orders
```

no MVP.

### Silver

Serão criadas:

```text
silver_quotes
silver_quote_items
```

Não haverá:

```text
silver_orders
```

no MVP.

### Gold

A visão:

```text
gold_quote_summary
```

deverá considerar o estado atual da cotação.

## Critérios para reconsiderar esta decisão

A criação de uma entidade `orders` deverá ser reconsiderada se o projeto
passar a incluir pelo menos uma das seguintes necessidades:

- integração com ERP;
- pedido confirmado independente da cotação;
- reserva ou baixa de estoque;
- logística;
- faturamento;
- nota fiscal;
- entrega;
- cancelamento de pedido;
- devolução;
- pagamento real;
- múltiplas versões de uma cotação;
- conversão formal de cotação em pedido;
- acompanhamento do ciclo de vida do pedido.

## Resultado esperado

O MVP deverá demonstrar o seguinte fluxo:

```text
Cliente descreve necessidade
   ↓
Produtos compatíveis encontrados
   ↓
Estoque consultado
   ↓
Cotação criada
   ↓
Aprovação humana
   ↓
Pagamento simulado
   ↓
Documento simulado
   ↓
Cotação concluída
```

A decisão mantém o projeto simples sem remover os controles de
auditoria, aprovação humana e preservação histórica.
