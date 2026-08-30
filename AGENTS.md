# Instruções para agentes — Nexum Sales Assistant

## 1. Contexto

Este repositório implementa o Nexum Sales Assistant, um MVP de vendas
B2B executado com Databricks e Declarative Automation Bundles.

O projeto ativo não é o antigo B2B Sales Intelligence. Não usar como
fonte de requisitos:

- score comercial;
- churn;
- dashboard;
- Genie Agent;
- funcionários;
- contatos recomendados;
- priorização de empresas.

As fontes atuais de verdade são:

```text
docs/discovery.md
docs/prd.md
docs/data_model.md
docs/specs/
docs/adrs/
```

## 2. Arquitetura funcional

O fluxo do MVP é:

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

O código deve controlar validações, cálculos, persistência e transições.
O LLM deve interpretar e comunicar resultados, sem inventar dados.

## 3. Entidades principais

O modelo deve contemplar:

```text
companies
products
inventory
quotes
quote_items
approvals
payments
documents
conversation_events
```

A fonte canônica de clientes é:

```text
silver_companies
```

A entidade comercial principal é:

```text
quotes
```

Não criar `orders` no MVP.

## 4. Camadas de dados

Respeitar a arquitetura:

```text
Bronze → Silver → Gold
```

Golds de consumo previstas:

```text
gold_product_catalog
gold_product_availability
gold_quote_summary
gold_conversation_audit
```

As ferramentas não devem consultar arquivos CSV diretamente quando
existir uma camada estruturada apropriada.

## 5. Regras de segurança e negócio

O agente não pode:

- inventar produtos, clientes ou preços;
- afirmar disponibilidade sem resultado de `check_inventory`;
- alterar estoque durante uma consulta;
- aplicar descontos não documentados;
- aprovar cotação em nome de uma pessoa;
- preencher aprovação humana fictícia;
- iniciar pagamento antes de aprovação válida;
- processar pagamento real;
- gerar documento fiscal;
- tratar documento simulado como documento oficial;
- ignorar erros de qualidade;
- substituir uma saída estruturada de ferramenta por texto inventado.

A aprovação humana é obrigatória antes de `simulate_payment`.

## 6. Documentação obrigatória

Antes de implementar uma ferramenta:

1. ler a SPEC correspondente;
2. ler os ADRs relacionados;
3. verificar o modelo em `docs/data_model.md`;
4. explicar o plano;
5. listar arquivos afetados;
6. definir testes;
7. solicitar revisão quando necessário.

## 7. Validações

Depois de qualquer alteração relevante:

```bash
git diff --check
git status --short
git diff
```

Conforme aplicável, executar também:

- testes unitários;
- testes de integração;
- validação de schema;
- consultas de qualidade;
- validação do bundle;
- inspeção dos resultados;
- verificação de auditoria;
- verificação das transições de `quotes`.

Uma tarefa não está concluída apenas porque o agente informou que o
código parece correto.

## 8. Alterações destrutivas

Não remover ou sobrescrever arquivos sem:

- listar previamente os arquivos afetados;
- explicar a motivação;
- verificar se pertencem ao projeto antigo;
- confirmar que não são necessários para restauração;
- obter aprovação quando houver risco de perda.

## 9. Convenções

- Python conforme configuração do projeto;
- SQL e Python com nomes em `snake_case`;
- documentação em Markdown;
- commits pequenos e descritivos;
- não ocultar erros de dados;
- manter alterações fáceis de revisar.

## 10. Conclusão de uma tarefa

Ao finalizar, informar:

- resumo da alteração;
- arquivos criados, alterados ou removidos;
- comandos executados;
- testes realizados;
- resultado das validações;
- limitações ou pendências.
