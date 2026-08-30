# Agent Harness Engineering — Nexum Sales Assistant

## 1. Objetivo

Este documento define como ferramentas de desenvolvimento orientadas por
agentes serão utilizadas no projeto Nexum Sales Assistant.

O objetivo não é delegar a construção inteira do sistema ao agente, mas
utilizar agentes como copilotos para acelerar tarefas de engenharia,
mantendo revisão, responsabilidade e entendimento humano sobre as
decisões importantes.

O harness deverá preservar a rastreabilidade entre:

```text
necessidade de negócio
        ↓
discovery.md
        ↓
prd.md
        ↓
data_model.md
        ↓
SPECs
        ↓
ADRs
        ↓
código
        ↓
testes e validações
```

## 2. Ferramentas utilizadas

O projeto poderá utilizar:

- Claude Code;
- AI Dev Kit;
- Git;
- Databricks Asset Bundles;
- PySpark;
- SQL;
- Markdown para documentação técnica;
- ferramentas de teste e validação disponíveis no repositório.

A disponibilidade de uma ferramenta não elimina a necessidade de revisão
humana.

## 3. Papel do harness

O harness será utilizado para:

- explorar a estrutura do repositório;
- ler e revisar documentos;
- sugerir implementações;
- explicar APIs e erros;
- gerar rascunhos de documentação;
- propor testes;
- revisar código;
- auxiliar no troubleshooting;
- identificar inconsistências entre PRD, modelo, SPECs, ADRs e código;
- verificar schemas;
- executar comandos de leitura e validação autorizados;
- comparar implementação com critérios de aceite;
- apoiar a construção das camadas Bronze, Silver e Gold.

O harness não é a fonte de verdade do produto. As decisões de negócio e
arquitetura continuam sob responsabilidade humana.

## 4. Fontes de contexto

Ao analisar ou modificar o projeto, o agente deverá considerar os
seguintes documentos:

1. `docs/discovery.md`;
2. `docs/prd.md`;
3. `docs/data_model.md`;
4. `docs/specs/`;
5. `docs/adrs/`;
6. código-fonte;
7. README e demais documentos auxiliares.

### Precedência

Quando houver conflito:

- regras de negócio devem ser comparadas com `discovery.md` e `prd.md`;
- estrutura de dados deve ser comparada com `data_model.md`;
- comportamento de ferramentas deve ser comparado com as SPECs;
- decisões arquiteturais devem ser comparadas com os ADRs;
- código divergente não deve ser corrigido silenciosamente.

O agente deverá identificar o conflito, explicar o impacto e solicitar
uma decisão antes de alterar uma regra estabelecida.

## 5. Responsabilidade humana

A responsável pelo projeto mantém a decisão final sobre:

- problema de negócio;
- escopo do MVP;
- modelo de dados;
- regras de compatibilidade;
- regras de preço;
- regras de estoque;
- transições de estado;
- aprovação humana;
- arquitetura;
- critérios de aceite;
- permissões;
- alterações de infraestrutura;
- interpretação dos resultados;
- aprovação de alterações no código;
- entrada ou saída de funcionalidades do escopo.

O agente não deve transformar uma sugestão em decisão de produto sem
revisão humana.

## 6. O que o agente pode automatizar

O agente pode:

- criar rascunhos de arquivos;
- sugerir alterações em código;
- explicar trechos de PySpark ou SQL;
- sugerir consultas;
- criar testes unitários e de integração como rascunho;
- revisar nomes, tipos e padrões;
- apontar possíveis erros;
- executar comandos de leitura e validação autorizados;
- auxiliar na documentação;
- propor refatorações;
- revisar consistência entre documentos e código;
- gerar dados sintéticos conforme regras aprovadas;
- criar consultas de qualidade;
- verificar transições de estado;
- comparar resultados com critérios de aceite;
- preparar mudanças pequenas e revisáveis.

Toda alteração gerada deve ser revisada antes de ser incorporada.

## 7. O que o agente não pode decidir sozinho

O agente não pode decidir sozinho:

