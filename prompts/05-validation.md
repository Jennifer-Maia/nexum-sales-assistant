# Etapa 05 — Validação e critérios de aceite

## Objetivo

Validar o Nexum Sales Assistant de ponta a ponta: testes das
ferramentas, qualidade de dados, transições de estado, auditoria e
critérios de aceite das SPECs.

Uma tarefa não está concluída apenas porque o agente informou que o
código parece correto (`docs/agent_harness.md` §18).

## Documentos obrigatórios

Antes de alterar qualquer arquivo, leia:

- `AGENTS.md`;
- `CLAUDE.md`;
- `docs/prd.md` (§17, critérios de aceite);
- `docs/data_model.md` (§15, §17);
- `docs/agent_harness.md` (§18–§20);
- `docs/adrs/ADR-004-llm-interpreta-codigo-decide.md`;
- `docs/adrs/ADR-005-catalogo-pequeno-no-mvp.md` (critérios de
  qualidade e casos obrigatórios);
- as SPECs em `docs/specs/`;
- `README.md`.

## O que validar

### Testes das ferramentas

- critérios de aceite de cada SPEC (`CA01` em diante), incluindo casos
  de erro, limite e bloqueio;
- reprodutibilidade das ferramentas determinísticas (ADR-004).

### Transições de estado

- todas as transições permitidas de `quotes` (`docs/data_model.md` §8);
- bloqueio das transições inválidas.

### Qualidade de dados

- chaves e integridade (`docs/data_model.md` §15);
- os critérios de qualidade do ADR-005;
- consultas de contagem e nulidade sobre Bronze, Silver e Gold.

### Auditoria

- eventos em `conversation_events` para busca, estoque, cotação,
  aprovação, pagamento e documento (`docs/data_model.md` §13);
- rastreabilidade entre ferramenta, entrada, resultado e registro
  (`docs/agent_harness.md` §20).

### Jornada completa

Executar os casos obrigatórios de demonstração do ADR-005:

- busca com resultados;
- busca sem resultados;
- produto inativo não retornado;
- estoque suficiente, insuficiente e ausente;
- cotação criada em estado `draft`;
- aprovação humana antes do pagamento;
- pagamento simulado somente após aprovação;
- documento simulado somente após pagamento simulado.

## Validações obrigatórias

```bash
git diff --check
uv run pytest
uv run ruff check .
databricks bundle validate --profile <perfil>
```

Conforme aplicável, executar também a pipeline e inspecionar os
resultados das Golds e da auditoria (`docs/agent_harness.md` §18).

## Regras de segurança

- Não usar pagamentos reais nem documentos fiscais em nenhum teste.
- Não criar dados de aprovação fictícios em nome de um aprovador.
- Não alterar `docs/` sem aprovação.
- Não fazer deploy nem commit automaticamente.

## Processo obrigatório

Antes de modificar qualquer arquivo:

1. apresentar o plano de testes e validações;
2. listar os critérios de aceite que serão cobertos;
3. listar arquivos a criar, alterar e remover;
4. explicar riscos;
5. aguardar aprovação explícita.

Depois da aprovação:

1. criar ou atualizar os testes;
2. executar as validações listadas;
3. registrar os resultados reais, incluindo falhas;
4. mostrar o diff produzido;
5. não fazer commit automaticamente.

## Critérios de aceite

A etapa estará concluída quando:

- os testes das ferramentas cobrirem os critérios de aceite das SPECs;
- as transições válidas e inválidas de `quotes` possuírem testes;
- as consultas de qualidade forem executadas sem ocultar erros;
- a auditoria da jornada estiver verificada;
- a jornada completa do Nexum puder ser demonstrada de ponta a ponta;
- o README refletir o estado final validado.
