# SPEC — create_quote

## 1. Objetivo

Criar uma cotação preliminar para um cliente B2B a partir de produtos
selecionados e quantidades informadas.

A ferramenta deve:

- validar cliente e produtos;
- validar quantidades;
- consultar dados comerciais confiáveis;
- verificar disponibilidade;
- congelar os preços utilizados;
- calcular os subtotais e o total;
- criar a cotação com status inicial `draft`;
- encaminhar a cotação para aprovação humana.

A ferramenta não deve:

- confirmar o pedido;
- reservar estoque;
- alterar estoque;
- aplicar descontos automaticamente;
- realizar pagamento;
- gerar documento;
- aprovar a própria cotação.

## 2. Responsabilidade

A ferramenta é responsável por:

- criar o cabeçalho da cotação;
- criar os itens da cotação;
- consultar preço atual;
- validar estoque suficiente;
- calcular valores;
- manter o preço histórico da cotação;
- associar a cotação à sessão da conversa;
- registrar a criação para auditoria.

A ferramenta não é responsável por:

- interpretar a necessidade do cliente;
- buscar produtos por linguagem natural;
- recomendar produtos;
- negociar condições comerciais;
- aprovar a cotação;
- processar pagamento;
- emitir documento fiscal ou simulado.

## 3. Entrada

A ferramenta deverá receber:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `session_id` | STRING | Sim | Sessão da conversa |
| `customer_id` | STRING | Sim | Empresa cliente |
| `items` | ARRAY | Sim | Produtos e quantidades |
| `currency` | STRING | Não | Moeda da cotação |
| `valid_until` | DATE | Não | Data de validade |
| `requested_by` | STRING | Sim | Ator que solicitou a cotação |

Cada item deverá conter:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `product_id` | STRING | Sim | Produto selecionado |
| `quantity` | INT | Sim | Quantidade solicitada |

### Exemplo de entrada

```json
{
  "session_id": "SES-0001",
  "customer_id": "C0001",
  "currency": "BRL",
  "valid_until": "2026-09-02",
  "requested_by": "assistant",
  "items": [
    {
      "product_id": "PRD-TEMP-001",
      "quantity": 20
    },
    {
      "product_id": "PRD-GATE-001",
      "quantity": 1
    }
  ]
}
```

## 4. Validações de entrada

A ferramenta deverá rejeitar a solicitação quando:

- `session_id` estiver ausente;
- `customer_id` estiver ausente;
- `items` estiver ausente ou vazio;
- `requested_by` estiver ausente;
- a moeda for diferente de `BRL` no MVP;
- houver item sem `product_id`;
- houver item sem `quantity`;
- alguma quantidade for menor ou igual a zero;
- o mesmo produto aparecer mais de uma vez na lista;
- a data de validade for anterior à data de criação.

## 5. Validação do cliente

O `customer_id` deverá existir na tabela de empresas válida para o MVP.

Fonte esperada:

```text
silver_companies
```

ou uma Gold de clientes validada.

Quando o cliente não existir, a ferramenta deverá retornar:

```json
{
  "quote_status": "validation_error",
  "error_code": "CUSTOMER_NOT_FOUND",
  "message": "The customer could not be found in the approved customer dataset"
}
```

A ferramenta não deverá criar automaticamente um novo cliente.

## 6. Validação dos produtos

Cada `product_id` deverá:

- existir no catálogo;
- estar ativo;
- possuir preço válido;
- possuir moeda válida;
- possuir prazo válido;
- possuir especificações essenciais.

Produtos inexistentes ou inativos não poderão ser incluídos na cotação.

### Erro de produto

```json
{
  "quote_status": "validation_error",
  "error_code": "PRODUCT_NOT_AVAILABLE",
  "product_id": "PRD-UNKNOWN",
  "message": "The product does not exist or is not active"
}
```

## 7. Validação do estoque

Antes de criar a cotação, a ferramenta deverá verificar a disponibilidade
de cada item por meio da lógica definida em `check_inventory`.

