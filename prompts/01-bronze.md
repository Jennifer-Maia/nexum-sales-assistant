# Etapa 01 — Dados sintéticos e ingestão Bronze

## Objetivo

Criar os dados sintéticos controlados do Nexum Sales Assistant e
implementar a camada Bronze, que deve ingerir os arquivos de origem
preservando os dados e adicionando metadados técnicos de
rastreabilidade.

A Bronze não aplica regras de negócio, não calcula compatibilidade ou
recomendação e não é consultada diretamente pelas ferramentas
comerciais (`docs/data_model.md` §5.1; `docs/agent_harness.md` §13).

## Documentos obrigatórios

Antes de alterar qualquer arquivo, leia:

- `AGENTS.md`;
- `CLAUDE.md`;
- `docs/prd.md`;
- `docs/data_model.md` (§5.1, §17);
- `docs/agent_harness.md` (§13, §14);
- `docs/adrs/ADR-002-silver-companies-como-fonte-de-cliente.md`;
- `docs/adrs/ADR-005-catalogo-pequeno-no-mvp.md`;
- `docs/specs/search_products.md`;
- `docs/specs/check_inventory.md`;
- `README.md`;
- `databricks.yml`;
- `resources/*.yml`.

Conforme `AGENTS.md`, leia também as skills Databricks aplicáveis
(`databricks-core` e a skill de produto correspondente), quando
disponíveis.

## Dados sintéticos

Antes da ingestão, criar os dados sintéticos conforme
`docs/data_model.md` §17 e
`docs/adrs/ADR-005-catalogo-pequeno-no-mvp.md`:

- catálogo pequeno cobrindo as categorias `temperature`, `pressure` e
  `vibration`;
- produtos ativos e inativos;
- casos compatíveis e incompatíveis por faixa, categoria e unidade;
- estoque no depósito padrão `WH-MAIN`, com casos de estoque
  suficiente, insuficiente, ausente e desatualizado (limite de 7 dias,
  conforme `docs/specs/check_inventory.md` §13);
- `currency = BRL`;
- os casos obrigatórios de demonstração listados no ADR-005.

Os dados devem ser identificados como sintéticos e de demonstração
(`docs/data_model.md` §17). Não apresentar dados sintéticos como
registros reais (`docs/agent_harness.md` §14).

## Dados de entrada

Os arquivos de origem devem ficar em `fixtures/` e ser publicados no
volume gerenciado `raw_data` do bundle, reutilizando o padrão já
existente em `resources/raw_data.volume.yml`.

Não fixar nomes de catalog ou schema no código. Não modificar os
arquivos de origem após a geração.

## Tabelas de saída

Implementar os datasets Bronze previstos em `docs/data_model.md` §5.1
que possuam arquivos de origem.

Observações:

- `bronze_companies` reutiliza a base de empresas existente, mantida
  como contexto de clientes B2B previamente cadastrados
  (`docs/discovery.md`; ADR-002);
- as entidades transacionais (`quotes`, `quote_items`, `approvals`,
  `payments`, `documents`, `conversation_events`) podem possuir dados
  semente sintéticos de demonstração (`docs/data_model.md` §17); a
  ingestão Bronze desses datasets segue `docs/data_model.md` §5.1
  quando existirem arquivos de origem correspondentes;
- a criação dessas entidades em tempo de execução pelas ferramentas
  pertence à etapa 04 (`04-tools.md`);
- qualquer conflito entre os documentos deve ser sinalizado antes de
  implementar (`docs/agent_harness.md` §4).

## Requisitos da ingestão

A implementação deve:

1. ler os arquivos de origem;
2. preservar as colunas de origem;
3. não aplicar regras de negócio nesta camada;
4. adicionar as colunas técnicas:
   - `_ingestion_timestamp`;
   - `_source_file`;
   - `_source_system`;
5. documentar se a leitura utiliza inferência de schema ou schema
   explícito;
6. não remover duplicidades nesta etapa;
7. não implementar Silver, Gold ou ferramentas.

## Implementação

Preferir a abordagem declarativa já utilizada pelo bundle:

- serverless compute;
- `catalog: ${var.catalog}` e `schema: ${var.schema}`;
- transformações em Python, um dataset por arquivo;
- caminho dos arquivos parametrizado (padrão `source_base_path`).

Não adicionar:

- machine learning;
- integrações externas;
- dependências desnecessárias.

## Arquivos permitidos

O agente pode propor alterações ou criações nos seguintes locais:

- `resources/*.yml`;
- `src/b2b_sales_intelligence_etl/`;
- `fixtures/` (novos dados sintéticos);
- `tests/`;
- `README.md`;
- `pyproject.toml`, somente se uma dependência for realmente necessária.

Não remover arquivos sem explicar o motivo.

## Regras de segurança

- Não modificar `docs/` sem aprovação.
- Não corrigir silenciosamente dados inconsistentes
  (`docs/agent_harness.md` §14).
- Não tratar dados sintéticos como dados reais.
- Não fazer deploy.
- Não fazer commit automaticamente.

## Processo obrigatório

Antes de modificar qualquer arquivo:

1. apresentar o plano dos dados sintéticos (entidades, volumes e casos
   de teste cobertos);
2. explicar a estratégia de disponibilização dos arquivos no workspace;
3. listar as tabelas Bronze que serão criadas e suas fontes;
4. listar arquivos a criar, alterar e remover;
5. explicar os riscos;
6. aguardar aprovação explícita.

Depois da aprovação:

1. implementar somente a camada Bronze e os dados sintéticos;
2. não implementar Silver;
3. não implementar Gold;
4. não implementar ferramentas;
5. não fazer deploy;
6. executar testes locais possíveis;
7. executar:

```bash
databricks bundle validate --profile <perfil>
```

8. mostrar o diff produzido;
9. informar os comandos que foram executados;
10. não fazer commit automaticamente.

## Critérios de aceite

A etapa estará concluída quando:

- os dados sintéticos cobrirem os casos exigidos por
  `docs/data_model.md` §17 e pelo ADR-005;
- as tabelas Bronze previstas tiverem sido definidas com as colunas
  técnicas de rastreabilidade;
- os dados de origem forem preservados;
- não houver lógica Silver, Gold ou de ferramentas;
- o bundle passar na validação;
- o README documentar a camada Bronze e a origem dos dados sintéticos.
