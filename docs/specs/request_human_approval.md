# SPEC — request_human_approval

## 1. Objetivo

Solicitar e registrar a aprovação humana de uma cotação antes que ela
possa avançar para pagamento simulado ou geração de documento.

A aprovação humana é obrigatória porque a cotação pode envolver:

- valor comercial;
- quantidade;
- disponibilidade;
- condição de venda;
- responsabilidade da empresa;
- confirmação de uma ação comercial.

A ferramenta não deve aprovar automaticamente uma cotação.

## 2. Responsabilidade

A ferramenta é responsável por:

- validar a cotação;
- criar uma solicitação de aprovação;
- alterar a cotação para `pending_approval`;
- registrar o responsável pela solicitação;
- impedir avanço sem aprovação;
- registrar a decisão humana;
- alterar a cotação para `approved` ou `rejected`;
- registrar auditoria.

A ferramenta não é responsável por:

- criar a cotação;
- alterar preços;
- aplicar descontos;
- alterar estoque;
- reservar produtos;
- realizar pagamento;
- gerar documento;
- aprovar em nome do usuário.

## 3. Operações

A ferramenta deverá suportar duas operações:

```text
request
resolve
```

### `request`

Solicita aprovação humana para uma cotação em estado `draft`.

### `resolve`

Registra a decisão de um aprovador humano sobre uma solicitação
pendente.

## 4. Entrada para solicitação

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `operation` | STRING | Sim | Deve ser `request` |
| `session_id` | STRING | Sim | Sessão da conversa |
| `quote_id` | STRING | Sim | Cotação a ser aprovada |
| `requested_by` | STRING | Sim | Usuário ou sistema solicitante |
| `reason` | STRING | Não | Motivo da solicitação |

### Exemplo

```json
{
  "operation": "request",
  "session_id": "SES-0001",
  "quote_id": "QTE-000001",
  "requested_by": "assistant",
  "reason": "Cotação pronta para revisão comercial"
}
```

## 5. Validações da solicitação

A solicitação deverá ser rejeitada quando:

- `session_id` estiver ausente;
- `quote_id` estiver ausente;
- `requested_by` estiver ausente;
- a cotação não existir;
- a cotação não possuir itens;
- a cotação estiver em estado diferente de `draft`;
- o total da cotação for inválido;
- houver preço ou estoque inconsistente.

A ferramenta não deverá criar uma segunda aprovação para uma cotação
que já esteja em `pending_approval`.

## 6. Transição para aprovação

Quando a solicitação for válida:

```text
quotes.status:
draft → pending_approval
```

A ferramenta deverá criar um registro em:

```text
approvals
```

Com:

```text
status = pending
requested_by = valor recebido
resolved_by = null
resolved_at = null
```

Quando a decisão for `approved`, a ferramenta deverá também atualizar
os campos de resumo da cotação:

```text
quotes.approved_by = approvals.resolved_by
quotes.approved_at = approvals.resolved_at
```

Quando a decisão for `rejected`, esses campos não deverão ser preenchidos
como aprovação.

## 7. Saída da solicitação

```json
{
  "approval_status": "requested",
  "approval_id": "APR-000001",
  "quote_id": "QTE-000001",
  "quote_status": "pending_approval",
  "session_id": "SES-0001",
  "next_action": "human_review"
}
```

## 8. Entrada para resolução

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `operation` | STRING | Sim | Deve ser `resolve` |
| `session_id` | STRING | Sim | Sessão da conversa |
| `approval_id` | STRING | Sim | Solicitação pendente |
| `decision` | STRING | Sim | `approved` ou `rejected` |
| `resolved_by` | STRING | Sim | Identificador do aprovador |
| `reason` | STRING | Sim quando rejeitada | Justificativa da decisão |

### Exemplo de aprovação

```json
{
  "operation": "resolve",
  "session_id": "SES-0001",
  "approval_id": "APR-000001",
  "decision": "approved",
  "resolved_by": "vendor-001",
  "reason": "Cotação revisada e aprovada"
}
```

### Exemplo de rejeição

```json
{
  "operation": "resolve",
  "session_id": "SES-0001",
  "approval_id": "APR-000001",
  "decision": "rejected",
  "resolved_by": "vendor-001",
  "reason": "Quantidade precisa ser revisada com o cliente"
}
```

## 9. Validações da resolução

A resolução deverá ser rejeitada quando:

