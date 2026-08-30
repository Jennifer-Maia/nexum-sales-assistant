# SPEC — search_products

## 1. Objetivo

Buscar produtos ativos no catálogo da Nexum Industrial que sejam
compatíveis com os requisitos técnicos informados pelo cliente.

A ferramenta deve retornar somente produtos existentes nos dados
estruturados e compatíveis com os filtros recebidos.

A ferramenta não deve interpretar livremente a necessidade do cliente.
A interpretação da mensagem e a extração dos requisitos acontecem antes,
em uma etapa separada.

## 2. Responsabilidade

A ferramenta é responsável por:

- consultar o catálogo de produtos;
- filtrar produtos ativos;
- verificar compatibilidade com os requisitos estruturados;
- ordenar os resultados;
- retornar dados suficientes para uma recomendação;
- registrar a busca para auditoria.

A ferramenta não é responsável por:

- conversar diretamente com o cliente;
- inventar produtos;
- inventar especificações;
- consultar ou alterar estoque;
- consultar ou alterar preços;
- criar cotações;
- confirmar pedidos;
- decidir sozinha qual produto será comprado.

## 3. Entrada

A ferramenta deverá receber um objeto estruturado com os requisitos
identificados na conversa.

### Campos obrigatórios

| Campo | Tipo | Descrição |
|---|---|---|
| `category` | STRING | Categoria técnica da necessidade |
| `session_id` | STRING | Identificador da sessão da conversa |

### Campos opcionais

| Campo | Tipo | Descrição |
|---|---|---|
| `min_required_value` | DECIMAL | Limite mínimo exigido |
| `max_required_value` | DECIMAL | Limite máximo exigido |
| `measurement_unit` | STRING | Unidade da faixa informada |
| `quantity` | INT | Quantidade desejada |
| `use_case` | STRING | Caso de uso identificado |
| `limit` | INT | Quantidade máxima de resultados |
| `product_ids` | ARRAY<STRING> | Produtos específicos, quando aplicável |

### Exemplo de entrada

```json
{
  "session_id": "SES-0001",
  "category": "temperature",
  "min_required_value": 0,
  "max_required_value": 150,
  "measurement_unit": "C",
  "quantity": 20,
  "use_case": "monitoring_multiple_machines",
  "limit": 3
}
```

## 4. Categorias aceitas no MVP

A ferramenta deverá aceitar somente:

```text
temperature
pressure
vibration
```

Valores fora dessa lista deverão resultar em erro de validação ou
encaminhamento para atendimento humano.

## 5. Regras de compatibilidade

### 5.1 Produto ativo

Somente produtos com:

```text
active = true
```

podem ser retornados.

### 5.2 Categoria

A categoria do produto deve ser igual à categoria solicitada:

```text
product.category = input.category
```

### 5.3 Faixa operacional

Quando os limites forem informados, o produto deverá suportar toda
a faixa solicitada:

```text
product.min_operating_value <= input.min_required_value
```

e:

```text
product.max_operating_value >= input.max_required_value
```

Exemplo:

```text
Necessidade: 0 °C a 150 °C
Produto: -20 °C a 180 °C
Resultado: compatível
```

Produto com faixa de 20 °C a 100 °C não será considerado compatível.

### 5.4 Unidade de medição

Quando a unidade for informada, ela deverá ser compatível com a unidade
do produto.

A ferramenta não deverá realizar conversões de unidade no MVP.

Exemplo:

```text
C e °C podem ser normalizados para a mesma unidade.
bar e psi não devem ser convertidos automaticamente.
```

### 5.5 Caso de uso

Quando o campo `use_case` for informado, a busca poderá utilizar o
campo estruturado de casos de uso do produto como filtro complementar.

O caso de uso não deverá substituir os filtros técnicos obrigatórios.

### 5.6 Quantidade

A quantidade solicitada não será usada para excluir o produto nesta
ferramenta.

A disponibilidade deverá ser verificada separadamente por
`check_inventory`.

A ferramenta poderá retornar a quantidade solicitada como contexto,
mas não deverá afirmar que o produto está disponível.

## 6. Ordenação

Os resultados deverão ser ordenados por:

1. compatibilidade técnica;
2. produto ativo;
3. menor prazo;
4. menor preço;
5. `product_id`, como critério determinístico final.

A ferramenta não deverá ordenar por preferência subjetiva do modelo
de linguagem.

## 7. Limite de resultados

O valor padrão de `limit` será:

```text
3
```

O limite máximo permitido no MVP será:

```text
10
```

Quando o cliente pedir mais produtos, a ferramenta deverá respeitar
o limite máximo definido pelo sistema.

## 8. Saída com resultados

Quando houver produtos compatíveis, a ferramenta deverá retornar:

| Campo | Tipo | Descrição |
|---|---|---|
| `session_id` | STRING | Sessão da consulta |
| `search_status` | STRING | `success` |
| `result_count` | INT | Quantidade retornada |
| `products` | ARRAY | Produtos compatíveis |
| `searched_at` | TIMESTAMP | Momento da consulta |

Cada produto retornado deverá conter:

```text
product_id
sku
product_name
category
description
use_cases
technical_specs
measurement_unit
min_operating_value
max_operating_value
price
currency
lead_time_days
active
```

### Exemplo de saída

