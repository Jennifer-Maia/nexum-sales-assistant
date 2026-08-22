# Etapa 00 — Setup do projeto

## Objetivo

Preparar o bundle Databricks para o projeto B2B Sales Intelligence, removendo os exemplos de táxi gerados pelo template e deixando a estrutura pronta para as etapas Bronze, Silver e Gold.

Esta etapa não deve implementar ainda a lógica de ingestão, transformação, score ou recomendação comercial.

## Documentos obrigatórios

Antes de alterar qualquer arquivo, leia:

- `AGENTS.md`
- `CLAUDE.md`
- `.llm/prd.md`
- `README.md`
- `databricks.yml`
- `resources/sample_job.job.yml`
- `resources/b2b_sales_intelligence_etl.pipeline.yml`
- `pyproject.toml`

## Escopo permitido

### Arquivos que podem ser removidos

Remover somente os arquivos de exemplo de táxi:

- `src/sample_notebook.ipynb`
- `src/b2b_sales_intelligence/taxis.py`
- `src/b2b_sales_intelligence_etl/transformations/sample_trips_b2b_sales_intelligence.py`
- `src/b2b_sales_intelligence_etl/transformations/sample_zones_b2b_sales_intelligence.py`
- `src/b2b_sales_intelligence_etl/explorations/sample_exploration.ipynb`
- `tests/sample_taxis_test.py`

Antes de remover qualquer arquivo, confirmar que ele pertence somente ao exemplo de táxi e que não é referenciado por outro recurso necessário.

### Arquivos que podem ser alterados

- `resources/sample_job.job.yml`
- `resources/b2b_sales_intelligence_etl.pipeline.yml`
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`, somente se houver instruções conflitantes ou incompletas

### Arquivos que podem ser criados

Somente arquivos necessários para:

- substituir referências quebradas aos exemplos de táxi;
- manter a estrutura mínima do bundle;
- documentar a nova organização.

Não criar ainda:

- lógica Bronze;
- lógica Silver;
- lógica Gold;
- score comercial;
- dashboard;
- notebooks de negócio;
- integrações externas.

## Job

Analisar o job atual em `resources/sample_job.job.yml`.

Remover as tarefas relacionadas ao exemplo de táxi, incluindo:

- `notebook_task`;
- `python_wheel_task`, caso ela não seja necessária para a execução futura da pipeline.

Manter somente a tarefa de atualização da pipeline se isso for compatível com a configuração atual.

Avaliar se o arquivo deve ser renomeado para:

```text
resources/b2b_sales_intelligence_job.yml
```

Se o arquivo for renomeado, atualizar todas as referências necessárias e explicar a mudança.

O job não deve executar automaticamente durante esta etapa.

Não habilitar notificações, schedules ou triggers adicionais.

## Pipeline

Manter a definição básica da pipeline em:

```text
resources/b2b_sales_intelligence_etl.pipeline.yml
```

Preservar:

- o uso de `${var.catalog}`;
- o uso de `${var.schema}`;
- serverless compute;
- a estrutura de recursos do bundle.

Remover referências às transformações de táxi.

Não implementar ainda as tabelas Bronze, Silver ou Gold.

Se a pipeline não puder ficar válida sem uma transformação, explicar o problema antes de criar um arquivo temporário.

## Configuração

Não alterar ainda os targets `dev` e `prod` em `databricks.yml`, salvo se houver uma referência quebrada diretamente causada pela limpeza do template.

Preservar:

```text
catalog dev: workspace
schema dev: dev
catalog prod: workspace
schema prod: prod
```

Não criar novo catalog, novo schema ou recurso externo nesta etapa.

## Dados

Preservar os arquivos:

```text
fixtures/companies_clean.csv
fixtures/employees_clean.csv
```

Não modificar conteúdo dos CSVs.

Não adicionar os arquivos noisy nesta etapa.

## Documentação

Atualizar o `README.md` para deixar claro que:

- o projeto é uma solução B2B Sales Intelligence;
- os exemplos de táxi foram removidos;
- Bronze, Silver e Gold serão implementadas nas próximas etapas;
- os dados principais estão em `fixtures/`;
- esta etapa é somente de preparação.

Não afirmar que Bronze, Silver ou Gold já estão funcionando.

## Regras de segurança

- Não apagar arquivos fora da lista autorizada.
- Não alterar os CSVs.
- Não adicionar dependências sem justificativa.
- Não usar Supabase, JDBC, Fivetran, AWS, Azure ou GCP.
- Não usar machine learning.
- Não fazer deploy.
- Não executar comandos destrutivos fora do escopo.
- Não modificar o histórico do Git.
- Não fazer commit automaticamente.

## Processo obrigatório

Antes de modificar qualquer arquivo:

1. apresentar um resumo do estado atual;
2. explicar como o job atual funciona;
3. explicar como a pipeline atual funciona;
4. listar os arquivos que serão removidos;
5. listar os arquivos que serão alterados;
6. listar os arquivos que serão criados;
7. explicar possíveis riscos;
8. aguardar aprovação explícita.

Depois da aprovação:

1. aplicar somente as mudanças aprovadas;
2. verificar referências quebradas;
3. executar testes locais possíveis;
4. executar:

```bash
databricks bundle validate --profile grid_intelligence
```

5. mostrar o resultado da validação;
6. resumir os arquivos alterados;
7. não fazer commit;
8. não fazer deploy.

## Critérios de aceite

A etapa estará concluída quando:

- os arquivos de táxi autorizados forem removidos;
- não existirem referências quebradas aos arquivos removidos;
- o job não depender mais do notebook de táxi;
- a pipeline não depender mais das transformações de táxi;
- os CSVs permanecerem intactos;
- o README refletir corretamente o estado do projeto;
- o bundle passar em:

```bash
databricks bundle validate --profile grid_intelligence
```

- nenhuma lógica de Bronze, Silver, Gold ou score tiver sido implementada prematuramente.