# Churn Prediction: Previsão de Evasão de Clientes no Databricks

Este projeto implementa um pipeline de Machine Learning focado em identificar clientes com maior probabilidade de cancelamento (Churn). O fluxo foi desenhado para transformar dados brutos da camada Silver em inteligência estratégica na camada Gold.

## Contexto de Negócio
O objetivo principal é fornecer ao time de Customer Success uma ferramenta proativa. Em vez de reagir ao cancelamento, o modelo permite identificar padrões de comportamento que antecedem a saída do cliente, possibilitando ações de retenção direcionadas.

## Estrutura do Projeto
O notebook segue a arquitetura medalhão e está dividido nas seguintes etapas:

1. **Processamento (Silver):** Limpeza e padronização dos dados históricos.
2. **Engenharia de Atributos (Feature Engineering):** Criação de variáveis de comportamento, como a taxa de uso em relação ao valor contratado e o tempo de permanência (tenure).
3. **Modelagem:** Implementação de um classificador de Floresta Aleatória (Random Forest). 
   * *Nota técnica:* Devido a restrições de clusters compartilhados no Databricks, utilizei uma abordagem híbrida com PySpark para o processamento de dados e Scikit-Learn para o treino do modelo.
4. **Entrega (Gold):** Geração de uma tabela final contendo o ID do cliente e a sua respetiva probabilidade de churn.

## Tecnologias Utilizadas
* **Databricks:** Ambiente de desenvolvimento e processamento.
* **PySpark:** Manipulação e transformação de grandes volumes de dados.
* **Scikit-Learn:** Treino do algoritmo de Machine Learning.
* **Pandas:** Interface para transição de dados entre Spark e o modelo.

## Diferenciais da Solução
* **Foco em Probabilidade:** O modelo não entrega apenas um "sim" ou "não", mas uma probabilidade, permitindo priorizar os clientes de maior risco.
* **Contorno Técnico:** Resolução de limitações de infraestrutura (whitelisting) através da integração eficiente entre Spark e bibliotecas Python tradicionais.

## Próximos Passos
Este projeto é a primeira etapa de uma série de análises sobre o ciclo de vida do cliente. Atualmente, estou a desenvolver um dashboard para visualizar estes indicadores, que será integrado ao meu portfólio de projetos em breve.