```json
{
  "session_id": "SES-0001",
  "search_status": "success",
  "result_count": 2,
  "searched_at": "2026-08-26T21:00:00Z",
  "products": [
    {
      "product_id": "PRD-TEMP-001",
      "sku": "NEX-TEMP-001",
      "product_name": "Sensor de Temperatura Industrial T150",
      "category": "temperature",
      "measurement_unit": "C",
      "min_operating_value": -20,
      "max_operating_value": 180,
      "price": 780.00,
      "currency": "BRL",
      "lead_time_days": 3,
      "active": true
    }
  ]
}
```

## 9. Saída sem resultados

Quando nenhum produto for compatível, a ferramenta deverá retornar:

```json
{
  "session_id": "SES-0001",
  "search_status": "no_compatible_product",
  "result_count": 0,
  "products": [],
  "searched_at": "2026-08-26T21:00:00Z"
}
```

Nesse caso, o assistente deverá:

- informar que não encontrou uma opção compatível;
- não sugerir produto incompatível como se fosse adequado;
- explicar quais informações foram usadas na busca;
- oferecer encaminhamento para um vendedor.

## 10. Falhas de validação

A ferramenta deverá rejeitar a consulta quando:

- `session_id` estiver ausente;
- `category` estiver ausente;
- `category` não for aceita;
- `min_required_value` for maior que `max_required_value`;
- valores técnicos forem inválidos;
- `quantity` for menor ou igual a zero;
- `limit` for menor que 1;
- `limit` for maior que 10;
- a unidade for incompatível com a categoria.

### Exemplo de erro

```json
{
  "session_id": "SES-0001",
  "search_status": "validation_error",
  "error_code": "INVALID_REQUIRED_RANGE",
  "message": "min_required_value must be less than or equal to max_required_value"
}
```

## 11. Falhas de dados

A ferramenta deverá sinalizar erro quando:

- a tabela de produtos não estiver disponível;
- houver produto sem categoria;
- houver produto ativo sem especificações essenciais;
- houver faixa operacional inconsistente;
- houver preço inválido;
- houver prazo inválido.

A ferramenta não deverá corrigir silenciosamente os dados durante a consulta.

## 12. Fonte de dados

A consulta deverá utilizar a camada Gold:

```text
gold_product_catalog
```

A Gold deverá ser construída a partir das tabelas Silver de produtos.

A ferramenta não deverá consultar diretamente um arquivo CSV.

## 13. Preço, estoque e prazo

Esta ferramenta poderá retornar o preço e o prazo cadastrados no catálogo
como referência, mas não deverá afirmar disponibilidade.

A disponibilidade deverá ser confirmada pela ferramenta:

```text
check_inventory
```

O resultado final apresentado ao cliente deverá combinar:

```text
search_products
+
check_inventory
```

## 14. Auditoria

Cada execução deverá registrar um evento em:

```text
conversation_events
```

O evento deverá conter, no mínimo:

```text
event_type = product_search
session_id
tool_name = search_products
tool_reference_id
content
created_at
```

O registro deverá permitir identificar:

- quais filtros foram utilizados;
- quando a consulta ocorreu;
- quantos produtos foram encontrados;
- quais produtos foram retornados;
- se houve erro ou ausência de resultados.

## 15. Critérios de aceite

### CA01 — Busca por categoria

Dada uma categoria válida, a ferramenta retorna somente produtos
daquela categoria.

### CA02 — Produtos ativos

Produtos inativos nunca aparecem nos resultados.

### CA03 — Compatibilidade de faixa

A ferramenta retorna somente produtos que cobrem integralmente a faixa
solicitada.

### CA04 — Limite de resultados

A ferramenta retorna no máximo três produtos por padrão e nunca mais de
dez.

### CA05 — Nenhum resultado

Quando não houver produto compatível, a saída deverá indicar
`no_compatible_product`.

### CA06 — Dados reais do catálogo

Nome, especificações, preço e prazo devem existir no catálogo consultado.

### CA07 — Não consultar estoque indevidamente

A ferramenta não deverá afirmar disponibilidade sem executar
`check_inventory`.

### CA08 — Reprodutibilidade

Com os mesmos dados de entrada e o mesmo catálogo, a consulta deverá
produzir resultados consistentes.

### CA09 — Auditoria

Cada execução deverá gerar um evento de busca registrado.

### CA10 — Não inventar

A ferramenta não poderá retornar um produto que não exista em
`gold_product_catalog`.

## 16. Exemplo de jornada atendida

### Entrada do cliente

> Preciso monitorar 20 máquinas entre 0 °C e 150 °C.

### Requisitos extraídos

```json
{
  "category": "temperature",
  "min_required_value": 0,
  "max_required_value": 150,
  "measurement_unit": "C",
  "quantity": 20
}
```

### Resultado esperado

A ferramenta retorna até três sensores de temperatura que:

- possuem categoria `temperature`;
- suportam a faixa de 0 °C a 150 °C;
- estão ativos;
- possuem especificações registradas.

A ferramenta ainda não confirma se há 20 unidades disponíveis.
Essa responsabilidade pertence a `check_inventory`.

## 17. Dependências

A ferramenta depende de:

- `gold_product_catalog`;
- contrato de dados definido em `docs/data_model.md`;
- dados de produtos válidos na Silver;
- sessão de conversa válida;
- mecanismo de registro em `conversation_events`.

## 18. Fora do escopo

- recomendar produtos sem requisitos mínimos;
- consultar fornecedores externos;
- fazer conversão automática de unidades;
- alterar produtos;
- alterar preços;
- alterar estoque;
- reservar produtos;
- criar cotações;
- negociar descontos;
- confirmar pedidos;
- realizar pagamentos.