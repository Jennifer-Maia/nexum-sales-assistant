# ADR-003 — Separação entre `approved_by` e `resolved_by`

## Status

Aceita.

## Data

2026-08-26

## Contexto

O fluxo de aprovação do Nexum Sales Assistant possui duas entidades
relacionadas, mas com responsabilidades diferentes:

- `quotes`, que representa a cotação e seu estado comercial;
- `approvals`, que registra a solicitação e a resolução da aprovação.

Durante a revisão do modelo, identificou-se que o responsável por uma
aprovação poderia ser representado pelo mesmo campo nas duas tabelas.

Entretanto, uma solicitação de aprovação pode terminar em dois resultados:

```text
approved
rejected
```

Por isso, o nome `approved_by` não representa corretamente todos os
casos da tabela `approvals`.

## Decisão

Serão utilizados campos diferentes em cada entidade:

### Na tabela `quotes`

```text
approved_by
approved_at
```

Esses campos representam o resumo da aprovação positiva da cotação.

### Na tabela `approvals`

```text
resolved_by
resolved_at
```

Esses campos representam a resolução da solicitação, seja ela aprovada
ou rejeitada.

## Responsabilidades dos campos

### `quotes.approved_by`

Indica o usuário que aprovou a cotação.

Esse campo somente deverá ser preenchido quando:

```text
quotes.status = approved
```

Quando a cotação for rejeitada, `quotes.approved_by` não deverá ser
preenchido como se houvesse aprovação.

### `quotes.approved_at`

Indica o momento em que a cotação foi aprovada.

Esse campo somente deverá ser preenchido quando a decisão for:

```text
approved
```

### `approvals.resolved_by`

Indica o usuário que resolveu a solicitação de aprovação.

Esse campo deverá ser preenchido tanto quando a decisão for:

```text
approved
```

quanto quando for:

```text
rejected
```

### `approvals.resolved_at`

Indica o momento em que a solicitação foi resolvida.

Esse campo deverá ser preenchido quando o status deixar de ser:

```text
pending
```

## Modelo resultante

```text
quotes
├── approved_by
└── approved_at

approvals
├── resolved_by
└── resolved_at
```

## Fluxo de aprovação positiva

Quando a decisão for aprovada:

```text
approvals.status = approved
approvals.resolved_by = identificador do aprovador
approvals.resolved_at = momento da decisão
```

A cotação deverá ser atualizada com:

```text
quotes.status = approved
quotes.approved_by = approvals.resolved_by
quotes.approved_at = approvals.resolved_at
```

## Fluxo de rejeição

Quando a decisão for rejeitada:

```text
approvals.status = rejected
approvals.resolved_by = identificador do responsável
approvals.resolved_at = momento da decisão
approvals.reason = justificativa
```

A cotação deverá ser atualizada com:

```text
quotes.status = rejected
quotes.rejection_reason = approvals.reason
```

Os campos abaixo não deverão representar uma aprovação positiva:

```text
quotes.approved_by
quotes.approved_at
```

## Regras de integridade

Uma aprovação válida deverá atender às seguintes condições.

### Solicitação pendente

```text
approvals.status = pending
approvals.resolved_by IS NULL
approvals.resolved_at IS NULL
```

### Solicitação aprovada

```text
approvals.status = approved
approvals.resolved_by IS NOT NULL
approvals.resolved_at IS NOT NULL
```

### Solicitação rejeitada

```text
approvals.status = rejected
approvals.resolved_by IS NOT NULL
approvals.resolved_at IS NOT NULL
approvals.reason IS NOT NULL
```

## Condição para pagamento

Uma cotação somente poderá avançar para pagamento quando as duas
condições forem verdadeiras:

```text
quotes.status = approved
```

e:

```text
approvals.status = approved
approvals.resolved_by IS NOT NULL
approvals.resolved_at IS NOT NULL
```

Além disso, a cotação aprovada deverá possuir:

```text
quotes.approved_by IS NOT NULL
quotes.approved_at IS NOT NULL
```

## Justificativa

A separação foi escolhida porque:

- `approved_by` representa exclusivamente uma aprovação positiva;
- `resolved_by` representa qualquer resolução da solicitação;
- uma rejeição também precisa registrar quem tomou a decisão;
- os nomes dos campos refletem melhor o significado dos dados;
- evita interpretar uma rejeição como aprovação;
- melhora a auditabilidade;
- facilita consultas e relatórios;
- mantém o histórico da solicitação separado do resumo comercial.

## Alternativas consideradas

### Alternativa 1 — Usar somente `approved_by` nas duas tabelas

Essa alternativa usaria:

```text
approvals.approved_by
```

mesmo quando a solicitação fosse rejeitada.

