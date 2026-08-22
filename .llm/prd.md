# PRD — B2B Sales Intelligence

## 1. Visão do produto

O B2B Sales Intelligence é uma plataforma analítica para priorização comercial. A solução transforma dados de empresas e funcionários em oportunidades de recompra, contatos recomendados e ações comerciais explicáveis.

## 2. Problema de negócio

O time comercial possui muitas empresas e contatos, mas recursos limitados para realizar abordagens. É necessário identificar quais empresas apresentam maior comercial e quais funcionários devem ser contatados primeiro.

## 3. Objetivo do MVP

Construir uma pipeline Databricks em arquitetura medalhão:

- Bronze: ingestão dos CSVs;
- Silver: limpeza, padronização e relacionamento;
- Gold: oportunidades comerciais, contatos recomendados e score de prioridade.

## 4. Fonte de dados

Arquivos principais:

- `fixtures/companies_clean.csv`
- `fixtures/employees_clean.csv`

Arquivos previstos para evolução:

- `companies_noisy.csv`
- `employees_noisy.csv`
- `employees_with_company_sample.csv`

## 5. Volume conhecido

- 734 empresas;
- 5.234 funcionários;
- 733 empresas com funcionários;
- 1.451 funcionários classificados como decisores;
- 3.783 funcionários não decisores.

## 6. Chaves

- Empresas: `Company_ID`;
- Funcionários: `Employee_ID`;
- Relacionamento: `employees_clean.Company_ID = companies_clean.Company_ID`.

## 7. Camada Bronze

Criar:

- `bronze_companies`;
- `bronze_employees`.

A Bronze deve preservar os dados de origem e adicionar:

- `_ingestion_timestamp`;
- `_source_file`;
- `_source_system`.

## 8. Camada Silver

Criar tabelas padronizadas para:

- empresas;
- funcionários;
- relacionamento empresa-contato.

Regras:

- converter entidades HTML como `&` para `&`;
- converter datas para tipo `date`;
- converter métricas numéricas para tipos apropriados;
- remover duplicidades por chave;
- validar relacionamentos;
- manter rastreabilidade da origem.

## 9. Camada Gold

Criar:

- `gold_company_opportunities`;
- `gold_recommended_contacts`.

A tabela de oportunidades deverá conter dados da empresa, comportamento de compra, contrato, marketing, score e recomendação.

A tabela de contatos recomendados deverá priorizar funcionários decisores e com maior influência dentro de cada empresa.

## 10. Score

O MVP deverá usar um score heurístico e explicável, não um modelo estatístico de probabilidade.

O score poderá considerar:

- frequência de compra;
- dias desde a última compra;
- compras no último ano;
- status do contrato;
- leads gerados;
- taxa de conversão;
- existência de decisor;
- influência dos contatos;
- necessidade de follow-up.

Os pesos devem ser documentados e não podem ser inventados sem validação da distribuição dos dados.

## 11. Restrições técnicas

Não utilizar no MVP:

- Supabase como fonte de ingestão;
- JDBC externo;
- Fivetran;
- AWS;
- Azure;
- GCP;
- machine learning;
- dados pessoais reais;
- infraestrutura não necessária.

Ambiente:

- Databricks Free Edition;
- Declarative Automation Bundles;
- serverless compute;
- catalog `workspace`;
- targets `dev` e `prod`.

## 12. Critérios de aceite

O projeto será considerado funcional quando:

- o bundle passar no `databricks bundle validate`;
- a ingestão gerar 734 empresas;
- a ingestão gerar 5.234 funcionários;
- não houver chaves duplicadas;
- o relacionamento empresa-funcionário for validado;
- Bronze, Silver e Gold forem executáveis;
- as tabelas finais possuírem score e recomendação;
- o README explicar como reproduzir o projeto.