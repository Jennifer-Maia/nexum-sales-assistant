# SPEC — generate_document

## 1. Objetivo

Gerar um documento simulado de confirmação para uma cotação que teve
um pagamento simulado concluído com sucesso.

O documento serve exclusivamente para demonstrar o encerramento da
jornada de vendas do Nexum Sales Assistant.

O documento:

- não possui validade fiscal;
- não representa uma nota fiscal;
- não comprova uma transação financeira real;
- não substitui um documento comercial oficial;
- não deve ser apresentado como emitido por uma autoridade fiscal.

## 2. Responsabilidade

A ferramenta é responsável por:

- validar a cotação;
- confirmar a existência de pagamento simulado bem-sucedido;
- reunir os dados da cotação e dos itens;
- gerar um comprovante simulado;
- registrar a referência do documento;
- atualizar o status da cotação para `completed`;
- registrar a geração para auditoria.

A ferramenta não é responsável por:

- emitir nota fiscal;
- emitir documento fiscal;
- processar pagamento;
- confirmar entrega;
- alterar preço;
- alterar estoque;
- aplicar impostos reais;
- gerar validade jurídica;
- corrigir dados comerciais.

## 3. Aviso obrigatório

O documento deverá conter, de forma visível:

```text
DOCUMENTO SIMULADO — SEM VALIDADE FISCAL, FINANCEIRA OU CONTÁBIL
```

Esse aviso deverá aparecer:

- no título do documento;
- no corpo do documento;
- na resposta da ferramenta;
- no registro da tabela `documents`;
- no evento de auditoria.

## 4. Entrada

A ferramenta deverá receber:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `session_id` | STRING | Sim | Sessão da conversa |
| `quote_id` | STRING | Sim | Cotação relacionada |
| `requested_by` | STRING | Sim | Ator que solicitou o documento |
| `document_format` | STRING | Não | `html`, `txt` ou `pdf` |

### Exemplo de entrada

```json
{
  "session_id": "SES-0001",
  "quote_id": "QTE-000001",
  "requested_by": "system",
  "document_format": "html"
}
```

## 5. Formato padrão

Quando `document_format` não for informado, o formato padrão será:

```text
html
```

Formatos aceitos no MVP:

```text
html
txt
```

O formato `pdf` poderá ser implementado caso seja necessário para a
demonstração, desde que o arquivo mantenha o aviso de documento
simulado e sem validade fiscal.

Formatos não aceitos deverão resultar em erro de validação.

## 6. Validações de entrada

A ferramenta deverá rejeitar a solicitação quando:

- `session_id` estiver ausente;
- `quote_id` estiver ausente;
- `requested_by` estiver ausente;
- `quote_id` não existir;
- a sessão não corresponder à cotação;
- o formato não for aceito;
- a cotação não possuir itens;
- o total da cotação for nulo ou inválido.

## 7. Pagamento obrigatório

A ferramenta só poderá gerar o documento quando existir um pagamento
relacionado à cotação com:

```text
payments.status = simulated_success
payments.simulated = true
```

A ferramenta deverá rejeitar a geração quando:

- não existir pagamento;
- o pagamento estiver com status `simulated_failure`;
- o pagamento estiver marcado como não simulado;
- o pagamento estiver relacionado a outra cotação;
- o pagamento possuir valor diferente do total da cotação.

### Exemplo de erro

```json
{
  "document_status": "payment_required",
  "error_code": "SUCCESSFUL_SIMULATED_PAYMENT_REQUIRED",
  "quote_id": "QTE-000001",
  "message": "A successful simulated payment is required before document generation"
}
```

## 8. Estado da cotação

Antes da geração, a cotação deverá estar em:

```text
paid
```

Após a geração bem-sucedida:

```text
paid → completed
```

A ferramenta não deverá gerar documento para cotações nos estados:

```text
draft
pending_approval
approved
rejected
```

## 9. Idempotência

A ferramenta deverá evitar a geração de documentos duplicados para a
mesma cotação.

Quando já existir um documento relacionado à cotação, a ferramenta
deverá retornar a referência existente:

```json
{
  "document_status": "already_generated",
  "document_id": "DOC-000001",
  "quote_id": "QTE-000001",
  "message": "A simulated document already exists for this quote"
}
```

A ferramenta não deverá criar um segundo documento simulado para a
mesma cotação no MVP.

## 10. Dados utilizados

O documento deverá utilizar dados persistidos nas tabelas:

```text
quotes
quote_items
products
payments
silver_companies
```

Dados que devem ser apresentados quando disponíveis:

- identificador da cotação;
- identificador do cliente;
- nome da empresa cliente;
- data da cotação;
- data do pagamento simulado;
- itens adquiridos;
- quantidade;
- preço unitário;
- subtotal;
- total;
- moeda;
- identificador do pagamento simulado;
- aviso de ausência de validade fiscal.

A ferramenta não deverá obter essas informações do texto livre do LLM.

## 11. Estrutura do documento

O documento deverá conter, no mínimo:

### Cabeçalho

```text
Nexum Industrial
DOCUMENTO SIMULADO
SEM VALIDADE FISCAL, FINANCEIRA OU CONTÁBIL
```

### Identificação

- `document_id`;
- `quote_id`;
- `customer_id`;
- nome da empresa cliente, quando disponível;
- data de geração.

### Itens

Para cada item:

- `product_id`;
- SKU;
- nome do produto;
- quantidade;
- preço unitário;
- subtotal;
- moeda.

### Totais

- subtotal geral;
- total da cotação;
- moeda;
- referência do pagamento simulado.

