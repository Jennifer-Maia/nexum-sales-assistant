# ADR-005 — Catálogo Pequeno e Controlado no MVP

## Status

Aceita.

## Data

2026-08-26

## Contexto

O Nexum Sales Assistant precisa demonstrar uma jornada completa de
vendas B2B:

```text
necessidade do cliente
    ↓
busca de produto
    ↓
consulta de estoque
    ↓
criação de cotação
    ↓
aprovação humana
    ↓
pagamento simulado
    ↓
documento simulado
```

Para validar essa jornada, o sistema precisa de dados de catálogo,
estoque, empresas, cotações e eventos de conversa.

No entanto, o objetivo do MVP não é representar um catálogo industrial
completo. O objetivo é demonstrar:

- qualidade da engenharia de dados;
- busca determinística;
- compatibilidade técnica;
- separação entre catálogo e estoque;
- criação de cotação;
- aprovação humana;
- pagamento simulado;
- auditoria;
- uso controlado de LLM.

Um catálogo excessivamente grande aumentaria a complexidade dos dados
sem necessariamente melhorar a demonstração.

## Decisão

O MVP utilizará um catálogo pequeno, controlado e representativo,
composto por produtos sintéticos.

O catálogo deverá cobrir as categorias técnicas necessárias para validar
as ferramentas:

```text
temperature
pressure
vibration
```

A quantidade de produtos deverá ser suficiente para demonstrar:

- produtos compatíveis;
- produtos incompatíveis;
- produtos ativos;
- produtos inativos;
- diferentes faixas operacionais;
- diferentes preços;
- diferentes prazos;
- diferentes situações de estoque;
- ausência de estoque;
- estoque insuficiente;
- dados potencialmente desatualizados.

Os dados serão explicitamente identificados como sintéticos e destinados
à demonstração.

## Escopo do catálogo

O catálogo deverá conter produtos com:

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

Os dados deverão permitir testar as regras de
`search_products`.

## Características mínimas

O conjunto de produtos deverá incluir, no mínimo, exemplos de:

### Produto compatível

Produto ativo que cobre integralmente a faixa solicitada.

### Produto incompatível por faixa

Produto ativo da mesma categoria, mas que não cobre a faixa solicitada.

### Produto incompatível por categoria

Produto ativo com especificações válidas, mas pertencente a outra
categoria.

### Produto inativo

Produto que possui dados completos, mas não pode ser retornado.

### Produto com unidade incompatível

Produto cuja unidade não corresponde à unidade solicitada.

### Produto com dados inválidos

Produto com preço, prazo ou especificação inconsistente para testar
validações de qualidade.

## Exemplos de categorias

### Temperature

Deverá permitir testar faixas como:

```text
0 °C a 150 °C
```

Exemplos de produtos:

```text
PRD-TEMP-001
PRD-TEMP-002
PRD-TEMP-003
```

### Pressure

Deverá permitir testar faixas de pressão com unidade explicitamente
registrada.

Exemplos:

```text
PRD-PRES-001
PRD-PRES-002
```

### Vibration

Deverá permitir testar produtos voltados ao monitoramento de vibração
em máquinas industriais.

Exemplos:

```text
PRD-VIB-001
PRD-VIB-002
```

Os valores exatos serão definidos nos dados sintéticos, não neste ADR.

## Dados de estoque

Cada produto relevante deverá possuir registros de estoque que permitam
testar:

```text
available
insufficient_stock
inventory_not_found
stale_inventory
```

O estoque deverá utilizar ao menos um depósito padrão:

```text
WH-MAIN
```

Os dados deverão conter:

```text
product_id
warehouse_id
available_quantity
reserved_quantity
inventory_updated_at
```

A consulta de estoque não deverá modificar os dados.

## Dados comerciais

Os produtos deverão possuir preços e prazos sintéticos para permitir:

- cálculo de subtotal;
- cálculo de total;
- ordenação determinística;
- congelamento do preço na cotação;
- comparação entre produtos;
- demonstração de alteração futura no catálogo sem alterar
  cotação já criada.

