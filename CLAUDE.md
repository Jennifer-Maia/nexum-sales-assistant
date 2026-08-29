# CLAUDE.md

As instruções específicas para agentes estão em `AGENTS.md`.

@AGENTS.md

Leia também, conforme a tarefa:

- `docs/discovery.md`;
- `docs/prd.md`;
- `docs/data_model.md`;
- a SPEC correspondente em `docs/specs/`;
- os ADRs relevantes em `docs/adrs/`.

## Identidade do projeto

Este é o projeto **Nexum Sales Assistant**, um MVP de assistente de
vendas B2B executado sobre Databricks e Declarative Automation Bundles.

O fluxo principal é:

```text
busca de produto
    ↓
consulta de estoque
    ↓
criação de cotação
    ↓
aprovação humana
    ↓
pagamento simulado
    ↓
documento simulado
```

O projeto antigo de B2B Sales Intelligence, baseado em score, churn,
funcionários, contatos recomendados, dashboard e Genie Agent, não faz
parte do escopo ativo deste branch.

## Regras obrigatórias

1. Leia a documentação aplicável antes de alterar arquivos.
2. Use `docs/prd.md` e `docs/discovery.md` para o contexto do produto.
3. Use `docs/data_model.md` para entidades, campos e relacionamentos.
4. Use as SPECs como contrato das ferramentas.
5. Use os ADRs como registro das decisões arquiteturais.
6. Não executar etapas futuras sem aprovação quando a mudança afetar
   regras de negócio, estados, dados comerciais ou infraestrutura.
7. Não inventar produtos, clientes, preços, estoque, prazos, aprovações,
   pagamentos ou documentos.
8. Não substituir regras determinísticas por texto gerado pelo LLM.
9. Não remover a aprovação humana antes do pagamento simulado.
10. Não tratar dados sintéticos como dados reais.
11. Não processar pagamentos reais.
12. Não gerar documentos com validade fiscal.
13. Não criar uma entidade `orders` no MVP.
14. Usar `quotes` como entidade comercial principal.
15. Usar `silver_companies` como fonte canônica de clientes.
16. Manter rastreabilidade entre origem, transformação, ferramenta e
    auditoria.
17. Usar nomes em `snake_case` nas tabelas e campos finais.
18. Criar ou atualizar testes para regras críticas.
19. Validar o bundle e os arquivos afetados após as alterações.
20. Informar os arquivos alterados e as validações executadas ao final.

## Separação entre LLM e código

O princípio obrigatório é:

```text
LLM interpreta.
Código valida.
Código consulta.
Código calcula.
Código controla estados.
Humano aprova ações comerciais sensíveis.
```

O LLM pode interpretar mensagens, extrair requisitos, chamar ferramentas
e explicar resultados.

O LLM não pode decidir sozinho:

- qual produto existe;
- qual preço deve ser aplicado;
- quanto estoque está disponível;
- se uma cotação foi aprovada;
- se um pagamento ocorreu;
- se um documento possui validade;
- se uma transição de estado é permitida.

## Ferramentas do MVP

As ferramentas previstas são:

```text
search_products
check_inventory
create_quote
request_human_approval
simulate_payment
generate_document
```

Toda implementação deverá seguir a SPEC correspondente em
`docs/specs/`.

## Máquina de estados

Os estados permitidos para `quotes` são:

```text
draft
pending_approval
approved
rejected
paid
completed
```

Transições inválidas devem ser bloqueadas pelo código, não apenas
descritas na resposta textual do agente.

## Processo antes de alterar arquivos

Antes de modificar qualquer arquivo:

1. identificar a documentação aplicável;
2. explicar o plano;
3. listar arquivos a criar, alterar ou remover;
4. apontar riscos e dependências;
5. definir validações e testes;
6. solicitar revisão quando a mudança afetar regras sensíveis.

Não fazer alterações destrutivas sem autorização explícita.

## Processo depois de alterar arquivos

Executar, conforme aplicável:

```bash
git diff --check
git diff
```

Também verificar:

- referências quebradas;
- schemas;
- imports;
- testes;
- critérios de aceite;
- transições de estado;
- qualidade dos dados;
- configuração do bundle.

Informar ao final:

- arquivos alterados;
- arquivos removidos;
- comandos executados;
- resultado das validações;
- pendências conhecidas.