### Aviso final

```text
Este documento foi gerado exclusivamente para demonstração.
Não representa nota fiscal, comprovante de pagamento real ou
documento com validade jurídica, fiscal, financeira ou contábil.
```

## 12. Persistência

A ferramenta deverá criar um registro em:

```text
documents
```

Com os seguintes valores obrigatórios:

```text
document_id
quote_id
document_type = simulated_receipt
has_fiscal_value = false
content_reference
created_at
```

O campo:

```text
has_fiscal_value
```

deverá ser sempre:

```text
false
```

O campo `content_reference` deverá indicar o caminho ou identificador
do conteúdo gerado.

Exemplo:

```text
documents/simulated_receipt/QTE-000001.html
```

## 13. Saída bem-sucedida

```json
{
  "document_status": "generated",
  "document_id": "DOC-000001",
  "quote_id": "QTE-000001",
  "document_type": "simulated_receipt",
  "has_fiscal_value": false,
  "document_format": "html",
  "content_reference": "documents/simulated_receipt/QTE-000001.html",
  "quote_status": "completed",
  "message": "Documento simulado gerado sem validade fiscal, financeira ou contábil.",
  "created_at": "2026-08-26T22:00:00Z"
}
```

## 14. Falhas de pagamento

Quando o pagamento estiver com status:

```text
simulated_failure
```

a ferramenta deverá retornar:

```json
{
  "document_status": "payment_failed",
  "error_code": "PAYMENT_SIMULATION_FAILED",
  "quote_id": "QTE-000001",
  "message": "The simulated payment did not succeed. No document was generated."
}
```

A cotação deverá permanecer em:

```text
approved
```

ou no estado definido pela SPEC de pagamento.

Nenhum registro deverá ser criado em `documents`.

## 15. Falhas de dados

A ferramenta deverá interromper a geração quando:

- a cotação não possuir itens;
- houver produto inexistente em um item;
- o total da cotação estiver inconsistente;
- o pagamento possuir valor diferente do total;
- a empresa cliente não puder ser identificada;
- o conteúdo não puder ser criado;
- o formato solicitado não for suportado.

A ferramenta não deverá preencher informações ausentes com valores
inventados.

## 16. Auditoria

A execução deverá registrar um evento em:

```text
conversation_events
```

O evento deverá conter:

```text
event_type = document_generated
session_id
tool_name = generate_document
tool_reference_id = document_id
created_at
```

O conteúdo deverá permitir identificar:

- cotação;
- cliente;
- documento gerado;
- formato;
- pagamento simulado relacionado;
- valor total;
- responsável pela geração;
- aviso de ausência de validade.

Quando a geração falhar, a falha também deverá ser registrada.

## 17. Segurança

A ferramenta não poderá:

- emitir nota fiscal;
- gerar documento fiscal;
- utilizar certificado digital;
- conectar-se à SEFAZ;
- declarar impostos reais;
- declarar quitação financeira real;
- utilizar dados de cartão;
- gerar documento com aparência de nota fiscal válida;
- omitir o aviso de simulação;
- gerar documento antes do pagamento simulado bem-sucedido;
- alterar estoque;
- alterar o valor da cotação.

## 18. Critérios de aceite

### CA01 — Pagamento obrigatório

A ferramenta não deve gerar documento sem pagamento
`simulated_success`.

### CA02 — Pagamento simulado

O pagamento relacionado deve possuir:

```text
simulated = true
```

### CA03 — Documento simulado

O documento deve possuir:

```text
document_type = simulated_receipt
has_fiscal_value = false
```

### CA04 — Aviso obrigatório

O conteúdo deve informar que não possui validade fiscal, financeira
ou contábil.

### CA05 — Dados confiáveis

Itens, quantidades, preços e total devem vir das tabelas estruturadas.

### CA06 — Estado da cotação

Uma geração bem-sucedida deve alterar:

```text
paid → completed
```

### CA07 — Falha de pagamento

Nenhum documento deve ser criado quando o pagamento simulado falhar.

### CA08 — Idempotência

A ferramenta não deve criar mais de um documento para a mesma cotação.

### CA09 — Auditoria

A geração ou falha deve criar evento em `conversation_events`.

### CA10 — Sem validade fiscal

O documento não pode ser apresentado como nota fiscal ou comprovante
de pagamento real.

### CA11 — Não alterar estoque

A geração do documento não deve alterar disponibilidade ou reserva.

### CA12 — Não inventar

A ferramenta não deve inventar cliente, produto, preço, quantidade,
total ou pagamento.

## 19. Exemplo de fluxo completo

```text
create_quote
    ↓
quotes.status = draft
    ↓
request_human_approval
    ↓
quotes.status = pending_approval
    ↓
aprovação humana
    ↓
quotes.status = approved
    ↓
simulate_payment
    ↓
payments.status = simulated_success
    ↓
quotes.status = paid
    ↓
generate_document
    ↓
documents criado
    ↓
quotes.status = completed
```

## 20. Dependências

A ferramenta depende de:

- `quotes`;
- `quote_items`;
- `products`;
- `silver_companies`;
- `payments`;
- `documents`;
- `conversation_events`;
- SPEC `simulate_payment`;
- contrato definido em `docs/data_model.md`.

## 21. Fora do escopo

- nota fiscal;
- cupom fiscal;
- documento fiscal;
- recibo com validade legal;
- pagamento real;
- emissão contábil;
- integração com ERP;
- integração com transportadora;
- confirmação de entrega;
- baixa de estoque;
- reserva de estoque;
- estorno;
- cancelamento real;
- assinatura digital.