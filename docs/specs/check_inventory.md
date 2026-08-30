# SPEC — check_inventory

## 1. Objetivo

Consultar a disponibilidade de um produto para uma quantidade solicitada.

A ferramenta deve informar se existe estoque suficiente com base nos dados
estruturados da Nexum Industrial.

A ferramenta não deve reservar, reduzir ou alterar o estoque.

## 2. Responsabilidade

A ferramenta é responsável por:

- validar o produto informado;
- consultar a disponibilidade atual;
- comparar a quantidade disponível com a quantidade solicitada;
- retornar o resultado de forma determinística;
- registrar a consulta para auditoria.

A ferramenta não é responsável por:

- buscar produtos;
- recomendar produtos;
- alterar estoque;
- reservar produtos;
- criar cotações;
- confirmar pedidos;
- realizar pagamentos;
- decidir se a venda deve ser aprovada.

## 3. Entrada

A ferramenta deverá receber:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `session_id` | STRING | Sim | Identificador da sessão |
| `product_id` | STRING | Sim | Produto que será consultado |
| `quantity_requested` | INT | Sim | Quantidade desejada |
| `warehouse_id` | STRING | Não | Estoque a consultar |

### Exemplo de entrada

```json
{
  "session_id": "SES-0001",
  "product_id": "PRD-TEMP-001",
  "quantity_requested": 20,
  "warehouse_id": "WH-MAIN"
}
```

## 4. Validações de entrada

A ferramenta deverá rejeitar a consulta quando:

- `session_id` estiver ausente;
- `product_id` estiver ausente;
- `quantity_requested` estiver ausente;
- `quantity_requested` for menor ou igual a zero;
- `warehouse_id` for informado, mas estiver vazio;
- o produto não existir;
- o produto estiver inativo.

### Exemplo de erro

```json
{
  "session_id": "SES-0001",
  "product_id": "PRD-TEMP-001",
  "inventory_status": "validation_error",
  "error_code": "INVALID_QUANTITY",
  "message": "quantity_requested must be greater than zero"
}
```

## 5. Fonte de dados

A consulta deverá utilizar:

```text
gold_product_availability
```

Essa Gold deverá combinar:

- dados do produto;
- dados do estoque;
- quantidade disponível;
- data da última atualização;
- identificador do estoque.

A ferramenta não deverá consultar diretamente:

- arquivos CSV;
- dados enviados pelo modelo de linguagem;
- valores armazenados apenas no histórico da conversa.

## 6. Regra de disponibilidade

A disponibilidade será calculada pela comparação:

```text
available_quantity >= quantity_requested
```

### Produto disponível

Quando houver quantidade suficiente:

```text
available = true
```

### Produto indisponível

Quando a quantidade disponível for menor que a quantidade solicitada:

```text
available = false
```

A ferramenta deverá retornar a quantidade disponível, mas não deverá
prometer reposição ou disponibilidade futura.

## 7. Quantidade considerada

No MVP, a ferramenta deverá utilizar:

```text
available_quantity
```

A coluna `reserved_quantity` poderá ser exibida como contexto, mas não
será utilizada para implementar reserva física.

A ferramenta não deverá:

- diminuir `available_quantity`;
- aumentar `reserved_quantity`;
- criar registro de reserva;
- bloquear o produto para outro cliente.

## 8. Estoque padrão

Quando `warehouse_id` não for informado, a ferramenta deverá consultar:

```text
WH-MAIN
```

O identificador do estoque padrão deverá ser documentado e utilizado
de forma consistente nos dados sintéticos.

## 9. Saída em caso de disponibilidade

Quando a quantidade for suficiente, a ferramenta deverá retornar:

```json
{
  "session_id": "SES-0001",
  "product_id": "PRD-TEMP-001",
  "warehouse_id": "WH-MAIN",
  "inventory_status": "available",
  "available": true,
  "quantity_requested": 20,
  "available_quantity": 42,
  "reserved_quantity": 0,
  "inventory_updated_at": "2026-08-26T20:00:00Z",
  "checked_at": "2026-08-26T21:00:00Z"
}
```

## 10. Saída em caso de estoque insuficiente

Quando a quantidade disponível for menor que a quantidade solicitada:

```json
{
  "session_id": "SES-0001",
  "product_id": "PRD-TEMP-001",
  "warehouse_id": "WH-MAIN",
  "inventory_status": "insufficient_stock",
  "available": false,
  "quantity_requested": 50,
  "available_quantity": 42,
  "reserved_quantity": 0,
  "inventory_updated_at": "2026-08-26T20:00:00Z",
  "checked_at": "2026-08-26T21:00:00Z"
}
```

Nesse caso, o assistente deverá:

- informar a quantidade disponível;
- informar que a quantidade solicitada não está disponível;
- não afirmar que o produto está indisponível permanentemente;
- não prometer uma data de reposição;
- encaminhar para análise humana quando necessário.

## 11. Saída quando não houver registro de estoque

Quando o produto existir, mas não houver registro correspondente em
`gold_product_availability`, a ferramenta deverá retornar:

```json
{
  "session_id": "SES-0001",
  "product_id": "PRD-TEMP-001",
  "warehouse_id": "WH-MAIN",
  "inventory_status": "inventory_not_found",
  "available": false,
  "quantity_requested": 20,
  "available_quantity": null,
  "reserved_quantity": null,
  "checked_at": "2026-08-26T21:00:00Z"
}
```

A ausência de registro não deverá ser interpretada como estoque zero sem
que isso esteja explicitamente definido pela camada de dados.

O assistente deverá informar que a disponibilidade não pôde ser confirmada.