- alterar o objetivo do produto;
- aumentar o escopo do MVP;
- remover a aprovação humana;
- criar uma entidade comercial não prevista;
- criar a tabela `orders` no MVP;
- alterar a máquina de estados;
- modificar preços;
- aplicar descontos;
- alterar estoque;
- reservar estoque;
- aprovar uma cotação em seu próprio nome;
- registrar uma aprovação humana inexistente;
- tratar pagamento simulado como pagamento real;
- gerar documento com validade fiscal;
- tratar dados sintéticos como dados reais;
- ignorar falhas de qualidade;
- substituir regras determinísticas por texto gerado;
- inventar produtos, clientes, estoque, preços ou prazos;
- apagar dados ou arquivos relevantes;
- alterar a infraestrutura de produção sem revisão;
- alterar as Golds consumidas pelo agente sem revisão;
- conectar o projeto a sistemas financeiros ou fiscais reais.

## 8. Separação entre LLM e código

O princípio do projeto é:

```text
LLM interpreta.
Código valida.
Código consulta.
Código calcula.
Código decide.
Humano aprova ações comerciais sensíveis.
```

### O LLM pode

- interpretar mensagens;
- extrair requisitos;
- identificar informações ausentes;
- solicitar ferramentas;
- explicar resultados;
- apresentar dados retornados;
- indicar a próxima etapa permitida;
- encaminhar para atendimento humano.

### O código e as ferramentas devem

- validar entradas;
- consultar dados estruturados;
- filtrar produtos;
- verificar estoque;
- calcular preços;
- congelar valores de cotação;
- controlar estados;
- registrar aprovações;
- simular pagamentos;
- gerar documentos simulados;
- registrar auditoria;
- bloquear transições inválidas.

O LLM não poderá substituir a saída estruturada de uma ferramenta por
uma afirmação própria.

## 9. Contratos das ferramentas

As ferramentas do MVP são:

```text
search_products
check_inventory
create_quote
request_human_approval
simulate_payment
generate_document
```

Cada ferramenta deverá possuir uma SPEC correspondente em:

```text
docs/specs/
```

A SPEC é o contrato funcional da ferramenta e deverá definir:

- objetivo;
- responsabilidade;
- campos de entrada;
- tipos;
- campos obrigatórios;
- validações;
- regras de negócio;
- fonte de dados;
- formato da saída;
- códigos de erro;
- efeitos permitidos;
- efeitos proibidos;
- auditoria;
- critérios de aceite;
- dependências;
- fora do escopo.

Uma implementação não deverá ser considerada correta apenas porque
funciona em um caso feliz. Ela deverá atender também aos casos de erro,
limite e bloqueio descritos na SPEC.

## 10. Ferramentas e responsabilidades

### `search_products`

Responsável por:

- interpretar requisitos estruturados recebidos;
- consultar `gold_product_catalog`;
- retornar produtos compatíveis;
- excluir produtos inativos;
- ordenar resultados deterministicamente;
- registrar a consulta.

Não deverá:

- criar produtos;
- confirmar estoque;
- congelar preços;
- criar cotação;
- prometer prazo de entrega.

### `check_inventory`

Responsável por:

- consultar `gold_product_availability`;
- comparar disponibilidade com quantidade solicitada;
- informar dados desatualizados;
- registrar a consulta.

Não deverá:

- reservar estoque;
- reduzir estoque;
- aumentar estoque;
- alterar `available_quantity`;
- alterar `reserved_quantity`.

### `create_quote`

Responsável por:

- validar o cliente em `silver_companies`;
- validar produtos e estoque;
- consultar preços confiáveis;
- congelar preços nos itens;
- calcular subtotais e total;
- criar cotação em estado `draft`;
- registrar auditoria.

Não deverá:

- aprovar a cotação;
- reservar estoque;
- aplicar desconto não aprovado;
- iniciar pagamento.

### `request_human_approval`

Responsável por:

- solicitar aprovação;
- registrar a decisão humana;
- controlar a transição para `approved` ou `rejected`;
- preencher `resolved_by` e `resolved_at`;
- copiar os dados de aprovação para a cotação quando aprovada;
- registrar auditoria.

Não deverá:

- aprovar em nome do agente;
- alterar preços;
- alterar estoque;
- iniciar pagamento.

### `simulate_payment`

Responsável por:

- validar a aprovação humana;
- registrar pagamento exclusivamente simulado;
- atualizar o status de pagamento;
- mover a cotação para `paid` somente em caso de sucesso;
- registrar auditoria.

Não deverá:

- processar dinheiro real;
- receber dados financeiros reais;
- alterar o valor aprovado;
- executar antes da aprovação humana.

### `generate_document`

Responsável por:

- validar pagamento simulado bem-sucedido;
- gerar documento simulado;
- manter o aviso de ausência de validade;
- mover a cotação de `paid` para `completed`;
- registrar auditoria.

