# Etapa 00 — Setup do projeto Nexum

## Objetivo

Migrar a estrutura do repositório e o bundle Databricks do produto
anterior para o Nexum Sales Assistant.

Esta etapa prepara o terreno para as etapas seguintes (Bronze, Silver,
Gold, ferramentas e validação). Ela não deve implementar lógica de
negócio do Nexum.

## Documentos obrigatórios

Antes de alterar qualquer arquivo, leia:

- `AGENTS.md`;
- `CLAUDE.md`;
- `docs/discovery.md`;
- `docs/prd.md`;
- `docs/data_model.md`;
- `docs/agent_harness.md`;
- `docs/adrs/ADR-004-llm-interpreta-codigo-decide.md`;
- `docs/adrs/ADR-005-catalogo-pequeno-no-mvp.md`;
- `docs/specs/` (contratos das ferramentas; contexto das próximas etapas);
- `README.md`;
- `databricks.yml`;
- `resources/*.yml`;
- `pyproject.toml`.

## Contexto

O repositório está em migração. A documentação em `docs/` já define o
Nexum Sales Assistant; `README.md`, `CLAUDE.md` e `AGENTS.md` já foram
migrados. O código em `src/` e os recursos em `resources/` ainda
refletem o produto anterior e devem ser substituídos.

O fluxo do Nexum é:

```text
search_products
    ↓
check_inventory
    ↓
create_quote
    ↓
request_human_approval
    ↓
simulate_payment
    ↓
generate_document
```

## Arquivos que podem ser removidos

Apresentar a lista completa antes de remover, com justificativa e
confirmação de que cada item pertence ao produto anterior
(`AGENTS.md` §8). Candidatos:

- as transformações legadas da Bronze do produto anterior em
  `src/b2b_sales_intelligence_etl/transformations/`;
- os CSVs legados em `fixtures/` (não versionados, conforme
  `.gitignore`; serão substituídos pelos dados sintéticos do Nexum na
  etapa 01);
- `src/image_gen_output.png`, se não for referenciado por nenhum
  documento ativo;
- demais artefatos legados identificados durante a análise, com
  aprovação explícita para cada um.

Antes de remover qualquer arquivo, verificar que ele não é referenciado
por outro recurso necessário.

## Arquivos que podem ser alterados

- `resources/*.yml`, para remover referências legadas;
- `src/b2b_sales_intelligence/main.py`, para alinhar o entry point ao
  Nexum;
- `src/b2b_sales_intelligence_etl/README.md`, para descrever a nova
  organização;
- `README.md`, somente se a estrutura descrita mudar;
- `pyproject.toml`, somente se uma dependência for realmente necessária.

## Arquivos que podem ser criados

Somente arquivos necessários para:

- manter a estrutura mínima do bundle válida;
- documentar a nova organização.

Não criar ainda:

- lógica Bronze, Silver ou Gold do Nexum;
- ferramentas do agente;
- tabelas ou Golds;
- integrações externas.

## Bundle e pipeline

Preservar:

- `catalog` e `schema` como variáveis (`${var.catalog}`,
  `${var.schema}`);
- targets `dev` e `prod` em `databricks.yml`;
- serverless compute;
- o padrão de volume gerenciado para os dados de entrada, se ele for
  reutilizável para os dados sintéticos do Nexum.

Não renomear o bundle nem os targets nesta etapa, salvo aprovação
explícita com lista de impactos.

Remover as referências às transformações legadas. Se a pipeline não
puder ficar válida sem uma transformação, explicar o problema antes de
criar um arquivo temporário.

O job não deve executar automaticamente durante esta etapa. Não
habilitar notificações, schedules ou triggers adicionais.

## Configuração

Não criar novo catalog, novo schema ou recurso externo nesta etapa.

## Dados

Não criar os dados sintéticos do Nexum nesta etapa; eles pertencem à
etapa 01 (`01-bronze.md`), conforme `docs/data_model.md` §17 e
`docs/adrs/ADR-005-catalogo-pequeno-no-mvp.md`.

Não modificar os CSVs legados antes da aprovação de remoção.

## Documentação

Ao final, garantir que:

- o README descreva corretamente o estado atual do projeto;
- a estrutura de `src/` esteja documentada;
- nenhuma documentação ativa cite artefatos removidos.

## Regras de segurança

- Não apagar arquivos fora da lista autorizada.
- Não alterar `docs/` sem aprovação.
- Não adicionar dependências sem justificativa.
- Não usar machine learning.
- Não fazer deploy.
- Não executar comandos destrutivos fora do escopo.
- Não modificar o histórico do Git.
- Não fazer commit automaticamente.

## Processo obrigatório

Antes de modificar qualquer arquivo:

1. apresentar um resumo do estado atual;
2. listar os artefatos legados identificados;
3. listar os arquivos que serão removidos, alterados e criados;
4. explicar possíveis riscos;
5. aguardar aprovação explícita.

Depois da aprovação:

1. aplicar somente as mudanças aprovadas;
2. verificar referências quebradas;
3. executar testes locais possíveis;
4. executar:

```bash
databricks bundle validate --profile <perfil>
```

5. mostrar o resultado da validação;
6. resumir os arquivos alterados;
7. não fazer commit;
8. não fazer deploy.

## Critérios de aceite

A etapa estará concluída quando:

- os artefatos legados aprovados tiverem sido removidos;
- não existirem referências quebradas aos arquivos removidos;
- a pipeline e o job não dependerem mais do código legado;
- o bundle passar em:

```bash
databricks bundle validate --profile <perfil>
```

- nenhuma lógica de Bronze, Silver, Gold ou ferramenta do Nexum tiver
  sido implementada prematuramente;
- a estrutura estiver pronta para a etapa 01.