A cotação não deverá ser criada quando:

- a quantidade solicitada for maior que o estoque disponível;
- o estoque não for encontrado;
- o estoque estiver desatualizado e exigir confirmação humana;
- houver inconsistência nos dados de inventário.

A ferramenta deverá retornar os itens com problema.

### Exemplo

```json
{
  "quote_status": "inventory_validation_error",
  "error_code": "INSUFFICIENT_STOCK",
  "items": [
    {
      "product_id": "PRD-TEMP-001",
      "quantity_requested": 50,
      "available_quantity": 42
    }
  ]
}
```

A consulta de estoque não deverá reservar nem modificar as quantidades.

## 8. Fonte do preço

O preço deverá ser consultado na fonte estruturada de catálogo.

Fonte esperada:

```text
gold_product_catalog
```

ou uma tabela Gold equivalente aprovada.

O valor informado no pedido de criação não poderá substituir o preço
consultado no catálogo.

A ferramenta não deverá aceitar:

- preço enviado pelo modelo;
- preço informado livremente pelo cliente;
- desconto não aprovado;
- preço negativo;
- moeda diferente da cotação.

## 9. Congelamento do preço

Ao criar a cotação, o preço atual deverá ser copiado para:

```text
quote_items.unit_price
```

O subtotal deverá ser calculado como:

```text
subtotal = quantity * unit_price
```

O total deverá ser calculado como:

```text
total_amount = SUM(subtotal)
```

Alterações futuras no catálogo não deverão modificar o valor de uma
cotação já criada.

## 10. Status inicial

Toda cotação criada por esta ferramenta deverá iniciar como:

```text
draft
```

Depois da criação, o sistema poderá solicitar aprovação humana,
alterando o status para:

```text
pending_approval
```

A alteração para `pending_approval` deverá ser registrada como um evento
separado ou em uma operação explicitamente documentada.

A ferramenta `create_quote` não deverá marcar a cotação como aprovada.

## 11. Identificadores

A ferramenta deverá gerar identificadores únicos para:

- `quote_id`;
- `quote_item_id`.

Formato sugerido:

```text
QTE-000001
QTI-000001
```

A implementação poderá utilizar UUIDs, desde que os identificadores sejam
únicos e consistentes.

## 12. Validade da cotação

A cotação poderá receber uma data de validade.

Quando não for informada, deverá ser utilizada a política padrão do MVP:

```text
valid_until = created_at + 7 dias
```

A validade da cotação não representa garantia de estoque após esse
período.

O preço congelado permanece registrado, mas qualquer nova confirmação
deverá passar por validação comercial.

## 13. Saída bem-sucedida

Quando todas as validações forem aprovadas, a ferramenta deverá retornar:

```json
{
  "quote_status": "created",
  "quote_id": "QTE-000001",
  "session_id": "SES-0001",
  "customer_id": "C0001",
  "status": "draft",
  "currency": "BRL",
  "items": [
    {
      "quote_item_id": "QTI-000001",
      "product_id": "PRD-TEMP-001",
      "quantity": 20,
      "unit_price": 780.00,
      "subtotal": 15600.00
    }
  ],
  "total_amount": 15600.00,
  "created_at": "2026-08-26T21:00:00Z",
  "valid_until": "2026-09-02",
  "next_action": "request_human_approval"
}
```

## 14. Persistência

A cotação deverá ser persistida em:

```text
quotes
```

Os produtos da cotação deverão ser persistidos em:

```text
quote_items
```

A criação deverá manter a relação:

```text
quotes.quote_id
    └── quote_items.quote_id
```

Uma cotação sem itens não é válida.

## 15. Aprovação humana

Após a criação da cotação, a próxima ação esperada será:

```text
request_human_approval
```

A aprovação deverá ser executada por uma ferramenta separada.

A ferramenta `create_quote` não poderá:

- alterar `status` para `approved`;
- preencher `approved_by`;
- preencher `approved_at`;
- criar um pagamento;
- gerar documento.

