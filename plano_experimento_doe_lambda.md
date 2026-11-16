# Plano do trabalho final: planejamento de experimentos em sistemas distribuídos

**Disciplina:** GT00SIN010.1 - Tópicos Especiais em Sistemas Inteligentes: Planejamento de Experimentos em Computação - T01 (2026.2)
**Aluno:** Tarcísio Batista Prates
**Data:** 16/11/2026
**Status:** proposta de execução; experimentos ainda não realizados.

## 1. Proposta

Desenvolver o Projeto 5 do manual, com duas partes:

1. **Parte principal:** simulação de uma plataforma de e-commerce, preservando a equação e os fatores exigidos pelo enunciado.
2. **Parte complementar:** experimento real com uma função AWS Lambda, avaliando recursos computacionais e carga.

As partes serão analisadas separadamente. O experimento no Lambda não reproduz integralmente o sistema de Redis, banco e workers da simulação e não valida seus coeficientes. Seu objetivo é aplicar os mesmos princípios de planejamento experimental a um serviço real.

A substituição da simulação pelo experimento real só deverá ocorrer após alinhamento com o professor.

## 2. Perguntas de pesquisa

### Simulação

- Quais fatores influenciam a latência P99?
- Como o efeito dos workers depende do pool de conexões?
- Quanto a região explica da variabilidade?
- Qual combinação minimiza a latência e atende à meta de 50 ms?

### AWS Lambda

- Qual o efeito da memória configurada sobre a latência?
- Como o tamanho da entrada e a concorrência modificam o desempenho?
- Existem interações entre recursos e carga?
- Qual configuração oferece melhor equilíbrio entre latência, capacidade e custo?

## 3. Parte principal: simulação do Projeto 5

### 3.1 Fatores

| Fator | Código | Nível baixo (-1) | Nível alto (+1) |
|---|---|---|---|
| TTL do Redis | X1 | 15 segundos | 120 segundos |
| Pool de conexões DB | X2 | 20 conexões | 100 conexões |
| Threads de worker | X3 | 4 threads | 16 threads |
| Política de evicção | X4 | LRU Volatile | LFU Allkeys |

Blocos: us-east-1 (Norte da Virgínia) e sa-east-1 (São Paulo).

### 3.2 Delineamento

- Fatorial completo 2^4: 16 combinações.
- Todas as combinações em cada região.
- Três repetições independentes por combinação e região.
- Total: 16 × 2 × 3 = **96 observações simuladas**.
- Ordem aleatorizada dentro de cada bloco.
- Semente fixa: 2026.

As três repetições são uma decisão desta proposta, não uma exigência explícita do manual.

### 3.3 Processo gerador de dados

```text
Y = 85 - 18*X1 - 12*X2 - 8*X3 + 14*X2*X3 + gamma_regiao + erro

gamma_us_east_1 = -15 ms
gamma_sa_east_1 = +15 ms
erro ~ Normal(media=0, variancia=9 ms²)
desvio_padrao = 3 ms
```

A resposta Y é uma medição simulada de latência P99 em ms. Não é a duração de uma requisição individual.

X4 não participa da equação: será mantido no delineamento como fator de efeito populacional nulo. A análise poderá apresentar variação amostral, mas não deverá presumir um efeito real.

Os efeitos regionais são premissas do exercício, não medições ou afirmações sobre o desempenho real das regiões AWS.

### 3.4 Análise

- Ajustar regressão com bloco, efeitos principais e interações de segunda ordem.
- Preservar efeitos principais associados às interações incluídas.
- Construir tabela de ANOVA e apresentar coeficientes, intervalos de confiança e p-valores.
- Adotar nível de significância de 5%.
- Comparar coeficientes estimados com os parâmetros conhecidos do DGP.
- Interpretar a interação X2 × X3.
- Comparar modelos equivalentes com e sem bloco, apresentando soma dos quadrados residual e quadrado médio residual.
- Examinar resíduos versus ajustados, gráfico Q-Q e observações influentes.
- Aplicar Shapiro-Wilk e Levene, explicitando os agrupamentos utilizados e a baixa potência de grupos pequenos.
- Comparar configurações por região e discutir a meta de 50 ms.

