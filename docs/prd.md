# PRD — Nexum Sales Assistant

## 1. Informações do documento

- **Produto:** code docs/agent_harness.md Assistant
- **Empresa fictícia:** Nexum Industrial
- **Versão:** 0.1
- **Status:** Draft
- **Responsável:** Jennifer
- **Data:** 2026-08-26

## 2. Resumo executivo

A Nexum Industrial é uma empresa B2B que vende equipamentos e
soluções para manutenção, operação e monitoramento industrial.

O Nexum Sales Assistant é um assistente de vendas que ajuda clientes
a transformar uma necessidade descrita em linguagem natural em uma
recomendação de produto e uma cotação preliminar.

O assistente consulta dados estruturados de catálogo, especificações,
preço, estoque e prazo. Ele não poderá inventar informações comerciais
ou técnicas.

A confirmação de um pedido, a aprovação de condições comerciais,
o pagamento simulado e a emissão do documento simulado dependerão
de validação humana.

## 3. Problema

Vendedores B2B gastam tempo significativo traduzindo a necessidade
do cliente em produtos adequados, consultando especificações técnicas,
disponibilidade, preço e prazo.

Essa fricção pode:

- atrasar a geração de cotações;
- aumentar o tempo de atendimento;
- dificultar a escolha do produto correto;
- fazer o cliente abandonar a conversa;
- reduzir a velocidade de avanço das oportunidades comerciais.

## 4. Oportunidade

Criar um assistente capaz de:

1. compreender a necessidade inicial do cliente;
2. identificar quais informações ainda faltam;
3. fazer perguntas de esclarecimento;
4. consultar produtos compatíveis;
5. verificar preço, estoque e prazo;
6. apresentar recomendações explicáveis;
7. preparar uma cotação preliminar;
8. encaminhar ações comerciais sensíveis para aprovação humana.

## 5. Objetivo do produto

Reduzir a fricção entre a descrição da necessidade do cliente e a
geração de uma cotação confiável, sem comprometer a precisão dos dados,
a segurança das ações ou a responsabilidade comercial humana.

## 6. Pergunta de produto

> Como poderíamos ajudar clientes B2B a encontrar equipamentos adequados
> para suas necessidades, reduzindo o tempo entre a descrição do problema
> e a geração de uma cotação confiável?

## 7. Usuários

### 7.1 Usuário principal do atendimento

Profissional de uma empresa de médio ou grande porte que precisa
encontrar equipamentos para manutenção, operação ou monitoramento.

Exemplos:

- técnico de manutenção;
- comprador;
- analista de suprimentos;
- responsável por operações;
- engenheiro de produção.

### 7.2 Usuário interno

Vendedor ou representante comercial da Nexum Industrial.

Esse usuário revisa recomendações, aprova condições comerciais e
acompanha o histórico do atendimento.

### 7.3 Administrador do catálogo

Responsável por manter produtos, especificações, preços, estoque
e prazos atualizados.

## 8. Domínio do MVP

O MVP atenderá inicialmente três tipos de necessidade:

1. monitoramento de temperatura;
2. medição de pressão;
3. monitoramento de vibração.

O catálogo inicial será pequeno e controlado, com produtos sintéticos
criados especificamente para a demonstração.

## 9. Jornada principal

1. O cliente inicia uma conversa.
2. O cliente descreve uma necessidade em linguagem natural.
3. O assistente identifica a categoria provável da necessidade.
4. O assistente verifica se possui informações suficientes.
5. Se necessário, faz perguntas de esclarecimento.
6. O assistente extrai requisitos estruturados da conversa.
7. O sistema consulta produtos compatíveis.
8. O sistema verifica estoque, preço e prazo.
9. O assistente apresenta até três opções.
10. O cliente escolhe uma opção ou pede comparação.
11. O assistente monta uma cotação preliminar.
12. Um vendedor revisa e aprova a cotação.
13. O pagamento é simulado.
14. Um documento sem validade fiscal é gerado.
15. Os eventos da conversa, cotação, aprovação e pagamento são registrados.

## 10. Exemplo de interação

### Necessidade inicial

> Preciso monitorar a temperatura de várias máquinas e hoje faço isso
> manualmente.

### Perguntas esperadas

O assistente pode perguntar:

- Quantas máquinas serão monitoradas?
- Qual é a faixa aproximada de temperatura?
- O monitoramento precisa ser contínuo?
- O ambiente possui umidade, poeira ou vibração intensa?
- Existe alguma restrição de prazo?

### Recomendação esperada

Após obter informações suficientes, o sistema deverá apresentar
produtos compatíveis com:

- categoria correta;
- faixa de operação adequada;
- quantidade disponível;
- preço registrado;
- prazo registrado.

A recomendação deverá explicar os principais critérios utilizados.

## 11. Requisitos funcionais

### RF01 — Iniciar atendimento