#### Motivos para não escolher

- o nome não representa uma rejeição;
- pode sugerir que a solicitação sempre foi aprovada;
- reduz a clareza do modelo;
- dificulta auditoria;
- gera semântica incorreta para o responsável pela rejeição.

### Alternativa 2 — Usar somente `resolved_by` nas duas tabelas

Essa alternativa eliminaria:

```text
quotes.approved_by
```

e usaria `resolved_by` também na cotação.

#### Motivos para não escolher

- a cotação precisa de um resumo explícito da aprovação;
- relatórios de cotação ficariam menos intuitivos;
- `quotes` possui contexto comercial, enquanto `approvals` possui
  contexto de workflow;
- o nome `approved_by` é mais preciso para uma cotação aprovada.

### Alternativa 3 — Criar apenas uma tabela de aprovação sem campos na cotação

Essa alternativa manteria o responsável somente em `approvals`.

#### Motivos para não escolher

- consultas da cotação exigiriam sempre um join;
- dificultaria visões Gold resumidas;
- reduziria a conveniência para relatórios operacionais;
- esconderia informações importantes do estado da cotação.

### Alternativa 4 — Criar uma tabela separada de usuários aprovadores

Essa alternativa criaria uma entidade específica para aprovadores.

#### Motivos para não escolher no MVP

- adiciona complexidade desnecessária;
- não há integração com identidade corporativa;
- a demonstração utilizará identificadores simples;
- a autorização real está fora do escopo.

Essa alternativa poderá ser reconsiderada no futuro.

## Consequências positivas

- semântica mais precisa;
- distinção clara entre aprovação e resolução;
- rejeições auditáveis;
- relatórios mais fáceis de interpretar;
- validação de pagamento mais segura;
- menor risco de confundir decisão humana com estado comercial.

## Consequências negativas

- existem quatro campos relacionados ao responsável e ao momento;
- é necessário sincronizar o resumo da cotação com a aprovação;
- a implementação precisa validar consistência entre as tabelas;
- consultas podem precisar analisar `quotes` e `approvals`;
- alterações futuras no fluxo de aprovação podem exigir novos campos.

## Impacto nas tabelas

### `quotes`

Manter:

```text
approved_at
approved_by
rejection_reason
```

### `approvals`

Utilizar:

```text
resolved_by
resolved_at
reason
```

## Impacto nas ferramentas

### `create_quote`

Deverá criar a cotação com:

```text
status = draft
approved_by = null
approved_at = null
```

A ferramenta não poderá preencher dados de aprovação.

### `request_human_approval`

Deverá:

- criar a solicitação com `status = pending`;
- preencher `resolved_by` somente na resolução;
- preencher `resolved_at` somente na resolução;
- atualizar `quotesproved_by` e `quotes.approved_at` quando aprovada;
- atualizar `quotes.rejection_reason` quando rejeitada.

### `simulate_payment`

Deverá validar:

```text
approvals.status = approved
approvals.resolved_by IS NOT NULL
approvals.resolved_at IS NOT NULL
quotes.approved_by IS NOT NULL
quotes.approved_at IS NOT NULL
```

### `generate_document`

Não deverá aprovar ou resolver solicitações. Apenas utilizará a cotação
já aprovada e paga.

## Impacto na auditoria

Os eventos de aprovação deverão registrar:

```text
approval_id
quote_id
decision
resolved_by
resolved_at
reason
```

Eventos de aprovação positiva também poderão registrar:

```text
approved_by
approved_at
```

quando esses valores forem copiados para a cotação.

## Critérios para reconsiderar esta decisão

A decisão deverá ser revisada se o projeto passar a incluir:

- múltiplos aprovadores;
- aprovação em diferentes níveis;
- delegação de aprovação;
- substituição de aprovador;
- aprovação parcial;
- aprovação com condições;
- assinatura digital;
- integração com identidade corporativa;
- histórico de alterações na cotação após aprovação.

Esses cenários poderão exigir uma modelagem mais detalhada de workflow.

## Resultado esperado

O modelo deverá permitir distinguir claramente:

```textQuem resolveu a solicitação?
approvals.resolved_by
```

de:

```text
Quem aprovou a cotação?
quotes.approved_by
```

Para uma aprovação positiva:

```text
approvals.resolved_by → quotes.approved_by
approvals.resolved_at → quotes.approved_at
```

Para uma rejeição:

```text
approvals.resolved_by é preenchido
approvals.resolved_at é preenchido
quotes.rejection_reason é preenchido
quotes.approved_by permanece nulo
quotes.approved_at permanece nulo
```

Essa separação preserva a clareza semântica e a rastreabilidade do
processo de aprovação.