O throughput não será simulado sem uma equação justificada e alinhada com o professor.

## 4. Parte complementar: experimento real no AWS Lambda

### 4.1 Aplicação

Implementar uma função Python que receba um conjunto determinístico de pedidos e realize validação, cálculo de totais e agregações.

- Mesmo código, runtime e arquitetura em todos os tratamentos.
- Entradas reproduzíveis, com valores gerados a partir de semente fixa.
- Resultado validado por contagens e totais esperados.
- Sem chamadas a LLMs, Redis ou banco nesta extensão inicial.
- Uma região fixa; sem atribuir efeito regional com apenas uma região medida.
- Registrar runtime, arquitetura, timeout, versão do código e configurações usadas.

### 4.2 Fatores propostos

| Fator | Nível baixo (-1) | Nível alto (+1) |
|---|---|---|
| Memória da função | 512 MB | 1.024 MB |
| Tamanho da entrada | 100 pedidos | 10.000 pedidos |
| Concorrência do gerador de carga | 1 chamada simultânea | 10 chamadas simultâneas |

Fatorial completo 2^3: **8 combinações**.

A memória altera também a CPU disponível. O efeito será interpretado como mudança no conjunto de recursos computacionais.

Concorrência significa chamadas simultâneas mantidas pelo cliente de testes; não será confundida com threads internas nem com concorrência reservada da função.

Os níveis serão verificados em um piloto quanto ao tamanho do payload, duração e limites da conta. Qualquer ajuste será documentado antes da coleta definitiva.

### 4.3 Rodadas e unidade experimental

Proposta inicial:

- Cinco rodadas completas, realizadas em períodos distintos.
- Cada rodada funciona como bloco temporal e contém as oito combinações em ordem aleatória.
- Cada combinação é aplicada em uma janela de carga independente.
- Total inicial: **40 janelas experimentais**.
- Meta inicial de pelo menos 1.000 chamadas medidas por janela, revisada após o piloto.

A unidade experimental será a janela de carga, e não cada chamada isolada. As invocações dentro da janela são subobservações e podem apresentar dependência.

Com 1.000 chamadas, o P99 ainda depende de poucas observações da cauda. O piloto orientará se devemos ampliar a amostra; P99 não será apresentado como estimativa precisa sem avaliar sua estabilidade.

### 4.4 Protocolo de coleta

1. Executar piloto para validar função, gerador e instrumentação.
2. Preparar dados e fixar configurações.
3. Aplicar o tratamento e realizar aquecimento padronizado.
4. Iniciar janela medida, mantendo a concorrência definida.
5. Registrar todas as tentativas, incluindo falhas e throttling.
6. Encerrar janela sem requisições pendentes antes de alterar tratamento.
7. Repetir seguindo a aleatorização registrada.
8. Associar registros do cliente aos logs da função por identificadores de execução.

O gerador permanecerá na mesma máquina/localização, com a mesma configuração de rede, durante as coletas comparáveis. Sua capacidade será verificada para evitar que ele se torne o gargalo.

### 4.5 Cold starts

- Registrar sinais de inicialização nos logs da plataforma.
- Identificar invocações com inicialização e tratar casos não classificáveis como desconhecidos.
- Não presumir que uma pausa garante cold start.
- Relatar frequência e impacto observado.
- Usar invocações sem inicialização como análise principal de estado aquecido.
- Apresentar métricas totais e estratificadas para mostrar o impacto das inicializações.
- Se houver poucas inicializações, não realizar inferências fortes sobre cold start.

### 4.6 Métricas

| Métrica | Definição |
|---|---|
| Latência ponta a ponta | Tempo medido pelo cliente, incluindo transporte e serviço |
| Duração da função | Tempo de execução registrado pela plataforma |
| Mediana, P95 e P99 | Percentis por janela |
| Throughput | Respostas bem-sucedidas divididas pelo tempo medido |
| Taxa de erro | Tentativas com erro divididas pelo total |
| Throttling | Quantidade e proporção de tentativas limitadas |
| Custo estimado | Estimativa baseada no uso medido e preços vigentes |

