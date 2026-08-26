# Discovery — Nexum Sales Assistant

## Status

Em definição.

## Empresa fictícia

A Nexum Industrial é uma empresa B2B que fornece equipamentos e
soluções para manutenção e operação industrial.

Seu catálogo inclui equipamentos profissionais, sensores,
instrumentos de medição e dispositivos de monitoramento.

## Cliente do projeto

A Nexum Industrial contratou uma solução para reduzir a fricção
entre a necessidade técnica do cliente e a geração de uma cotação.

## Público-alvo

### Usuário comprador

Profissionais de empresas de médio e grande porte que precisam
encontrar equipamentos para manutenção, operação ou monitoramento.

Exemplos:

- fábricas;
- centros de distribuição;
- varejistas com muitas unidades;
- empresas de manutenção industrial.

### Usuário interno

Vendedores e representantes comerciais da Nexum Industrial.

## Problema

Vendedores B2B gastam tempo significativo traduzindo a necessidade
do cliente em produtos adequados, consultando especificações técnicas,
disponibilidade, preço e prazo.

Essa fricção pode atrasar a cotação, aumentar o tempo de atendimento
e fazer com que oportunidades comerciais sejam perdidas.

## Pergunta de negócio

Como poderíamos ajudar clientes B2B a encontrar equipamentos adequados
para suas necessidades, reduzindo o tempo entre a descrição do problema
e a geração de uma cotação confiável?

## Hipótese

Se um assistente conseguir entender a necessidade do cliente, fazer
perguntas de esclarecimento e consultar dados confiáveis de produtos,
preço, estoque e prazo, o vendedor poderá avançar mais rapidamente
na oportunidade comercial.

## Exemplo de necessidade

O cliente não informa necessariamente um SKU.

Ele pode dizer:

> Preciso monitorar a temperatura de várias máquinas e hoje faço isso
> manualmente.

O assistente deverá buscar informações adicionais, como:

- quantidade de equipamentos;
- faixa de temperatura;
- necessidade de monitoramento contínuo;
- ambiente de instalação;
- prazo desejado.

Somente depois deverá consultar o catálogo e apresentar opções compatíveis.

## Jornada desejada

1. Cliente descreve uma necessidade.
2. Assistente identifica a categoria provável.
3. Assistente faz perguntas de esclarecimento.
4. Assistente consulta os produtos disponíveis.
5. Assistente apresenta até três opções compatíveis.
6. Cliente escolhe uma opção ou solicita comparação.
7. Assistente consulta preço, estoque e prazo atuais.
8. Assistente monta uma cotação ou pedido preliminar.
9. Vendedor aprova a condição comercial.
10. Pagamento é simulado.
11. Documento é gerado sem validade fiscal.
12. Atendimento e pedido são registrados para auditoria.

## Escopo do MVP

O MVP atenderá inicialmente necessidades relacionadas a:

- monitoramento de temperatura;
- medição de pressão;
- monitoramento de vibração.

O MVP deverá:

- consultar um catálogo estruturado;
- filtrar produtos por atributos compatíveis;
- informar preço, estoque e prazo;
- evitar inventar especificações;
- montar uma cotação preliminar;
- exigir aprovação humana antes da confirmação;
- simular pagamento;
- gerar um documento simulado;
- registrar os eventos principais da jornada.

## Fora do escopo

- pagamento real;
- nota fiscal real;
- integração com ERP;
- integração com CRM real;
- reserva física de estoque;
- entrega real;
- negociação autônoma de descontos;
- recomendação técnica para situações críticas sem validação humana;
- modelo de machine learning;
- previsão de demanda;
- catálogo com milhares de produtos;
- atendimento omnichannel;
- agente totalmente autônomo.

## Human-in-the-loop

A aprovação humana será obrigatória antes de:

- confirmar o pedido;
- aplicar desconto;
- aceitar quantidade fora da política;
- confirmar uma condição comercial;
- concluir pagamento simulado;
- emitir o documento simulado.

O assistente poderá preparar a cotação, mas não poderá confirmar
sozinho uma ação comercial irreversível.

## Fonte da verdade

As informações abaixo deverão ser recuperadas dos dados estruturados:

- nome do produto;
- categoria;
- especificações;
- preço;
- estoque;
- prazo;
- status de disponibilidade.

O modelo de linguagem não poderá inventar esses dados.

Quando uma informação não estiver disponível, o assistente deverá informar
que não possui dados suficientes e encaminhar para revisão humana.

## Dados existentes

A base atual de empresas e funcionários será mantida como contexto
de CRM e poderá ser utilizada em uma evolução do projeto.

Ela não é suficiente para representar o catálogo, o estoque e os pedidos
do novo produto.

## Dados adicionais necessários

Precisaremos criar dados sintéticos controlados para:

- produtos;
- estoque;
- preços;
- pedidos;
- itens de pedido;
- cotações;
- aprovações;
- pagamentos simulados;
- documentos simulados;
- eventos de conversa.

## Impacto esperado

A solução busca reduzir o tempo gasto na etapa de identificação e
recomendação de produtos, diminuindo a fricção entre a necessidade do
cliente e a geração de uma oportunidade comercial.

Não será afirmado, no MVP, que o sistema reduz diretamente o ciclo
operacional, aumenta a conversão ou aumenta a receita, pois não teremos
dados históricos suficientes para provar esses efeitos.

## Métricas do MVP

### Métricas funcionais

- percentual de consultas respondidas com produtos existentes;
- percentual de respostas com preço, estoque e prazo rastreáveis;
- percentual de recomendações sem produto incompatível;
- percentual de pedidos que exigiram aprovação humana;
- quantidade de pedidos simulados corretamente registrados.

### Métricas de experiência

- tempo entre a necessidade inicial e a primeira recomendação;
- quantidade de perguntas necessárias para chegar a uma recomendação;
- quantidade de conversas que terminam sem produto compatível;
- avaliação humana da qualidade da recomendação.

### Métricas de segurança e confiabilidade

- quantidade de preços inventados;
- quantidade de produtos recomendados sem estoque;
- quantidade de ações executadas sem aprovação;
- quantidade de eventos sem registro de auditoria.

## Princípio

O assistente deve facilitar a venda sem esconder a lógica,
inventar informações ou substituir a responsabilidade humana
sobre decisões comerciais.