## 12. Saída quando o produto não existir

Quando `product_id` não existir no catálogo:

```json
{
  "session_id": "SES-0001",
  "product_id": "PRD-UNKNOWN",
  "warehouse_id": "WH-MAIN",
  "inventory_status": "product_not_found",
  "available": false,
  "quantity_requested": 20,
  "checked_at": "2026-08-26T21:00:00Z"
}
```

A ferramenta não deverá criar ou sugerir um produto substituto.

## 13. Dados desatualizados

A ferramenta deverá retornar `inventory_updated_at` para permitir que
o consumidor avalie a atualidade da informação.

No MVP, a ferramenta deverá sinalizar o dado como potencialmente
desatualizado quando a atualização exceder o limite definido pelo sistema.

Limite inicial:

```text
7 dias
```

Quando o estoque estiver além desse limite, a saída deverá incluir:

```text
inventory_status = stale_inventory
```

A quantidade poderá ser exibida como referência, mas a disponibilidade
deverá ser confirmada por um vendedor antes da cotação final.

### Exemplo

```json
{
  "session_id": "SES-0001",
  "product_id": "PRD-TEMP-001",
  "warehouse_id": "WH-MAIN",
  "inventory_status": "stale_inventory",
  "available": false,
  "quantity_requested": 20,
  "available_quantity": 42,
  "inventory_updated_at": "2026-08-10T20:00:00Z",
  "checked_at": "2026-08-26T21:00:00Z",
  "message": "Inventory data requires human confirmation because it is older than 7 days"
}
```

## 14. Erros de qualidade dos dados

A ferramenta deverá sinalizar erro quando:

- `available_quantity` for nulo;
- `available_quantity` for negativo;
- `reserved_quantity` for negativo;
- houver mais de um registro válido para o mesmo produto e estoque;
- `inventory_updated_at` for inválido;
- o produto estiver ativo, mas sem estoque consistente.

A ferramenta não deverá corrigir silenciosamente esses dados.

## 15. Auditoria

Cada execução deverá registrar um evento em:

```text
conversation_events
```

O evento deverá conter, no mínimo:

```text
event_type = inventory_checked
session_id
tool_name = check_inventory
tool_reference_id = product_id
content
created_at
```

O conteúdo registrado deverá permitir identificar:

- produto consultado;
- quantidade solicitada;
- estoque consultado;
- quantidade disponível;
- resultado da disponibilidade;
- data da atualização do estoque;
- existência de dado desatualizado;
- ocorrência de erro.

A auditoria não deverá registrar informações de pagamento real.

## 16. Não alteração do estoque

A ferramenta é somente de consulta.

Após a execução:

```text
available_quantity não muda
reserved_quantity não muda
```

Qualquer futura reserva de estoque deverá ser implementada em uma
ferramenta separada e documentada em uma SPEC própria.

## 17. Critérios de aceite

### CA01 — Quantidade suficiente

Dado um produto com 42 unidades disponíveis e uma solicitação de 20,
a ferramenta deve retornar `available = true`.

### CA02 — Quantidade insuficiente

Dado um produto com 42 unidades disponíveis e uma solicitação de 50,
a ferramenta deve retornar `available = false`.

### CA03 — Produto inexistente

Dado um `product_id` inexistente, a ferramenta deve retornar
`product_not_found`.

### CA04 — Produto inativo

Dado um produto inativo, a ferramenta não deve confirmar disponibilidade.

### CA05 — Estoque ausente

Dado um produto sem registro de estoque, a ferramenta deve retornar
`inventory_not_found`.

### CA06 — Estoque desatualizado

Dado um estoque com atualização superior a 7 dias, a ferramenta deve
sinalizar `stale_inventory`.

### CA07 — Entrada inválida

Dada uma quantidade menor ou igual a zero, a ferramenta deve retornar
erro de validação.

### CA08 — Não alterar estoque

A execução da ferramenta não deve modificar os dados de estoque.

### CA09 — Fonte confiável

O resultado deve ser calculado a partir de
`gold_product_availability`.

### CA10 — Auditoria

Cada consulta deve gerar um evento em `conversation_events`.

### CA11 — Não inventar

A ferramenta não pode informar disponibilidade sem registro
correspondente nos dados estruturados.

## 18. Exemplo de jornada

### Requisitos extraídos

```json
{
  "category": "temperature",
  "min_required_value": 0,
  "max_required_value": 150,
  "quantity": 20
}
```

### Resultado da busca

A ferramenta `search_products` retorna:

```text
PRD-TEMP-001
PRD-TEMP-002
PRD-TEMP-003
```

### Consulta de estoque

A ferramenta `check_inventory` consulta cada produto selecionado.

Resultado:

```text
PRD-TEMP-001 → 42 disponíveis → compatível com a quantidade
PRD-TEMP-002 → 8 disponíveis → quantidade insuficiente
PRD-TEMP-003 → estoque não encontrado → confirmação humana necessária
```

O assistente não deverá apresentar os três produtos como igualmente
disponíveis.

## 19. Dependências

A ferramenta depende de:

- `gold_product_availability`;
- `products.product_id`;
- `inventory.product_id`;
- `conversation_events`;
- contrato definido em `docs/data_model.md`;
- sessão de conversa válida.

## 20. Fora do escopo

- reservar estoque;
- reduzir estoque;
- atualizar estoque;
- estimar reposição;
- consultar fornecedores;
- prometer prazo de reposição;
- substituir produtos automaticamente;
- negociar quantidade;
- criar cotação;
- confirmar pedido;
- realizar pagamento.