Não deverá:

- emitir nota fiscal;
- gerar documento fiscal;
- declarar pagamento real;
- omitir o aviso de simulação.

## 11. Máquina de estados de `quotes`

A entidade comercial do MVP é:

```text
quotes
```

Não haverá uma entidade `orders` no MVP.

Estados permitidos:

```text
draft
pending_approval
approved
rejected
paid
completed
```

Fluxo válido:

```text
draft
  ↓
pending_approval
  ├── approved
  │     ↓
  │    paid
  │     ↓
  │  completed
  │
  └── rejected
```

Transições permitidas:

```text
draft → pending_approval
pending_approval → approved
pending_approval → rejected
approved → paid
paid → completed
```

Transições proibidas incluem:

```text
draft → approved
draft → paid
draft → completed
pending_approval → paid
pending_approval → completed
rejected → approved
rejected → paid
completed → draft
completed → paid
```

Qualquer alteração na máquina de estados exige:

1. revisão da SPEC afetada;
2. revisão de `data_model.md`;
3. avaliação de impacto nos ADRs;
4. testes de transição;
5. aprovação humana.

## 12. Aprovação humana

A aprovação humana é obrigatória antes do pagamento simulado.

Uma aprovação válida deverá possuir:

```text
approvals.status = approved
approvals.resolved_by IS NOT NULL
approvals.resolved_at IS NOT NULL
```

A cotação aprovada deverá possuir:

```text
quotes.status = approved
quotes.approved_by IS NOT NULL
quotes.approved_at IS NOT NULL
```

O agente não pode preencher esses campos como se fosse um aprovador
humano.

Uma execução de `simulate_payment` somente poderá ocorrer depois de uma
aprovação válida e de uma autorização explícita para executar a etapa
simulada.

## 13. Camadas de dados

O agente deverá respeitar a separação entre as camadas.

### Bronze

Responsável por preservar dados de origem:

```text
bronze_companies
bronze_products
bronze_inventory
bronze_quotes
bronze_quote_items
```

A Bronze não deverá ser consultada diretamente pelas ferramentas
comerciais.

### Silver

Responsável por dados tratados, tipados e validados:

```text
silver_companies
silver_products
silver_inventory
silver_quotes
silver_quote_items
silver_approvals
silver_payments
silver_documents
silver_conversation_events
```

A `silver_companies` é a fonte canônica de clientes do MVP.

### Gold

Responsável por modelos preparados para consumo:

```text
gold_product_catalog
gold_product_availability
gold_quote_summary
gold_conversation_audit
```

As ferramentas deverão utilizar as Golds apropriadas para consumo,
enquanto os relacionamentos canônicos e dados tratados permanecerão
nas camadas definidas em `data_model.md`.

As Golds não deverão ser construídas diretamente de arquivos CSV quando
já existir uma camada Silver correspondente.

## 14. Dados sintéticos

Os dados de catálogo, estoque, empresas, cotações, pagamentos e
documentos serão sintéticos e deverão ser identificados como dados de
demonstração.

O agente não deverá apresentar dados sintéticos como registros reais
de uma empresa real.

Os dados sintéticos deverão ser:

- pequenos;
- controlados;
- reproduzíveis;
- rastreáveis;
- suficientes para cobrir casos positivos e negativos;
- compatíveis com `data_model.md`;
- compatíveis com as SPECs;
- adequados para demonstrar as Golds.

O catálogo deverá incluir situações como:

- produto compatível;
- produto incompatível;
- produto inativo;
- estoque suficiente;
- estoque insuficiente;
- estoque ausente;
- estoque desatualizado;
- preço válido;
- dados inválidos para teste de qualidade.

## 15. Regras contra invenção

O agente e o LLM não deverão inventar:

- produtos;
- SKUs;
- especificações;
- categorias;
- clientes;
- preços;
- moedas;
- prazos;
- quantidade disponível;
- aprovações;
- pagamentos;
- documentos;
- valores calculados;
- resultados de consultas;
- dados de auditoria.

Quando os dados não forem suficientes, o sistema deverá:

- informar a ausência;
- retornar erro estruturado;
- solicitar informação válida;
- encaminhar para revisão humana quando necessário.

A ausência de dados não deverá ser convertida silenciosamente em uma
afirmação comercial.

## 16. Processo antes de implementar

Antes de implementar uma funcionalidade, o agente deverá:

