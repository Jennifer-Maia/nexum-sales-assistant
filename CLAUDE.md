# CLAUDE.md

Project guidance for AI agents lives in AGENTS.md.
Claude Code loads it via the import below.

@AGENTS.md
# Instruções para o Claude

## Contexto

Este é um projeto de portfólio de engenharia de dados chamado B2B Sales Intelligence, executado em Databricks Free Edition por meio de Declarative Automation Bundles.

## Regras obrigatórias

1. Leia `.llm/prd.md` antes de alterar o projeto.
2. Leia o prompt da etapa atual antes de executar mudanças.
3. Não executar etapas futuras sem aprovação.
4. Não usar Supabase, JDBC externo, Fivetran ou cloud externa.
5. Não inventar colunas que não existem na fonte sem documentar a derivação.
6. Não substituir um score heurístico por machine learning.
7. Preservar rastreabilidade da origem.
8. Não remover arquivos fora do escopo da etapa atual.
9. Usar nomes em snake_case nas tabelas finais.
10. Validar o bundle depois das alterações.
11. Criar testes para regras críticas.
12. Informar os arquivos alterados ao final de cada etapa.

## Processo de execução

Antes de modificar arquivos:

- explicar o plano;
- listar arquivos a criar, alterar e remover;
- identificar riscos;
- aguardar aprovação quando a tarefa solicitar revisão.

Depois de modificar arquivos:

- executar validações locais possíveis;
- verificar referências quebradas;
- informar comandos executados;
- resumir o resultado.