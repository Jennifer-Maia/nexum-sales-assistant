# SPEC — simulate_payment

## 1. Objetivo

Simular o pagamento de uma cotação previamente aprovada.

A ferramenta existe apenas para demonstrar o fluxo completo do
Nexum Sales Assistant:

```text
cotação criada
    ↓
aprovação humana
    ↓
pagamento simulado
    ↓
documento simulado
```

A ferramenta não movimenta dinheiro, não se conecta a instituições
financeiras e não possui validade financeira ou contábil.

## 2. Responsabilidade

A ferramenta é responsável por:

- validar a cotação;
- confirmar que houve aprovação humana;
- validar o valor da simulação;
- registrar um pagamento simulado;
- atualizar o status de pagamento da cotação;
- alterar o status da cotação para `paid` quando a simulação for bem-sucedida;
- registrar a operação para auditoria.

A ferramenta não é responsável por:

- processar pagamentos reais;
- validar cartão, boleto ou transferência real;
- alterar estoque;
- reservar produtos;
- aprovar a cotação;
- alterar o valor aprovado;
- gerar documento;
- emitir nota fiscal;
- confirmar entrega.

## 3. Aviso obrigatório

Toda resposta da ferramenta deverá identificar explicitamente que a
operação é simulada.

Mensagem obrigatória:

```text
Este pagamento é uma simulação sem valor financeiro, fiscal ou contábil.
```

A mesma informação deverá aparecer:

- na resposta da ferramenta;
- no registro de pagamento;
- no evento de auditoria;
- no documento simulado posterior.

## 4. Entrada

A ferramenta deverá receber:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `session_id` | STRING | Sim | Sessão da conversa |
| `quote_id` | STRING | Sim | Cotação a ser paga |
| `requested_by` | STRING | Sim | Ator que iniciou a simulação |
| `simulation_result` | STRING | Não | `success` ou `failure` |
| `simulation_reference` | STRING | Não | Referência interna da simulação |

### Exemplo de entrada

```json
{
  "session_id": "SES-0001",
  "quote_id": "QTE-000001",
  "requested_by": "vendor-001",
  "simulation_result": "success",
  "simulation_reference": "SIM-PAY-000001"
}
```

## 5. Valores aceitos

O campo `simulation_result` deverá aceitar somente:

```text
success
failure
```

Quando não for informado, o sistema poderá utilizar:

```text
success
```

desde que todas as validações sejam aprovadas.

A ferramenta não deverá aceitar valores como:

```text
approved
confirmed
real
completed
paid
```

Esses valores podem gerar confusão entre uma simulação e um pagamento
real.

## 6. Validações de entrada

A ferramenta deverá rejeitar a solicitação quando:

- `session_id` estiver ausente;
- `quote_id` estiver ausente;
- `requested_by` estiver ausente;
- `simulation_result` não for aceito;
- a cotação não existir;
- a sessão não corresponder à cotação;
- a cotação não possuir itens;
- o total da cotação for nulo ou negativo;
- a cotação já possuir um pagamento bem-sucedido.

### Exemplo de erro

```json
{
  "payment_status": "validation_error",
  "error_code": "QUOTE_NOT_FOUND",
  "quote_id": "QTE-UNKNOWN",
  "message": "The quote could not be found"
}
```

## 7. Aprovação obrigatória

A ferramenta só poderá executar a simulação quando a cotação atender
simultaneamente às condições:

```text
quotes.status = approved
```

e existir um registro correspondente em `approvals` com:

```text
approvals.status = approved
approvals.resolved_by IS NOT NULL
approvals.resolved_at IS NOT NULL
```

A ferramenta deverá rejeitar a simulação quando a cotação estiver em:

```text
draft
pending_approval
rejected
paid
completed
```
A cotação também deverá possuir os campos de aprovação preenchidos:

```text
quotes.approved_by IS NOT NULL
quotes.approved_at IS NOT NULL
``` 

### Exemplo

