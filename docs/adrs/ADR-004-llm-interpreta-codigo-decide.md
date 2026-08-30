# ADR-004 — LLM Interpreta, Código Decide

## Status

Aceita.

## Data

2026-08-26

## Contexto

O Nexum Sales Assistant utiliza um modelo de linguagem para conversar
com clientes, entender necessidades e conduzir o fluxo comercial.

O modelo de linguagem é adequado para:

- interpretar linguagem natural;
- identificar requisitos técnicos;
- esclarecer informações faltantes;
- explicar resultados;
- conduzir a conversa;
- indicar a próxima etapa do fluxo.

Entretanto, o modelo de linguagem não deve ser a autoridade final para
decisões que envolvam dados comerciais, estados transacionais ou ações
sensíveis.

Essas decisões precisam ser:

- reproduzíveis;
- auditáveis;
- baseadas em dados estruturados;
- protegidas contra invenção;
- independentes da variação textual da resposta do modelo.

## Decisão

O LLM será responsável pela interpretação e pela comunicação.

As ferramentas determinísticas, as tabelas estruturadas e as regras de
negócio serão responsáveis pelas decisões.

Princípio central:

```text
LLM interpreta.
Código valida.
Código consulta.
Código calcula.
Código decide.
Humano aprova ações comerciais sensíveis.
```

## Responsabilidades do LLM

O LLM poderá:

- interpretar a mensagem do cliente;
- extrair requisitos técnicos;
- identificar categoria de produto;
- identificar faixas de medição;
- identificar unidade informada;
- identificar quantidade desejada;
- identificar caso de uso;
- solicitar informações ausentes;
- escolher qual ferramenta chamar;
- explicar os resultados retornados;
- apresentar alternativas encontradas;
- informar quando uma etapa exige aprovação humana;
- encaminhar o cliente para um vendedor.

O LLM deverá utilizar somente os resultados retornados pelas ferramentas
para fazer afirmações factuais sobre produtos, estoque, preços, prazos,
cotações e pagamentos.

## Responsabilidades do código

O código e as ferramentas determinísticas serão responsáveis por:

- validar entradas;
- consultar o catálogo;
- filtrar produtos compatíveis;
- consultar disponibilidade;
- calcular preços;
- congelar preços na cotação;
- calcular subtotais;
- calcular totais;
- validar o cliente;
- controlar estados da cotação;
- registrar aprovações;
- exigir aprovação humana;
- simular pagamentos;
- gerar documentos simulados;
- registrar eventos de auditoria;
- impedir transições inválidas;
- impedir dados inventados.

## Responsabilidade humana

A aprovação humana será obrigatória antes de:

```text
approved → paid
```

O agente não poderá aprovar uma cotação em seu próprio nome.

O usuário humano será responsável por:

- revisar a cotação;
- confirmar condições comerciais;
- aprovar ou rejeitar a cotação;
- fornecer justificativa quando necessário;
- revisar inconsistências;
- decidir quando encaminhar o cliente para atendimento manual.

## Fluxo de interação

O fluxo conceitual será:

```text
Mensagem do cliente
        ↓
LLM interpreta a necessidade
        ↓
LLM produz requisitos estruturados
        ↓
Ferramenta valida os requisitos
        ↓
Ferramenta consulta dados confiáveis
        ↓
Ferramenta retorna resultado estruturado
        ↓
LLM explica o resultado
        ↓
Ação sensível exige aprovação humana
```

## Exemplo: busca de produto

### Mensagem

```text
Preciso monitorar 20 máquinas entre 0 °C e 150 °C.
```

### Interpretação do LLM

O LLM poderá produzir:

```json
{
  "category": "temperature",
  "min_required_value": 0,
  "max_required_value": 150,
  "measurement_unit": "C",
  "quantity": 20
}
```

### Decisão da ferramenta

A ferramenta `search_products` deverá:

- validar a categoria;
- validar a faixa;
- consultar `gold_product_catalog`;
- filtrar produtos compatíveis;
- retornar somente produtos existentes;
- ordenar os resultados deterministicamente.

O LLM não poderá criar um produto caso a ferramenta não encontre
resultados.

## Exemplo: estoque

O LLM poderá solicitar:

```text
Verifique se há 20 unidades do produto PRD-TEMP-001.
```

A ferramenta `check_inventory` deverá:

- consultar `gold_product_availability`;
- comparar `available_quantity` com `quantity_requested`;
- informar o resultado;
- registrar a consulta;
- não alterar o estoque.

O LLM não poderá afirmar que há estoque sem receber esse resultado
da ferramenta.

## Exemplo: preço

O LLM poderá apresentar o preço retornado pela busca ou pela criação
da cotação.

Entretanto:

```text
o LLM não calcula o preço final;
o LLM não escolhe um desconto;
o LLM não altera o preço unitário;
o LLM não confirma uma condição comercial não registrada.
```