1. localizar a documentação relacionada;
2. identificar a SPEC ou ADR aplicável;
3. explicar a mudança proposta;
4. listar os arquivos afetados;
5. identificar dependências;
6. apontar riscos;
7. sugerir testes;
8. verificar possíveis impactos no modelo de dados;
9. aguardar revisão quando a mudança afetar regras de negócio, estados,
   preços, estoque, permissões ou dados comerciais.

Para alterações pequenas de documentação ou comandos de validação, o
agente poderá prosseguir conforme a autorização recebida.

## 17. Revisão humana obrigatória

A revisão humana é obrigatória para alterações em:

- modelo de dados;
- Bronze, Silver ou Gold;
- regras de compatibilidade;
- preço;
- estoque;
- fluxo de cotação;
- máquina de estados;
- aprovação;
- pagamento;
- geração de documentos;
- permissões;
- configuração de produção;
- pipelines;
- tabelas Gold consumidas pelo agente;
- contratos das ferramentas;
- critérios de aceite;
- ADRs aceitos.

## 18. Validações

Nenhuma alteração deverá ser considerada concluída apenas porque o
agente informou que o código está correto.

As validações deverão incluir, conforme aplicável:

- leitura dos arquivos modificados;
- validação de Markdown;
- validação de sintaxe;
- validação de schema;
- testes unitários;
- testes de integração;
- consultas de qualidade;
- verificação de chaves;
- verificação de nulos;
- verificação de duplicidades;
- verificação de tipos;
- execução em ambiente de desenvolvimento;
- inspeção dos resultados;
- comparação com critérios de aceite;
- verificação de auditoria;
- verificação de transições de estado;
- verificação de que dados proibidos não foram alterados.

## 19. Checklist de conclusão

Uma tarefa só deverá ser considerada concluída quando:

- a documentação relacionada foi localizada;
- a implementação segue a SPEC aplicável;
- os ADRs não foram violados;
- o modelo de dados continua consistente;
- os testes relevantes foram executados;
- os casos de erro foram avaliados;
- os critérios de aceite foram verificados;
- não existem dados inventados;
- não houve alteração indevida de estoque;
- não houve aprovação automática;
- não houve pagamento real;
- documentos simulados estão claramente identificados;
- eventos de auditoria foram considerados;
- os arquivos alterados foram revisados;
- o `git diff` foi inspecionado.

Comandos mínimos recomendados:

```bash
git status --short
git diff --check
git diff
```

## 20. Auditoria e rastreabilidade

As ferramentas deverão registrar eventos em:

```text
conversation_events
```

O agente deverá verificar se as operações relevantes possuem:

- `session_id`;
- nome da ferramenta;
- tipo do evento;
- referência do registro;
- resultado;
- data e hora;
- erro, quando aplicável.

Os eventos deverão permitir rastrear:

```text
qual ferramenta foi chamada
com quais dados
qual resultado foi retornado
qual registro foi criado ou consultado
qual transição ocorreu
se houve aprovação humana
```

## 21. Alterações de documentação

Quando uma alteração modificar comportamento, o agente deverá verificar
se também precisa atualizar:

- `docs/data_model.md`;
- uma ou mais SPECs;
- um ADR existente;
- `docs/prd.md`;
- testes;
- código;
- dados sintéticos;
- consultas de qualidade;
- documentação do harness.

Não deverá existir alteração de código que contradiga silenciosamente a
documentação aprovada.

## 22. Critério de sucesso do harness

O uso do harness será considerado bem-sucedido quando:

- acelerar tarefas sem esconder decisões;
- produzir alterações revisáveis;
- manter rastreabilidade entre documentação e código;
- reduzir erros repetitivos;
- gerar testes e validações úteis;
- preservar a responsabilidade humana sobre o produto;
- proteger regras comerciais sensíveis;
- impedir invenção de dados;
- tornar falhas visíveis;
- deixar claro o que foi automatizado e o que foi revisado manualmente.

## 23. Evolução futura

A configuração de hooks, permissões, automações de CI/CD e outras
integrações será detalhada conforme as necessidades do projeto forem
surgindo.

Novas regras do harness deverão ser documentadas quando houver:

- novas ferramentas;
- novas camadas de dados;
- integração externa;
- mudanças de autorização;
- ações transacionais reais;
- novos riscos operacionais;
- necessidade de validações automatizadas adicionais.

Este documento deverá ser atualizado quando o fluxo de desenvolvimento
for amadurecido.