## 16. Auditoria

A execução deverá registrar eventos em:

```text
conversation_events
```

O evento deverá conter, no mínimo:

```text
event_type = quote_created
session_id
tool_name = create_quote
tool_reference_id = quote_id
content
created_at
```

O registro deverá permitir identificar:

- cliente- produtos;
- quantidades;
- preços utilizados;
- total calculado;
- status inicial;
- resultado das validações;
- usuário ou agente que solicitou a cotação.

Quando a cotação não for criada por erro de validação, a falha também
deverá ser registrada.

## 17. Falhas de qualidade

A ferramenta deverá interromper a criação quando:

- houver produto sem preço;
- houver produto sem estoque válido;
- houver quantidade negativa;
- houver duplicidade de item;
- houver total inconsistente;
- houver cliente inexistente;
- houver moeda incompatível;
- houver preço inválido;
- houver dados obrigatórios ausentes.

A ferramenta não deverá corrigir silenciosamente valores inválidos.

## 18. Regras de segurança

A ferramenta não poderá:

- aceitar preço calculado pelo LLM;
- aceitar descontos não aprovados;
- alterar estoque;
- reservar estoque;
- confirmar pedido;
- executar pagamento;
- gerar nota fiscal;
- gerar documento com validade fiscal;
- ignorar a aprovação humana.

## 19. Critérios de aceite

### CA01 — Criar cotação válida

Dado um cliente válido e produtos ativos com estoque suficiente,
a ferramenta deve criar uma cotação com status `draft`.

### CA02 — Criar itens

Cada produto solicitado deve gerar um registro em `quote_items`.

### CA03 — Calcular subtotal

O subtotal deve ser calculado como quantidade multiplicada pelo preço
consultado no catálogo.

### CA04 — Calcular total

O total da cotação deve ser igual à soma dos subtotais.

### CA05 — Congelar preço

O `unit_price` do item deve permanecer registrado mesmo que o preço
atual do catálogo seja alterado depois.

### CA06 — Cliente inexistente

A ferramenta deve rejeitar a cotação quando o cliente não existir.

### CA07 — Produto inativo

A ferramenta deve rejeitar a cotação quando um produto estiver inativo.

### CA08 — Estoque insuficiente

A ferramenta deve rejeitar a cotação quando qualquer item não possuir
estoque suficiente.

### CA09 — Sem reserva

A criação da cotação não deve alterar `available_quantity` ou
`reserved_quantity`.

### CA10 — Aprovação obrigatória

A cotação criada não pode avançar diretamente para `approved`, `paid`
ou `completed`.

### CA11 — Auditoria

A criação ou rejeição da cotação deve gerar evento em
`conversation_events`.

### CA12 — Reprodutibilidade

Com os mesmos dados de entrada e as mesmas fontes, a ferramenta deve
calcular os mesmos valores.

### CA13 — Não inventar

A ferramenta não pode criar produto, preço, estoque ou condição comercial
que não exista nos dados estruturados.

## 20. Exemplo de fluxo

```text
search_products
        ↓
check_inventory
        ↓
create_quote
        ↓
quotes.status = draft
        ↓
request_human_approval
        ↓
quotes.status = pending_approval
```

A ferramenta `create_quote` encerra sua responsabilidade ao criar a
cotação preliminar e indicar que a próxima ação é solicitar aprovação.

## 21. Dependências

A ferramenta depende de:

- `silver_companies` ou Gold de clientes;
- `gold_product_catalog`;
- `gold_product_availability`;
- `quotes`;
- `quote_items`;
- `conversation_events`;
- contrato definido em `docs/data_model.md`;
- SPECs `search_products` e `check_inventory`.

## 22. Fora do escopo

- aprovação humana;
- descontos;
- negociação;
- reserva de estoque;
- baixa de estoque;
- pedido real;
- integração com ERP;
- pagamento;
- documento;
- faturamento;
- logística;
- emissão fiscal.