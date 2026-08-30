# ADR-002 — `silver_companies` como Fonte Canônica de Clientes

## Status

Aceita.

## Data

2026-08-26

## Contexto

O Nexum Sales Assistant precisa identificar e validar a empresa cliente
durante a criação de uma cotação.

A base de empresas é originalmente ingerida na camada Bronze e passa por
tratamento, tipagem e validação na camada Silver.

O projeto também possui uma camada Gold, destinada a modelos preparados
para consumo por ferramentas, agentes e análises. Isso gera uma decisão
sobre qual camada deve ser considerada a fonte oficial para validação da
identidade do cliente.

## Decisão

A tabela tratada:

```text
silver_companies
```

será a fonte canônica de clientes do MVP.

O campo utilizado como chave será:

```text
silver_companies.company_id
```

A tabela `quotes` deverá referenciar essa entidade por meio de:

```text
quotes.customer_id
```

Relacionamento:

```text
silver_companies.company_id
    └── quotes.customer_id
```

## Papel de cada camada

### Bronze

A Bronze preserva os dados de origem:

```text
bronze_companies
```

Responsabilidades:

- ingerir os dados originais;
- preservar os valores recebidos;
- registrar metadados de ingestão;
- permitir rastreabilidade até a origem;
- não servir como fonte direta para decisões comerciais.

### Silver

A Silver representa os dados tratados e validados:

```text
silver_companies
```

Responsabilidades:

- padronizar nomes e tipos;
- validar `company_id`;
- tratar valores nulos;
- remover ou sinalizar duplicidades;
- normalizar campos relevantes;
- disponibilizar uma entidade confiável para relacionamentos;
- servir como fonte canônica de clientes.

### Gold

A Gold representa modelos preparados para consumo:

```text
gold_quote_summary
gold_conversation_audit
```

Outras visões Gold poderão utilizar dados de empresas quando isso for
necessário para facilitar consultas ou análises.

A Gold não substitui a entidade canônica `silver_companies`.

## Justificativa

A `silver_companies` foi escolhida como fonte canônica porque:

- contém dados tratados;
- possui maior qualidade que a Bronze;
- preserva a entidade empresarial de forma estruturada;
- evita duplicar o cadastro de clientes;
- mantém os relacionamentos entre empresas e cotações simples;
- permite validar chaves antes da criação de uma cotação;
- segue a separação de responsabilidades entre Bronze, Silver e Gold.

A Gold será utilizada quando o objetivo for consumo simplificado,
agregação ou apresentação, mas não deverá criar uma segunda fonte de
verdade para a identidade dos clientes.

## Uso na criação de cotações

Antes de criar uma cotação, a ferramenta `create_quote` deverá validar:

```text
customer_id existe em silver_companies.company_id
```

Quando o cliente não existir, a cotação deverá ser rejeitada.

A ferramenta não deverá:

- criar uma empresa automaticamente;
- aceitar um cliente inexistente;
- inferir um `customer_id` a partir de texto livre;
- utilizar um nome de empresa como chave;
- substituir o cliente por um registro semelhante.

## Uso na geração de documentos

A ferramenta `generate_document` poderá consultar
`silver_companies` para obter informações da empresa cliente, como:

- nome;
- identificador;
- indústria;
- região;
- demais atributos necessários para a demonstração.

Esses dados deverão ser obtidos a partir de:

```text
quotes.customer_id
```

e não diretamente do texto da conversa.

## Golds relacionadas

A adoção de `silver_companies` como fonte canônica não impede a criação
de tabelas Gold.

As Golds previstas continuam válidas:

```text
gold_product_catalog
gold_product_availability
gold_quote_summary
gold_conversation_audit
```

### `gold_quote_summary`

Poderá combinar:

```text
silver_quotes
silver_quote_items
silver_companies
```

para disponibilizar uma visão resumida das cotações.

Essa Gold poderá conter:

```text
quote_id
customer_id
customer_name
status
total_amount
currency
created_at
approved_at
approved_by
payment_status
```

Mesmo quando `customer_name` estiver presente na Gold, a chave canônica
continuará sendo:

```text
silver_companies.company_id
```

## Alternativas consideradas

### Alternativa 1 — Usar `bronze_companies` diretamente

#### Motivos para não escolher

- a Bronze pode conter tipos inconsistentes;
- pode conter duplicidades;
- pode possuir valores nulos ou inválidos;
- mistura dados de origem com lógica de consumo;
- aumenta o risco de relacionamentos incorretos;
- viola a separação entre ingestão e dados tratados.

A Bronze permanecerá disponível para rastreabilidade, mas não será a
fonte de validação comercial.