O sistema deve permitir o início de uma sessão de atendimento.

### RF02 — Interpretar necessidade

O sistema deve interpretar a mensagem inicial do cliente e identificar
uma categoria provável de produto.

Categorias do MVP:

- temperatura;
- pressão;
- vibração.

Se a categoria não puder ser identificada com segurança, o sistema
deverá pedir esclarecimentos ou encaminhar para um vendedor.

### RF03 — Solicitar informações faltantes

O assistente deve identificar requisitos necessários para a busca
de produtos e fazer perguntas antes de recomendar uma solução.

### RF04 — Buscar produtos

O sistema deve consultar produtos ativos que atendam aos requisitos
extraídos da conversa.

### RF05 — Consultar estoque

O sistema deve consultar a quantidade disponível antes de informar
disponibilidade ao cliente.

### RF06 — Consultar preço e prazo

O preço e o prazo informados devem vir dos dados estruturados do sistema.

### RF07 — Apresentar recomendações

O sistema deve apresentar no máximo três opções compatíveis, quando
existirem.

Cada opção deve conter, quando disponível:

- nome;
- categoria;
- descrição;
- especificações relevantes;
- preço;
- moeda;
- quantidade disponível;
- prazo estimado;
- justificativa de compatibilidade.

### RF08 — Informar ausência de compatibilidade

Quando nenhum produto atender aos requisitos, o sistema não deve inventar
uma alternativa. Deve informar que não encontrou uma opção compatível e
encaminhar o caso para análise humana.

### RF09 — Criar cotação preliminar

O sistema deve permitir a criação de uma cotação preliminar com:

- cliente;
- produtos;
- quantidades;
- preços consultados;
- subtotal;
- data de criação;
- validade;
- status.

### RF10 — Solicitar aprovação humana

A cotação deve passar por aprovação humana antes de ser confirmada.

### RF11 — Simular pagamento

O sistema poderá simular um pagamento somente após a aprovação da cotação.

O pagamento não terá valor financeiro real.

### RF12 — Gerar documento simulado

O sistema poderá gerar um documento de confirmação sem validade fiscal.

### RF13 — Registrar auditoria

O sistema deve registrar eventos relevantes da jornada:

- mensagem recebida;
- pergunta realizada;
- produto consultado;
- estoque consultado;
- preço retornado;
- cotação criada;
- aprovação solicitada;
- aprovação realizada;
- pagamento simulado;
- documento gerado.

## 12. Regras de negócio

### RN01 — Fonte da verdade

Nome, especificações, preço, estoque e prazo devem ser recuperados
dos dados estruturados.

### RN02 — Proibição de invenção

O assistente não pode inventar:

- produtos;
- preços;
- estoque;
- prazos;
- especificações;
- descontos;
- condições de pagamento.

### RN03 — Produto ativo

Somente produtos com `active = true` podem ser recomendados.

### RN04 — Estoque

Um produto não deve ser apresentado como disponível quando a quantidade
solicitada for maior que a quantidade disponível.

### RN05 — Recomendação insuficiente

O sistema não deve recomendar um produto quando faltarem requisitos
essenciais para avaliar compatibilidade.

### RN06 — Aprovação comercial

O assistente não pode confirmar sozinho:

- pedido;
- desconto;
- condição especial;
- quantidade fora da política;
- pagamento;
- documento final.

### RN07 — Falha de dados

Quando estoque, preço ou prazo não estiverem disponíveis, o sistema
deve informar a ausência do dado e encaminhar para revisão humana.

### RN08 — Rastreabilidade

Toda recomendação deve poder ser relacionada aos produtos e atributos
consultados.

## 13. Requisitos não funcionais

### RNF01 — Rastreabilidade

As respostas comerciais devem ser rastreáveis às tabelas e registros
consultados.

### RNF02 — Segurança

Nenhum pagamento real ou documento fiscal real será utilizado.

### RNF03 — Explicabilidade

O sistema deve informar por que um produto foi recomendado.

### RNF04 — Controle de ações

Ações irreversíveis ou comercialmente sensíveis devem exigir aprovação
humana.

### RNF05 — Reprodutibilidade

Os dados e transformações devem ser versionados e reproduzíveis.

### RNF06 — Qualidade de dados

As tabelas devem possuir validações para chaves, tipos, nulos,
quantidades e consistência entre entidades.

### RNF07 — Observabilidade

Os eventos da conversa e das ferramentas devem ser registrados.

## 14. Arquitetura conceitual

```text
Cliente
   |
   v
Interface de conversa
   |
   v
Sales Assistant
   |
   +--> Interpretação da necessidade
   |
   +--> Ferramentas determinísticas
   |       |
   |       +--> Busca de produtos
   |       +--> Consulta de estoque
   |       +--> Consulta de preço
   |       +--> Consulta de prazo
   |       +--> Criação de cotação
   |       +--> Solicitação de aprovação
   |       +--> Pagamento simulado
   |       +--> Documento simulado
   |
   v
Databricks
   |
   +--> Bronze
   +--> Silver
   +--> Gold
   |
   v
Vendedor / aprovador humano
```

