# Etapa 03 — Camada Gold

## Objetivo

Implementar os modelos Gold de consumo do agente, derivados das
camadas tratadas, conforme `docs/data_model.md` §5.3 e §17.

As Golds facilitam consultas, mas não substituem as fontes detalhadas
da Silver. A fonte canônica de clientes continua sendo
`silver_companies` (ADR-002).

## Documentos obrigatórios

Antes de alterar qualquer arquivo, leia:

- `AGENTS.md`;
- `CLAUDE.md`;
- `docs/data_model.md` (§5.3, §17);
- `docs/agent_harness.md` (§13);
- `docs/adrs/ADR-002-silver-companies-como-fonte-de-cliente.md`;
- `docs/adrs/ADR-005-catalogo-pequeno-no-mvp.md`;
- `docs/specs/search_products.md` (§12, fonte de dados);
- `docs/specs/check_inventory.md` (§5, fonte de dados);
- `README.md`.

## Tabelas de saída

Criar exatamente as quatro Golds previstas:

```text
gold_product_catalog
gold_product_availability
gold_quote_summary
gold_conversation_audit
```

Não criar Golds adicionais sem decisão registrada em ADR
(`docs/data_model.md` §14; ADR-002).

### `gold_product_catalog`

Campos conforme `docs/data_model.md` §17. Será consumida por
`search_products` (`docs/specs/search_products.md` §12).

### `gold_product_availability`

Combina catálogo e estoque; campos conforme `docs/data_model.md` §17,
incluindo `is_available` e `inventory_updated_at`. Será consumida por
`check_inventory` (`docs/specs/check_inventory.md` §5).

### `gold_quote_summary`

Visão resumida das cotações; campos conforme `docs/data_model.md` §17.
Poderá combinar `silver_quotes`, `silver_quote_items` e
`silver_companies` (ADR-002), mantendo a chave canônica em
`silver_companies.company_id`.

### `gold_conversation_audit`

Visão de auditoria da conversa e das ferramentas; campos conforme
`docs/data_model.md` §17.

## Regras

- As Golds devem ser derivadas das camadas Silver, nunca de arquivos
  CSV consultados diretamente (`docs/agent_harness.md` §13; ADR-005).
- A Gold não substitui a fonte canônica de clientes (ADR-002).
- Não corrigir silenciosamente dados inconsistentes.

## Regras de segurança

- Não criar Golds além das quatro previstas.
- Não alterar `docs/` sem aprovação.
- Não fazer deploy nem commit automaticamente.

## Processo obrigatório

Antes de modificar qualquer arquivo:

1. apresentar o mapeamento de cada Gold para suas fontes Silver;
2. listar os campos de cada Gold conforme `docs/data_model.md` §17;
3. listar arquivos a criar, alterar e remover;
4. explicar riscos;
5. aguardar aprovação explícita.

Depois da aprovação:

1. implementar somente a camada Gold;
2. não implementar ferramentas;
3. não fazer deploy;
4. executar testes locais possíveis;
5. executar:

```bash
databricks bundle validate --profile <perfil>
```

6. mostrar o diff produzido;
7. informar os comandos que foram executados;
8. não fazer commit automaticamente.

## Critérios de aceite

A etapa estará concluída quando:

- as quatro Golds previstas estiverem implementadas com os campos de
  `docs/data_model.md` §17;
- cada Gold for derivada da Silver correspondente;
- `gold_product_catalog` e `gold_product_availability` atenderem aos
  contratos das SPECs `search_products` e `check_inventory`;
- não houver implementação de ferramentas nesta etapa;
- o bundle passar na validação;
- o README documentar a camada Gold.