Todos os preços deverão utilizar:

```text
currency = BRL
```

O catálogo não deverá simular descontos complexos no MVP.

## Justificativa

Um catálogo pequeno foi escolhido porque:

- reduz o tempo de preparação dos dados;
- facilita a inspeção manual;
- torna os testes determinísticos;
- permite cobrir casos positivos e negativos;
- reduz o risco de inconsistências;
- facilita a demonstração;
- permite reproduzir os resultados;
- mantém o foco na arquitetura e no fluxo;
- evita criar complexidade sem valor para o MVP.

A qualidade do caso demonstrado é mais importante que a quantidade de
produtos.

## Representatividade

O catálogo pequeno não deverá ser tratado como uma amostra estatística
do mercado industrial.

Ele servirá para representar comportamentos necessários ao sistema:

```text
compatibilidade
incompatibilidade
disponibilidade
indisponibilidade
preço
prazo
estado ativo
estado inativo
```

Os dados não deverão ser apresentados como dados reais de uma empresa
real.

## Alternativas consideradas

### Alternativa 1 — Utilizar um catálogo industrial real

#### Motivos para não escolher

- pode envolver dados confidenciais;
- pode exigir autorização de uso;
- aumenta riscos de privacidade e segurança;
- pode conter regras comerciais não documentadas;
- dificulta a reprodução da demonstração;
- pode introduzir dependência externa;
- pode gerar expectativa de integração real.

O MVP utilizará dados sintéticos controlados.

### Alternativa 2 — Gerar milhares de produtos sintéticos

#### Motivos para não escolher

- aumenta o volume sem necessariamente aumentar a cobertura;
- dificulta a inspeção manual;
- torna os testes menos transparentes;
- aumenta o custo de processamento;
- dificulta explicar por que um produto foi retornado;
- pode esconder problemas de qualidade.

O volume será aumentado somente quando houver necessidade comprovada.

### Alternativa 3 — Utilizar apenas um produto por categoria

#### Motivos para não escolher

- não permite demonstrar ordenação;
- não permite comparar compatibilidade;
- reduz a cobertura de casos negativos;
- dificulta testar limite de resultados;
- não representa cenários de escolha.

Cada categoria deverá possuir produtos suficientes para testar diferentes
resultados.

### Alternativa 4 — Consultar fornecedores externos

#### Motivos para não escolher

- adiciona dependências externas;
- pode gerar resultados instáveis;
- dificulta auditoria;
- pode introduzir preços e disponibilidade não controlados;
- não é necessário para o objetivo do MVP.

O catálogo será local e estruturado.

## Consequências positivas

- dados reproduzíveis;
- menor complexidade;
- maior controle sobre os cenários;
- testes mais fáceis;
- demonstração mais clara;
- menor custo de processamento;
- facilidade para simular falhas;
- facilidade para revisar manualmente os resultados;
- menor risco de expor dados reais.

## Consequências negativas

- o catálogo não representa a variedade real do mercado;
- resultados não devem ser generalizados;
- algumas situações comerciais ficarão fora do MVP;
- o desempenho em grande escala não será validado;
- será necessário ampliar os dados em uma etapa futura;
- o agente poderá parecer mais preciso em um domínio pequeno e
  controlado do que em um catálogo real.

## Critérios de qualidade dos dados

Antes de os dados chegarem à Gold, deverão ser verificadas:

- unicidade de `product_id`;
- unicidade de `sku`;
- categoria válida;
- unidade compatível com a categoria;
- faixa operacional consistente;
- preço maior que zero;
- moeda válida;
- prazo maior ou igual a zero;
- estado `active` válido;
- quantidade de estoque não negativa;
- existência de produto relacionado ao estoque;
- ausência de duplicidade de produto e depósito;
- validade de timestamps.

Dados inválidos deverão ser sinalizados pela camada de qualidade.