A ferramenta `create_quote` deverá:

- consultar o preço estruturado;
- congelar o valor em `quote_items.unit_price`;
- calcular o subtotal;
- calcular o total;
- persistir os valores;
- retornar a cotação criada.

## Exemplo: aprovação

O LLM poderá informar:

```text
A cotação foi encaminhada para aprovação humana.
```

O LLM não poderá informar:

```text
Sua cotação foi aprovada.
```

sem que exista uma resolução humana registrada com:

```text
approvals.status = approved
approvals.resolved_by IS NOT NULL
approvals.resolved_at IS NOT NULL
```

A ferramenta `request_human_approval` será responsável pela transição:

```text
pending_approval → approved
```

ou:

```text
pending_approval → rejected
```

## Exemplo: pagamento

O LLM poderá iniciar uma solicitação de pagamento simulado após receber
o resultado da aprovação.

A ferramenta `simulate_payment` deverá validar:

```text
quotes.status = approved
approvals.status = approved
```

O LLM não poderá:

- marcar uma cotação como paga;
- criar um pagamento diretamente;
- informar que houve pagamento real;
- alterar o valor do pagamento;
- receber dados de cartão ou credenciais financeiras.

## Exemplo: documento

O LLM poderá informar que um documento simulado foi gerado somente após
receber a resposta de `generate_document`.

O documento deverá possuir:

```text
document_type = simulated_receipt
has_fiscal_value = false
```

O LLM deverá deixar claro que o documento:

```text
não possui validade fiscal, financeira ou contábil.
```

## Ferramentas determinísticas

O MVP utilizará as seguintes ferramentas:

```text
search_products
check_inventory
create_quote
request_human_approval
simulate_payment
generate_document
```

### `search_products`

Decide quais produtos atendem aos requisitos técnicos estruturados.

### `check_inventory`

Decide se a quantidade disponível atende à quantidade solicitada.

### `create_quote`

Decide os valores calculados da cotação com base no catálogo confiável.

### `request_human_approval`

Registra e aplica a decisão humana sobre a cotação.

### `simulate_payment`

Registra um resultado de pagamento exclusivamente simulado.

### `generate_document`

Gera um documento simulado somente após pagamento simulado bem-sucedido.

## Fonte de dados

As ferramentas deverão utilizar tabelas estruturadas:

```text
silver_companies
gold_product_catalog
gold_product_availability
quotes
quote_items
approvals
payments
documents
conversation_events
```

O LLM não deverá consultar diretamente:

- arquivos CSV;
- dados brutos da Bronze;
- mensagens históricas como fonte oficial de preço;
- informações não retornadas pelas ferramentas;
- conteúdo inventado ou não validado.

## Contratos de entrada e saída

Cada ferramenta deverá possuir contrato documentado em uma SPEC.

O contrato deverá definir:

- campos de entrada;
- tipos;
- campos obrigatórios;
- validações;
- de negócio;
- estados permitidos;
- formato de saída;
- códigos de erro;
- critérios de aceite;
- eventos de auditoria.

O LLM deverá chamar as ferramentas respeitando esses contratos.

Uma resposta textual do LLM não poderá substituir a saída estruturada
de uma ferramenta.

## Regras contra alucinação

O LLM não deverá:

- inventar produtos;
- inventar SKUs;
- inventar especificações;
- inventar estoque;
- inventar preços;
- inventar prazos;
- inventar clientes;
- inventar aprovações;
- inventar pagamentos;
- inventar documentos;
- apresentar dados sintéticos como dados reais;
- esconder ausência de informação;
- transformar estimativa em garantia;
- tratar documento simulado como nota fiscal.

Quando os dados não forem suficientes, o LLM deverá informar a limitação
ou encaminhar para atendimento humano.

## Regras de linguagem

O LLM deverá distinguir claramente:

```text
referência de catálogo
```

de:

```text
valor congelado em cotação
```

Também deverá distinguir:

```text
consulta de estoque
```

de:

```text
reserva de estoque
```

E:

```text
pagamento simulado
```

de:

```text
pagamento real
```

E:

```text
documento simulado
```

de:

```text
documento fiscal
```

## Falhas das ferramentas

Quando uma ferramenta retornar erro, o LLM deverá:

- preservar o significado do erro;
- não inventar uma resposta alternativa;
- explicar a limitação em linguagem;
- informar a próxima etapa permitida;
- encaminhar para atendimento humano quando necessário;
- registrar ou manter o evento de erro para auditoria.

O LLM não deverá transformar:

```text
inventory_not_found
```

:

```text
available = false
```

sem que essa regra esteja definida pelo contrato da ferramenta.

Também não deverá transformar:

```text
no_compatible_product
```

em recomendação de produto incompatível.

## Auditoria

Cada execução de ferramenta deverá gerar evento em:

```text
conversation_events
```

O evento deverá permitir rastrear:

