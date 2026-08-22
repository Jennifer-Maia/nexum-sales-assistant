# Etapa 01 — Ingestão Bronze

## Objetivo

Implementar a primeira camada da arquitetura medalhão do projeto B2B Sales Intelligence.

A camada Bronze deve ingerir os arquivos de empresas e funcionários preservando os dados de origem e adicionando metadados técnicos de rastreabilidade.

## Documentos obrigatórios

Antes de alterar qualquer arquivo, leia:

- `AGENTS.md`;
- `CLAUDE.md`;
- `.llm/prd.md`;
- `README.md`;
- `databricks.yml`;
- `resources/b2b_sales_intelligence_etl.pipeline.yml`;
- `prompts/01-bronze.md`;
- o conteúdo dos CSVs em `fixtures/`.

Conforme determinado em `AGENTS.md`, leia primeiro a skill `databricks-core`, caso ela esteja disponível.

## Dados de entrada

Arquivos:

```text
fixtures/companies_clean.csv
fixtures/employees_clean.csv
```

Entidades:

- empresas, identificadas por `Company_ID`;
- funcionários, identificados por `Employee_ID`;
- relacionamento por `Company_ID`.

Não modificar os arquivos CSV.

## Tabelas de saída

Criar as tabelas Bronze:

```text
bronze_companies
bronze_employees
```

As tabelas devem utilizar o catalog e schema definidos pelas variáveis do bundle:

```text
${var.catalog}
${var.schema}
```

Não fixar o nome do catalog ou schema no código.

## Requisitos da ingestão

A implementação deve:

1. ler os dois arquivos CSV;
2. preservar as colunas de origem;
3. evitar alterações de negócio nesta etapa;
4. adicionar as colunas técnicas:
   - `_ingestion_timestamp`;
   - `_source_file`;
   - `_source_system`;
5. permitir identificar qual arquivo originou cada registro;
6. usar tipos de leitura adequados;
7. documentar se a leitura utiliza inferência de schema ou schema explícito;
8. tratar corretamente o cabeçalho dos CSVs;
9. não remover duplicidades nesta etapa;
10. não aplicar regras de score;
11. não criar tabelas Silver ou Gold.

## Disponibilidade dos arquivos

Os CSVs estão localizados inicialmente no repositório local, mas a pipeline será executada no Databricks.

Antes de implementar a leitura, explique:

- qual caminho a pipeline usará durante a execução;
- como os arquivos locais serão disponibilizados no workspace;
- se o caminho é compatível com Databricks Free Edition;
- se será necessário alterar o bundle para publicar os arquivos;
- se será necessário executar um upload separado.

Não assumir que um caminho local do Windows estará disponível no Databricks.

Se a estratégia de disponibilização dos arquivos não estiver clara, não implementar uma solução frágil. Apresente as alternativas e aguarde aprovação.

## Implementação

Preferir a abordagem declarativa já utilizada pela pipeline existente, mantendo:

- serverless compute;
- `catalog: ${var.catalog}`;
- `schema: ${var.schema}`;
- estrutura de recursos do bundle;
- transformações em Python quando apropriado.

Não adicionar:

- Supabase;
- JDBC;
- Fivetran;
- AWS;
- Azure;
- GCP;
- machine learning;
- dependências externas desnecessárias.

## Arquivos permitidos

O agente pode propor alterações ou criações nos seguintes locais:

- `resources/b2b_sales_intelligence_etl.pipeline.yml`;
- `src/b2b_sales_intelligence_etl/`;
- `tests/`;
- `README.md`;
- `pyproject.toml`, somente se uma dependência for realmente necessária;
- `fixtures/`, somente para leitura, nunca para modificar os CSVs.

Não remover arquivos sem explicar o motivo.

## Processo obrigatório

Antes de modificar qualquer arquivo:

1. mostrar os nomes e colunas dos CSVs;
2. explicar a estratégia de disponibilização dos arquivos;
3. apresentar a arquitetura Bronze proposta;
4. listar arquivos a criar;
5. listar arquivos a alterar;
6. listar arquivos a remover, se houver;
7. explicar os riscos;
8. aguardar aprovação explícita.

Depois da aprovação:

1. implementar somente a camada Bronze;
2. não implementar Silver;
3. não implementar Gold;
4. não criar score;
5. não fazer deploy;
6. executar testes locais possíveis;
7. executar:

```bash
databricks bundle validate --profile grid_intelligence
```

8. mostrar o diff produzido;
9. informar os comandos que foram executados;
10. não fazer commit automaticamente.

## Critérios de aceite

A etapa Bronze estará concluída quando:

- a pipeline estiver configurada para ingerir os dois arquivos;
- as tabelas `bronze_companies` e `bronze_employees` estiverem definidas;
- as colunas técnicas estiverem presentes;
- os dados de origem forem preservados;
- os CSVs não forem alterados;
- não houver lógica Silver, Gold ou de score;
- o bundle passar na validação;
- o README documentar a camada Bronze;
- a estratégia de disponibilização dos arquivos estiver explicitamente documentada.