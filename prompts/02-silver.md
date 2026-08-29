# Etapa 02 — Camada Silver

## Objetivo

Implementar a camada Silver do Nexum Sales Assistant: padronizar nomes,
converter tipos, tratar valores inválidos, validar chaves e garantir
consistência entre entidades, preparando os dados para as ferramentas
do agente (`docs/data_model.md` §5.2).

## Documentos obrigatórios

Antes de alterar qualquer arquivo, leia:

- `AGENTS.md`;
- `CLAUDE.md`;
- `docs/data_model.md` (§5.2, §6–§15);
- `docs/agent_harness.md` (§13);
- `docs/adrs/ADR-002-silver-companies-como-fonte-de-cliente.md`;
- `docs/adrs/ADR-005-catalogo-pequeno-no-mvp.md` (critérios de
  qualidade);
- `docs/specs/create_quote.md` (validação de cliente e produtos);
- `docs/specs/generate_document.md` (consulta à `silver_companies`);
- `README.md`.

## Tabelas de saída

Implementar os datasets Silver previstos em `docs/data_model.md` §5.2
para as entidades com origem Bronze nesta etapa. Os datasets das
entidades transacionais seguem o mesmo tratamento quando existirem na
Bronze, conforme a etapa 01.

## Fonte canônica de clientes

`silver_companies` é a fonte canônica de clientes do MVP (ADR-002).

Garantir:

- `company_id` validado e sem duplicidades;
- tipos padronizados;
- a tabela pronta para os relacionamentos previstos:

```text
silver_companies.company_id
    └── quotes.customer_id
```

A Silver de empresas não deve servir como fonte de dados comerciais de
produto, estoque ou preço.

## Regras de tratamento

Conforme `docs/data_model.md` e o ADR-005:

- unicidade de `product_id` e de `sku`;
- categoria válida (`temperature`, `pressure` ou `vibration`);
- unidade compatível com a categoria;
- faixa operacional consistente
  (`min_operating_value <= max_operating_value`);
- preço maior que zero;
- `currency = BRL`;
- prazo maior ou igual a zero;
- estado `active` válido;
- quantidades de estoque não negativas;
- produto relacionado ao estoque existente;
- ausência de duplicidade de produto e depósito;
- timestamps válidos.

Dados inválidos devem ser sinalizados pela camada de qualidade, não
corrigidos silenciosamente (`docs/agent_harness.md` §14; ADR-005).

## Regras de segurança

- Não criar entidades não previstas em `docs/data_model.md`.
- Não criar a entidade `orders` no MVP (ADR-001).
- Não alterar `docs/` sem aprovação.
- Não fazer deploy nem commit automaticamente.

## Processo obrigatório

Antes de modificar qualquer arquivo:

1. listar os datasets Silver e suas fontes Bronze;
2. apresentar as regras de qualidade e os casos de teste;
3. listar arquivos a criar, alterar e remover;
4. explicar riscos;
5. aguardar aprovação explícita.

Depois da aprovação:

1. implementar somente a camada Silver;
2. não implementar Gold;
3. não implementar ferramentas;
4. não fazer deploy;
5. executar testes locais possíveis;
6. executar:

```bash
databricks bundle validate --profile <perfil>
```

7. mostrar o diff produzido;
8. informar os comandos que foram executados;
9. não fazer commit automaticamente.

## Critérios de aceite

A etapa estará concluída quando:

- os datasets Silver previstos estiverem implementados;
- `silver_companies` estiver validada como fonte canônica de clientes
  (ADR-002);
- as regras de qualidade do ADR-005 forem aplicadas sem correção
  silenciosa;
- não houver lógica Gold ou de ferramentas;
- o bundle passar na validação;
- o README documentar a camada Silver.