## 15. Dados necessários

### Dados já existentes

- empresas;
- funcionários;
- contatos;
- atributos de contexto comercial.

Esses dados serão tratados como contexto de CRM.

### Dados a criar

- produtos;
- estoque;
- preços;
- cotações;
- itens de cotação;
- pedidos;
- itens de pedido;
- aprovações;
- pagamentos simulados;
- documentos simulados;
- eventos de conversa.

## 16. Escopo do MVP

### Incluído

- catálogo sintético pequeno;
- três categorias de necessidade;
- consulta estruturada de produtos;
- filtro por atributos de compatibilidade;
- consulta de preço;
- consulta de estoque;
- consulta de prazo;
- recomendação de até três produtos;
- criação de cotação preliminar;
- aprovação humana;
- pagamento simulado;
- documento simulado;
- auditoria da jornada;
- pipeline de dados no Databricks;
- testes de jornadas principais;
- documentação técnica.

### Fora do MVP

- pagamento real;
- nota fiscal real;
- integração com ERP;
- integração com CRM real;
- reserva física de estoque;
- logística real;
- negociação autônoma;
- descontos automáticos;
- machine learning;
- previsão de demanda;
- catálogo com milhares de produtos;
- atendimento por voz;
- múltiplos canais;
- agente totalmente autônomo.

## 17. Critérios de aceite

### CA01 — Recomendação

Dado um cenário com requisitos suficientes, o sistema deve retornar
produtos existentes e compatíveis no catálogo.

### CA02 — Dados comerciais

Toda recomendação que informe preço, estoque ou prazo deve utilizar
dados existentes nas tabelas consultadas.

### CA03 — Ausência de produto

Quando não houver produto compatível, o sistema deve informar a ausência
de resultado e não inventar uma recomendação.

### CA04 — Estoque insuficiente

Quando a quantidade solicitada exceder o estoque disponível, o sistema
deve indicar a indisponibilidade.

### CA05 — Cotação

O sistema deve criar uma cotação com produtos e preços registrados.

### CA06 — Aprovação

O sistema não deve confirmar o pedido antes da aprovação humana.

### CA07 — Pagamento

O pagamento deve ser explicitamente identificado como simulado.

### CA08 — Documento

O documento gerado deve informar que não possui validade fiscal.

### CA09 — Auditoria

Os eventos principais da jornada devem ser registrados.

### CA10 — Reprodutibilidade

A mesma entrada e os mesmos dados de catálogo devem produzir resultados
consistentes nas ferramentas determinísticas.

## 18. Métricas do MVP

### Métricas funcionais

- percentual de cenários respondidos com produtos existentes;
- percentual de recomendações com preço rastreável;
- percentual de recomendações com estoque rastreável;
- percentual de recomendações com prazo rastreável;
- percentual de cotações criadas corretamente;
- percentual de pedidos bloqueados corretamente até a aprovação.

### Métricas de qualidade

- quantidade de produtos recomendados sem compatibilidade;
- quantidade de preços inventados;
- quantidade de recomendações sem estoque;
- quantidade de ações executadas sem aprovação;
- quantidade de eventos sem registro de auditoria.

### Métrica de experiência

- tempo entre a primeira mensagem e a primeira recomendação;
- quantidade média de perguntas até a recomendação;
- avaliação humana da qualidade das recomendações.

Essas métricas avaliarão o protótipo. Não serão usadas para afirmar,
sozinhas, aumento de receita ou redução comprovada do ciclo operacional.

## 19. Riscos

| Risco | Mitigação |
|---|---|
| O agente recomendar produto incompatível | Filtrar produtos com regras determinísticas |
| Preço ou estoque inventado | Consultar tabelas por ferramentas |
| Falta de informação técnica | Fazer perguntas ou encaminhar para humano |
| Pedido confirmado sem aprovação | Implementar estado e validação de aprovação |
| Dados sintéticos pouco realistas | Documentar origem e regras de geração |
| Escopo grande demais | Limitar o MVP a três categorias |
| Demonstração sem rastreabilidade | Registrar eventos e referências dos dados |
| Confusão entre recomendação e decisão técnica | Exigir validação humana em casos críticos |
| Dados desatualizados | Registrar `updated_at` e informar a data da consulta |

## 20. Princípios do produto

1. O modelo interpreta a linguagem; o código controla as ações.
2. O dado estruturado é a fonte da verdade comercial.
3. O assistente não deve preencher lacunas inventando informações.
4. Ações sensíveis exigem aprovação humana.
5. Toda recomendação deve ser explicável e auditável.
6. O MVP deve ser pequeno o suficiente para ser testado.