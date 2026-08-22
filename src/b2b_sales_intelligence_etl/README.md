# b2b_sales_intelligence_etl

Esta pasta define o código-fonte da pipeline B2B Sales Intelligence:

- `explorations/`: Notebooks ad-hoc usados para explorar os dados processados pela pipeline.
- `transformations/`: Todas as definições de datasets e transformações (Bronze, Silver e Gold).
- `utilities/` (opcional): Funções utilitárias e módulos Python usados na pipeline.
- `data_sources/` (opcional): Definições de views que descrevem os dados de origem.

## Getting Started

As transformações Bronze, Silver e Gold serão adicionadas em `transformations/` nas próximas etapas do projeto (etapas 01 a 03 dos prompts).

* Por convenção, cada dataset em `transformations` fica em um arquivo separado.
* Mais sobre a sintaxe em https://docs.databricks.com/dlt/python-ref.html.
* No workspace, use `Run file` para executar e visualizar uma transformação isolada.
* Pela CLI, use `databricks bundle run b2b_sales_intelligence_etl --refresh <nome_da_transformacao>` para rodar uma transformação isolada.

Para tutoriais e material de referência, veja https://docs.databricks.com/dlt.