### Alternativa 2 — Criar uma Gold exclusiva de clientes

Essa alternativa criaria uma tabela como:

```text
gold_customers
```

#### Motivos para não escolher no MVP

- adiciona uma entidade sem necessidade imediata;
- pode duplicar informações já tratadas Silver;
- cria risco de divergência entre `silver_companies` e `gold_customers`;
- aumenta a quantidade de dependências;
- não há necessidade de agregação específica para validar o cliente.

Uma Gold de clientes poderá ser criada no futuro se houver uma necessidade
concreta de consumo, como segmentação, enriquecimento ou integração com
um canal analítico.

### Alternativa 3 — Usar uma Gold operacional como fonte oficial

Essa alternativa faria a ferramenta consultar uma Gold diretamente para
validar clientes.

#### Motivos para não escolher

- a Gold pode mudar conforme as necessidades de consumo;
- uma visão analítica não deve necessariamente definir a identidade
  mestre da empresa;
- agregações ou filtros poderiam remover registros válidos;
- aumenta o acoplamento entre ferramentas e modelos de consumo.

A Gold poderá ser consultada pelas ferramentas quando apropriado, mas a
entidade de referência permanece na Silver.

### Alternativa 4 — Criar clientes durante a conversa

Essa alternativa permitiria que o agente criasse uma empresa quando não
encontrasse o cliente.

#### Motivos para não escolher

- o agente poderia inventar ou duplicar empresas;
- cria efeitos colaterais durante a conversa;
- não há fluxo de cadastro aprovado no MVP;
- dificulta a auditoria;
- aumenta o risco de dados comerciais inválidos.

O MVP utilizará somente empresas previamente cadastradas.

## Consequências positivas

- fonte canônica claramente definida;
- relacionamentos mais confiáveis;
- menor risco de duplicidade;
- separação clara entre Bronze, Silver e Gold;
- validação determinística de clientes;
- maior rastreabilidade;
- criação de cotação mais segura;
- possibilidade de criar Golds sem duplicar a entidade mestre.

## Consequências negativas

- a ferramenta dependerá da construção correta da Silver;
- dados presentes apenas na Bronze não estarão automaticamente
  disponíveis para criação de cotação;
- alterações no schema de `silver_companies` poderão afetar as ferramentas;
- será necessário validar chaves estrangeiras entre Silver;
- uma futura Gold operacional de clientes exigirá uma decisão adicional.

## Impacto no modelo de dados

A tabela `quotes` utilizará:

```text
customer_id STRING NOT NULL
```

Com referência lógica para:

```text
silver_companies.company_id
```

A referência não deverá ser substituída por:

```text
customer_name
company_name
```

nomes livres ou outros atributos não únicos.

## Impacto nas ferramentas

### `create_quote`

Deverá validar o cliente em:

```text
silver_companies
```

### `generate_document`

Poderá consultar:

```text
silver_companies
```

para enriquecer o documento simulado.

### `search_products`

Não depende diretamente de clientes.

### `check_inventory`

Não depende diretamente de clientes.

### `request_human_approval`

Utiliza a cotação já associada ao cliente validado.

### `simulate_payment`

Utiliza a cotação já aprovada e não deve criar ou alterar dados de
clientes.

## Impacto nas camadas de dados

### Bronze

```text
bronze_companies
```

Preserva a origem.

### Silver

```text
silver_companies
```

É a fonte canônica para relacionamentos de negócio.

### Gold

As tabelas Gold podem enriquecer ou agregar dados de clientes, mas não
substituem a chave canônica da Silver.

## Critérios para reconsiderar esta decisão

A criação de uma `gold_customers` ou de outra entidade canônica deverá
ser reconsiderada se houver:

- integração com múltiplos CRMs;
- necessidade de uma visão unificada de clientes;
- resolução de identidade entre fontes;
- histórico de mudanças empresariais;
- segmentações complexas;
- requisitos de consumo que não possam ser atendidos pela Silver;
 integração com sistemas externos;
- necessidade de dados mestres independentes do pipeline atual.

Mesmo nesses casos, a mudança deverá ser registrada em um novo ADR.

## Resultado esperado

O fluxo de criação de cotação deverá ser:

```text
customer_id recebido
       ↓
validação em silver_companies
       ↓
cliente validado
       ↓
consulta de produtos
       ↓
validação de estoque
       ↓
criação da cotação
```

A decisão garante que a identidade do cliente seja validada por dados
tratados, enquanto a Gold continua disponível para consumo otimizado
pelas ferramentas, análises e experiências do agente.