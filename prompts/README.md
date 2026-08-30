# Prompts de construção — Nexum Sales Assistant

Prompts versionados que orientam a implementação do Nexum Sales
Assistant, etapa por etapa.

A fonte de verdade do produto está em `docs/`. Cada prompt indica os
documentos obrigatórios e as SPECs e ADRs aplicáveis antes de qualquer
alteração de arquivo.

## Sequência de etapas

| Etapa | Arquivo | Entrega |
|---|---|---|
| 00 | `00-setup.md` | Migrar a estrutura do projeto e o bundle para o Nexum |
| 01 | `01-bronze.md` | Dados sintéticos e ingestão Bronze |
| 02 | `02-silver.md` | Padronização e validação na Silver |
| 03 | `03-gold.md` | Golds de consumo do agente |
| 04 | `04-tools.md` | As seis ferramentas do agente |
| 05 | `05-validation.md` | Testes, auditoria e critérios de aceite |

## Regras comuns

Cada etapa deverá:

1. ler os documentos obrigatórios listados no prompt;
2. explicar o plano antes de alterar arquivos;
3. listar arquivos a criar, alterar ou remover;
4. executar somente o escopo aprovado;
5. validar o bundle e os testes aplicáveis;
6. documentar as decisões;
7. não fazer deploy nem commit sem autorização explícita.