Não haverá repetição automática silenciosa de chamadas com erro. Se houver retries, eles serão registrados e contabilizados.

Registrar separadamente custo bruto estimado e eventual cobrança efetiva após franquias ou créditos. Não prometer custo zero.

### 4.7 Análise estatística

- Resumir métricas por tratamento e rodada.
- Usar como resposta principal a latência mediana de cada janela; P95 e P99 serão métricas complementares.
- Ajustar modelo fatorial com bloco temporal e efeitos/interações estimáveis.
- Examinar resíduos, heterogeneidade das variâncias e dependência temporal.
- Aplicar transformações ou métodos robustos quando justificados.
- Apresentar tamanhos de efeito e intervalos de confiança.
- Tratar múltiplas respostas como análises exploratórias complementares.
- Avaliar compromisso entre latência, throughput, erros e custo.

O teste com concorrência fixa usa carga de ciclo fechado. As conclusões ficarão restritas a esse protocolo; ele não representa automaticamente um fluxo externo com taxa fixa de chegada.

## 5. Implementação e organização

Estrutura prevista:

```text
projeto_doe/
  README.md
  requirements.txt
  simulacao/
    gerar_dados.py
    analisar.py
  lambda/
    handler.py
    gerar_entradas.py
    executar_experimento.py
    analisar.py
  configuracoes/
    simulacao.json
    experimento_lambda.json
  dados/
    simulados/
    reais/
  resultados/
    tabelas/
    graficos/
  relatorio/
    relatorio_final.pdf
```

Bibliotecas previstas: NumPy, pandas, SciPy, statsmodels, Matplotlib e boto3.

Credenciais AWS ficarão fora do código e dos arquivos entregues. O plano não implica provisionamento imediato de recursos.

## 6. Etapas de execução

| Etapa | Atividade | Saída |
|---|---|---|
| 1 | Confirmar escopo e esclarecer exigência de throughput | Escopo fechado |
| 2 | Construir matriz, DGP e simulação | Base de 96 observações |
| 3 | Realizar ANOVA e diagnósticos | Tabelas e gráficos da simulação |
| 4 | Implementar função e gerador de carga | Código validado |
| 5 | Executar piloto e definir limite de gasto | Protocolo definitivo |
| 6 | Coletar dados reais em rodadas | Dados brutos e metadados |
| 7 | Analisar Lambda e limitações | Comparações de desempenho |
| 8 | Elaborar relatório e instruções | PDF e scripts reprodutíveis |

A parte principal pode ser concluída independentemente da disponibilidade da AWS.

## 7. Entregáveis

1. **Relatório técnico-científico em PDF**, com introdução, variáveis, delineamento, DGP, ANOVA, diagnósticos, recomendações e limitações.
2. **Scripts Python comentados**, separando geração e análise.
3. **Dados simulados e reais**, com configurações e identificação das rodadas.
4. **Gráficos e tabelas**, usados no relatório.
5. **README**, com instruções de reprodução e distinção entre resultados simulados e medidos.

## 8. Critérios de conclusão

- Simulação reproduzível com a semente definida.
- Matriz experimental e blocos documentados.
- ANOVA e diagnósticos executados e interpretados.
- Comparação entre parâmetros verdadeiros e estimados.
- Recomendação fundamentada para o sistema simulado.
- Se a extensão for executada: dados reais rastreáveis, erros contabilizados e limites de inferência explícitos.
- Relatório sem confundir hipótese da simulação com evidência obtida na AWS.

## 9. Pontos a alinhar

- Aceitação da extensão com AWS Lambda.
- Necessidade de modelar throughput na parte simulada.
- Prazo, integrantes, extensão do relatório e eventual apresentação.
- Conta/região AWS disponíveis e orçamento para as medições.

## 10. Referências de partida

- Manual_Projetos_Pesquisa_DoE(1).pdf, Projeto 5 e rubrica de avaliação.
- AWS Lambda: configuração de memória: https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html
- AWS Lambda: ciclo de vida do ambiente: https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html

As configurações, limites e preços aplicáveis serão verificados antes da execução real.