```json
{
  "payment_status": "approval_required",
  "error_code": "QUOTE_NOT_APPROVED",
  "quote_id": "QTE-000001",
  "message": "A human-approved quote is required before payment simulation"
}
```

## 8. Valor do pagamento

O valor simulado deverá ser obtido de:

```text
quotes.total_amount
```

A ferramenta não deverá aceitar um valor de pagamento fornecido
pelo modelo ou pelo cliente.

O valor registrado em `payments.amount` deverá ser exatamente igual
ao total aprovado da cotação.

```text
payments.amount = quotes.total_amount
```

A ferramenta não deverá:

- alterar o total da cotação;
- aplicar desconto;
- adicionar taxa;
- arredondar silenciosamente;
- aceitar valor informado externamente.

## 9. Moeda

No MVP, a moeda aceita será:

```text
BRL
```

O registro de pagamento deverá utilizar a mesma moeda da cotação:

```text
payments.currency = quotes.currency
```

A ferramenta deverá rejeitar a operação quando a moeda da cotação
não estiver configurada ou for diferente da moeda suportada no MVP.

## 10. Resultado simulado com sucesso

Quando todas as validações forem aprovadas e
`simulation_result = success`:

1. criar um registro em `payments`;
2. definir `payments.status = simulated_success`;
3. definir `payments.simulated = true`;
4. utilizar o total da cotação como valor;
5. atualizar `quotes.payment_status`;
6. atualizar `quotes.status` para `paid`;
7. registrar o evento de auditoria;
8. indicar que a próxima ação é gerar o documento simulado.

### Exemplo de saída

```json
{
  "payment_status": "simulated_success",
  "payment_id": "PAY-000001",
  "quote_id": "QTE-000001",
  "quote_status": "paid",
  "amount": 15600.00,
  "currency": "BRL",
  "simulated": true,
  "simulation_reference": "SIM-PAY-000001",
  "message": "Este pagamento é uma simulação sem valor financeiro, fiscal ou contábil.",
  "next_action": "generate_document"
}
```

## 11. Resultado simulado com falha

Quando `simulation_result = failure`:

1. criar um registro em `payments`;
2. definir `payments.status = simulated_failure`;
3. definir `payments.simulated = true`;
4. não atualizar a cotação para `paid`;
5. manter a cotação como `approved`;
6. registrar o evento de auditoria;
7. indicar que é necessária nova tentativa ou revisão humana.

### Exemplo de saída

```json
{
  "payment_status": "simulated_failure",
  "payment_id": "PAY-000002",
  "quote_id": "QTE-000001",
  "quote_status": "approved",
  "amount": 15600.00,
  "currency": "BRL",
  "simulated": true,
  "simulation_reference": "SIM-PAY-000002",
  "message": "A simulação de pagamento falhou. Nenhum valor real foi movimentado.",
  "next_action": "human_follow_up"
}
```

## 12. Persistência

A ferramenta deverá persistir os dados em:

```text
payments
```

Campos mínimos do pagamento:

```text
payment_id
quote_id
status
amount
currency
simulated
created_at
```

O registro deverá manter:

```text
simulated = true
```

em todas as situações.

A ferramenta não deverá utilizar uma tabela ou integração de pagamento
real.

## 13. Transições de estado

### Sucesso

```text
quotes.status:
approved → paid

quotes.payment_status:
not_started → simulated_success
```

### Falha

```text
quotes.status:
approved → approved

quotes.payment_status:
not_started → simulated_failure
```

O pagamento simulado com falha não deverá alterar o estado comercial
da cotação para `rejected`.

## 14. Idempotência

A ferramenta deverá evitar a criação de múltiplos pagamentos simulados
bem-sucedidos para a mesma cotação.

Quando a cotação já possuir um pagamento com:

```text
status = simulated_success
```

a ferramenta deverá retornar:

```json
{
  "payment_status": "already_simulated",
  "quote_id": "QTE-000001",
  "message": "A successful simulated payment already exists for this quote",
  "next_action": "generate_document"
}
```

A ferramenta não deverá criar um segundo pagamento bem-sucedido.

Pagamentos simulados com falha poderão ser registrados novamente,
desde que cada tentativa possua uma referência distinta.

## 15. Verificação de consistência

Antes de registrar o pagamento, a ferramenta deverá validar:

- `quotes.total_amount` não é nulo;
- `quotes.total_amount` é maior que zero;
- o total corresponde à soma dos itens;
- a moeda está definida;
- a aprovação pertence à mesma cotação;
- a cotação ainda está em `approved`;
- não existe pagamento bem-sucedido anterior.

Caso exista inconsistência, a ferramenta deverá interromper a operação
e encaminhar para revisão humana.

## 16. Auditoria

Cada execução deverá registrar evento em:

```text
conversation_events
```

### Sucesso

```text
event_type = payment_simulated
tool_name = simulate_payment
tool_reference_id = payment_id
```

### Falha

O evento também deverá ser registrado como:

```text
event_type = payment_simulated
tool_name = simulate_payment
tool_reference_id = payment_id
```

O deverá indicar:

- cotação;
- resultado da simulação;
- valor;
- moeda;
- referência da simulação;
- responsável pela execução;
- aprovação utilizada;
- mensagem de que nenhum valor real foi movimentado.

## 17. Segurança e limites

A ferramenta não poderá:

- conectar-se a APIs financeiras reais;
- receber dados de cartão;
- receber senha, token bancário ou código de segurança;
- movimentar dinheiro;
- alterar preço;
- alterar quantidade;
- alterar estoque;
- confirmar entrega;
- emitir nota fiscal;
- gerar documento com validade fiscal;
- executar sem aprovação humana;
- tratar a simulação como pagamento real.

## 18. Critérios de aceite

### CA01 — Aprovação obrigatória

Uma cotação não aprovada não pode iniciar simulação de pagamento.

### CA02 — Sucesso

Uma cotação aprovada com resultado `success` deve gerar um pagamento
com status `simulated_success`.

### CA03 — Falha

Uma cotação aprovada com resultado `failure` deve gerar um pagamento
com status `simulated_failure`.

### CA04 — Estado da cotação

Após sucesso, a cotação deve passar para `paid`.

Após falha, a cotação deve permanecer `approved`.

### CA05 — Valor confiável

O valor do pagamento deve ser obtido de `quotes.total_amount`.

### CA06 — Simulação explícita

Todo pagamento deve possuir `simulated = true`.

### CA07 — Sem pagamento real

A ferramenta não deve solicitar nem armazenar dados financeiros reais.

### CA08 — Idempotência

A ferramenta não deve gerar dois pagamentos simulados bem-sucedidos
para a mesma cotação.

### CA09 — Auditoria

Toda execução deve gerar evento em `conversation_events`.

### CA10 — Próxima ação

Após sucesso, a próxima ação deve ser `generate_document`.

Após falha, a próxima ação deve ser `human_follow_up`.

### CA11 — Não alterar estoque

A simulação de pagamento não deve alterar
`available_quantity` ou `reserved_quantity`.

### CA12 — Não inventar

A ferramenta não pode criar valores, moedas ou condições comerciais
que não estejam nos dados estruturados.

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
```

## 20. Dependências

A ferramenta depende de:

- `quotes`;
- `quote_items`;
- `approvals`;
- `payments`;
- `conversation_events`;
- SPEC `create_quote`;
- SPEC `request_human_approval`;
- contrato definido em `docs/data_model.md`.

## 21. Fora do escopo

- pagamento real;
- gateway de pagamento;
- cartão;
- boleto real;
- Pix real;
- transferência bancária;
- conciliação financeira;
- estorno;
- parcelamento;
- crédito;
- faturamento;
- emissão fiscal;
- reserva ou baixa de estoque;
- geração de documento.