A pipeline não deverá corrigir silenciosamente dados comerciais
inconsistentes.

## Casos obrigatórios de demonstração

A demonstração deverá incluir pelo menos os seguintes casos:

### Busca com resultados

Uma necessidade válida retorna produtos compatíveis.

### Busca sem resultados

Uma necessidade válida não encontra produto que cubra a faixa
solicitada.

### Produto inativo

Um produto inativo não aparece na resposta.

### Estoque suficiente

A quantidade disponível atende à quantidade solicitada.

### Estoque insuficiente

A quantidade disponível não atende à quantidade solicitada.

### Estoque ausente

A disponibilidade não pode ser confirmada por falta de registro.

### Cotação válida

Um cliente, produtos e estoque válidos permitem criar uma cotação
em estado `draft`.

### Aprovação humana

A cotação passa por `pending_approval` antes de ser aprovada.

### Pagamento simulado

Somente a cotação aprovada pode receber pagamento simulado.

### Documento simulado

Somente um pagamento simulado bem-sucedido permite gerar o documento.

## Impacto nas camadas de dados

### Bronze

Receberá os dados sintéticos de origem:

```text
bronze_companies
bronze_products
bronze_inventory
bronze_quotes
bronze_quote_items
```

### Silver

Tratará e validará:

```text
silver_companies
silver_products
silver_inventory
silver_quotes
silver_quote_items
```

### Gold

Disponibilizará modelos preparados para consumo:

```text
gold_product_catalog
gold_product_availability
gold_quote_summary
gold_conversation_audit
```

As Golds deverão ser derivadas das camadas tratadas e não de arquivos
CSV consultados diretamente pelas ferramentas.

## Impacto nas ferramentas

### `search_products`

Consultará:

```text
gold_product_catalog
```

### `check_inventory`

Consultará:

```text
gold_product_availability
```

### `create_quote`

Utilizará:

```text
silver_companies
gold_product_catalog
gold_product_availability
```

### `request_human_approval`

Utilizará os dados da cotação e da aprovação persistidos.

### `simulate_payment`

Utilizará a cotação aprovada e os dados de aprovação.

### `generate_document`

Utilizará a cotação, os itens, o cliente, o pagamento simulado e os
dados estruturados dos produtos.

## Critérios para ampliar o catálogo

O catálogo poderá ser ampliado quando:

- uma nova categoria entrar no escopo;
- uma nova regra de compatibilidade for adicionada;
- houver necessidade de testar um caso de borda;
- os testes existentes não cobrirem uma regra;
- o fluxo precisar representar outro cenário comercial;
- o volume atual impedir uma validação relevante;
- houver necessidade de demonstrar performance.

A expansão deverá preservar:

- dados sintéticos;
- rastreabilidade;
- qualidade;
- reprodutibilidade;
- documentação das novas categorias e regras.

## Critérios para reconsiderar esta decisão

A estratégia de catálogo controlado deverá ser revisada quando houver:

- necessidade de validar performance em grande escala;
- integração com catálogo real;
- múltiplos fornecedores;
- regras comerciais por cliente;
- preços por volume;
- múltiplas moedas;
- contratos comerciais;
- substituição de produtos;
- disponibilidade em múltiplos depósitos;
- atualizações frequentes;
- exigência de testes de carga;
- operação em ambiente produtivo.

Uma futura migração para dados reais deverá ser registrada em novo ADR.

## Resultado esperado

O MVP deverá possuir um conjunto pequeno de dados capaz de demonstrar
de forma clara:

```text
dados sintéticos
    ↓
Bronze
    ↓
Silver validada
    ↓
Gold de consumo
    ↓
busca determinística
    ↓
estoque
    ↓
cotação
    ↓
aprovação humana
    ↓
pagamento simulado
    ↓
documento simulado
```

O catálogo não precisa ser grande para validar a arquitetura.

Ele precisa ser:

```text
consistente
controlado
representativo
auditável
reproduzível
```