- `approval_id` não existir;
- a aprovação já estiver resolvida;
- `decision` não for `approved` ou `rejected`;
- `resolved_by` estiver ausente;
- a decisão for `rejected` e `reason` estiver ausente;
- a cotação relacionada não estiver em `pending_approval`;
- a sessão não corresponder à cotação;
- o aprovador não estiver autorizado no contexto da demonstração.

No MVP, a autorização poderá utilizar uma lista simples de usuários
aprovadores documentada nos dados sintéticos.

## 10. Transições de estado

### Aprovação

```text
approvals.status:
pending → approved

quotes.status:
pending_approval → approved
```

### Rejeição

```text
approvals.status:
pending → rejected

quotes.status:
pending_approval → rejected
```

Após a rejeição, a cotação não poderá avançar diretamente para pagamento.

## 11. Saída de aprovação

```json
{
  "approval_status": "approved",
  "approval_id": "APR-000001",
  "quote_id": "QTE-000001",
  "quote_status": "approved",
  "resolved_by": "vendor-001",
  "resolved_at": "2026-08-26T21:30:00Z",
  "next_action": "simulate_payment"
}
```

## 12. Saída de rejeição

```json
{
  "approval_status": "rejected",
  "approval_id": "APR-000001",
  "quote_id": "QTE-000001",
  "quote_status": "rejected",
  "resolved_by": "vendor-001",
  "reason": "Quantidade precisa ser revisada com o cliente",
  "resolved_at": "2026-08-26T21:30:00Z",
  "next_action": "human_follow_up"
}
```

## 13. Integridade da aprovação

Uma cotação só poderá avançar para pagamento quando:

```text
quotes.status = approved
```

e existir uma aprovação correspondente com:

```text
approvals.status = approved
approvals.resolved_by IS NOT NULL
approvals.resolved_at IS NOT NULL
```

Uma aprovação não poderá ser reutilizada para outra cotação.

## 14. Auditoria

A ferramenta deverá registrar eventos em:

```text
conversation_events
```

### Ao solicitar aprovação

```text
event_type = approval_requested
tool_name = request_human_approval
tool_reference_id = approval_id
```

### Ao resolver aprovação

```text
event_type = approval_resolved
tool_name = request_human_approval
tool_reference_id = approval_id
```

O registro deverá conter:

- `session_id`;
- `quote_id`;
- `approval_id`;
- ação realizada;
- decisão;
- aprovador;
- justificativa;
- data e hora.

## 15. Segurança

A ferramenta não poderá:

- aprovar automaticamente;
- aceitar aprovação do próprio assistente;
- aceitar aprovação sem identificador humano;
- alterar o total da cotação;
- alterar preço;
- alterar estoque;
- iniciar pagamento antes da aprovação;
- gerar documento antes do pagamento;
- apagar uma rejeição registrada.

## 16. Critérios de aceite

### CA01 — Solicitar aprovação

Uma cotação válida em `draft` deve passar para
`pending_approval`.

### CA02 — Criar registro

A solicitação deve criar um registro em `approvals` com status `pending`.

### CA03 — Aprovar

Uma aprovação humana válida deve alterar a cotação para `approved`.

### CA04 — Rejeitar

Uma rejeição válida deve alterar a cotação para `rejected`.

### CA05 — Bloquear pagamento

Uma cotação em `draft`, `pending_approval` ou `rejected` não pode
iniciar pagamento.

### CA06 — Exigir aprovador

A cotação não pode ser aprovada sem `resolved_by`.

### CA07 — Exigir justificativa

Uma rejeição deve possuir justificativa.

### CA08 — Impedir duplicidade

Uma cotação não pode possuir duas solicitações de aprovação pendentes.

### CA09 — Auditoria

A solicitação e a resolução devem gerar eventos de auditoria.

### CA10 — Não alterar valores

A aprovação não deve alterar preço, quantidade, estoque ou total.

### CA11 — Não aprovar automaticamente

O assistente não pode resolver uma aprovação em seu próprio nome.

## 17. Dependências

A ferramenta depende de:

- `quotes`;
- `approvals`;
- `conversation_events`;
- `silver_companies`;
- SPEC `create_quote`;
- contrato definido em `docs/data_model.md`.

## 18. Fora do escopo

- múltiplos níveis de aprovação;
- aprovação por valor;
- assinatura digital;
- autorização corporativa real;
- integração com identidade corporativa;
- alteração da cotação após rejeição;
- renegociação automática;
- pagamento;
- geração de documento.