- sessão;
- ferramenta;
- entrada normalizada;
- resultado;
- referência do registro criado ou consultado;
- data e hora;
- ocorrência de erro;
- encaminhamento humano.

A auditoria deverá permitir responder:

```text
Qual ferramenta foi chamada?
Com quais requisitos?
Qual dado foi retornado?
Qual decisão foi tomada?
Houve aprovação humana?
Qual registro foi criado?
```

## Segurança

O LLM não poderá executar diretamente ações que alterem dados
comerciais sensíveis sem passar pelas ferramentas correspondentes.

Ações sensíveis incluem:

- criar cotação;
- alterar estado da cotação;
- registrar aprovação;
- registrar pagamento simulado;
- gerar documento;
- alterar preço;
- alterar estoque;
- alterar cliente.

No MVP, as ferramentas de consulta não deverão alterar dados:

```text
search_products
check_inventory
```

Ações de alteração deverão validar estado e permissões:

```text
request_human_approval
simulate_payment
generate_document
```

## Alternativas consideradas

### Alternativa 1 — Permitir que o LLM decida diretamente

Essa alternativa permitiria ao LLM- escolher preços;
- afirmar disponibilidade;
- aprovar cotações;
- calcular totais;
- alterar estados;
- criar pagamentos;
- gerar documentos.

#### Motivos para não escolher

- resultados não seriam determinísticos;
- aumentaria o risco de alucinação;
- dificultaria auditoria;
- regras poderiam mudar conforme a formulação da mensagem;
- ações comerciais ficariam sem controle;
- erros seriam difíceis de reproduzir;
- não haveria separação clara entre interpretação e execução.

### Alternativa 2 — Não utilizar LLM

Essa alternativa implementaria toda a interação com regras fixas e
interfaces estruturadas.

#### Motivos para não escolher no MVP

- reduziria a capacidade de conversar em linguagem natural;
- dificultaria a extração de requisitos;
- tornaria a experiência menos flexível;
- perderia o principal componente demonstrativo do assistente;
- exigiria que o cliente conhecesse comandos rígidos.

### Alternativa 3 — Permitir que o LLM decida, mas validar depois

Essa alternativa deixaria o LLM produzir uma decisão final e aplicaria
validações posteriores.

#### Motivos para não escolher

- a decisão já poderia carregar uma interpretação incorreta;
- validações posteriores poderiam não capturar todas as ambiguidades;
- aumenta a responsabilidade do modelo em ações sensíveis;
- dificulta identificar a origem de uma decisão;
- permite que texto livre substitua contratos estruturados.

## Consequências positivas

- decisões reproduzíveis;
- menor risco de alucinação;
- regras comerciais centralizadas;
- auditoria clara;
- testes determinísticos;
- separação de responsabilidades;
- maior facilidade de troubleshooting;
- possibilidade de substituir o LLM sem reescrever as regras de negócio;
- melhor controle de ações sensíveis.

## Consequências negativas

- maior quantidade de contratos e ferramentas;
- necessidade de manter SPECs atualizadas;
- maior complexidade de orquestração;
- algumas interações exigirão encaminhamento humano;
- o LLM poderá parecer menos autônomo;
- mudanças de negócio exigirão atualização de código e documentação.

## Impacto nas SPECs

As SPECs deverão continuar separando:

```text
interpretação da mensagem
```

de:

```text
execução da regra de negócio
```

O LLM poderá produzir os requisitos estruturados utilizados por
`search_products`, mas a ferramenta não deverá interpretar livremente
um texto como substituto desses campos.

## Impacto no harness

O `agent_harness.md` deverá orientar o agente de desenvolvimento a:

- preservar as regras determinísticas;
- não mover lógica comercial para prompts sem justificativa;
- criar testes para as ferramentas;
- verificar contratos de entrada e saída;
- identificar alterações que afetem estados;
- exigir revisão humana para ações sensíveis;
- manter rastreabilidade entre SPEC, e testes.

## Critérios para reconsiderar esta decisão

A decisão deverá ser revisada se houver:

- necessidade de regras probabilísticas;
- uso de modelos preditivos;
- recomendações baseadas em aprendizado de máquina;
- aumento da autonomia do agente;
- integração com sistemas transacionais reais;
- novos requisitos de autorização;
- necessidade de execução autônoma com controles adicionais;
- mudança no nível de risco das ações realizadas.

Mesmo nesses casos, decisões financeiras, fiscais e comerciais deverão
continuar sujeitas a validação apropriada.

## Resultado esperado

O Nexum Sales Assistant deverá seguir o princípio:

```text
A conversa pode ser flexível.
A decisão comercial deve ser controlada.
```

O LLM interpreta a intenção do cliente e coordena a conversa.

As ferramentas determinísticas consultam os dados, aplicam as regras,
calculam os valores e controlam as transições.

A aprovação humana permanece obrigatória antes do avanço comercial
sensível.