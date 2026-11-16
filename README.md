# Projeto 5 - Planejamento de experimentos em Python

Implementação local da **parte principal** de `plano_experimento_doe_lambda.md`, baseada no Projeto 5 do manual. Inclui simulação, regressão, ANOVA, diagnósticos, gráficos, relatório PDF e interface opcional. Não exige conta AWS nem conexão de rede após instalar as bibliotecas.

Código: [t4rcisio/pe_sistemas_dist](https://github.com/t4rcisio/pe_sistemas_dist). O relatório usa apresentação acadêmica em preto e branco, com cabeçalho do CEFET-MG e explicações voltadas à leitura do trabalho. As fontes e decisões de formatação estão em [docs/criterios_editoriais.md](docs/criterios_editoriais.md).

## Instalação (Windows / PowerShell)

Python 3.11 ou superior. Na pasta deste projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe executar.py
```

Não é necessário ativar o ambiente virtual. Se você já instalou as dependências no Python atual, basta `python executar.py`.

## Interface local

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abra o endereço local informado pelo Streamlit. A interface permite alterar semente, repetições e ruído, explorar resultados e baixar CSV/PDF. Cada nova execução da interface substitui `resultados_interface/`. A execução de linha de comando usa `resultados/` por padrão. Os arquivos originais do trabalho são preservados.

## Linha de comando

```powershell
python executar.py
python executar.py gerar --saida minha_execucao
python executar.py analisar --saida minha_execucao
python executar.py analisar --entrada minha_execucao/dados_simulados.csv --saida nova_analise
python executar.py --config configuracoes/simulacao.json --saida outra_execucao
python -m unittest discover -s tests -v
```

As etapas `gerar` e `analisar` são separadas para permitir análise sem consultar as colunas de verdade populacional. Use a mesma configuração nas duas etapas, especialmente o número de repetições. Para analisar uma execução configurada anteriormente, passe `--config minha_execucao/configuracao_utilizada.json`. `--entrada` aceita apenas bases completas com o delineamento deste projeto, não dados arbitrários.

## Delineamento e modelo

- Fatorial completo 2⁴: TTL (15/120 s), pool (20/100), workers (4/16), evicção (LRU Volatile/LFU Allkeys).
- Duas regiões como blocos cruzados com todos os tratamentos: us-east-1 e sa-east-1.
- Três repetições independentes por combinação e região, total de 96 observações; ordem aleatória dentro do bloco.
- Semente 2026. NumPy usa fluxos independentes para ordem e ruído. A sequência não pretende ser idêntica à de R com a mesma semente.
- DGP: `Y = 85 - 18 X1 - 12 X2 - 8 X3 + 14 X2 X3 + 15 Z + erro`, com `Z=-1/+1` nas regiões e erro normal de desvio padrão 3 ms (variância 9 ms²).
- A resposta é **uma medição simulada de P99**, não uma amostra de latências individuais da qual calculamos P99.
- O modelo inclui bloco, quatro efeitos principais e todas as seis interações entre pares. Não selecionamos termos automaticamente por p-valor.

ANOVA tipo II, ICs e p-valores usam OLS. A comparação com/sem bloco mantém os mesmos termos fatoriais. O efeito fatorial é duas vezes o coeficiente codificado; com interação, o efeito de workers depende do pool. Os ICs não recebem ajuste para múltiplas comparações.

Shapiro-Wilk é aplicado aos resíduos. Levene com centro na mediana usa as 32 células (região × quatro fatores), com três respostas por grupo na configuração padrão. Isso tem baixa potência. A falta de ajuste é comparada ao erro puro das réplicas. Há gráficos Q-Q, resíduos versus ajustados, resíduos por ordem e distância de Cook (referência 4/n, sem exclusão automática). P-valores não comprovam pressupostos; qualquer sinalização deve ser interpretada junto aos gráficos.

O ranking inclui IC da média e intervalo de predição para uma nova medição simulada. Uma média abaixo de 50 ms não garante atendimento em toda medição. X4 tem efeito populacional nulo; diferenças amostrais entre políticas não justificam vantagem causal. A melhor configuração teórica é TTL 120 s, pool 100, workers 4, em ambas as políticas: médias de 34 ms e 64 ms por região. Esses valores vêm do exercício, não de medições da AWS.

Na execução padrão, X1:X4 tem p≈0,045 apesar de efeito populacional nulo: é um falso positivo identificado pela verdade conhecida. O relatório sinaliza automaticamente os termos nulos que ultrapassam o limiar de significância. Não alteramos a semente nem excluímos resultados para fazer os testes concordarem com o DGP.

## Arquivos gerados

| Arquivo/pasta em `resultados/` | Conteúdo |
|---|---|
| `dados_simulados.csv` | Matriz, níveis físicos, ordem, resposta, média teórica e erro |
| `tabelas/coeficientes.csv` | Estimativas, verdade, erros, ICs, efeitos e p-valores |
| `tabelas/anova.csv` | ANOVA tipo II |
| `tabelas/comparacao_blocos.csv` | SQ, gl e QM residual nos dois modelos |
| `tabelas/diagnosticos.csv` | Shapiro, Levene e falta de ajuste |
| `tabelas/residuos.csv` | Ajustados, resíduos e influência |
| `tabelas/ranking.csv` | 32 configurações/regiões e intervalos |
| `tabelas/resumo_tratamentos.csv` | Estatísticas das réplicas |
| `graficos/` | Quatro figuras PNG |
| `relatorio.pdf` | Relatório técnico com resultados da execução |
| `modelo.txt`, `resumo.json` | Resumo OLS e indicadores principais |
| `configuracao_utilizada.json`, `ambiente.json` | Parâmetros e versões para reprodução |

Os CSVs usam vírgula como delimitador e ponto decimal, com UTF-8 BOM para facilitar importação. No Excel em português, importe via Dados → De Texto/CSV e selecione o delimitador correto.

## Escopo e limitações

A extensão real com Lambda descrita no plano permanece futura: não há provisionamento, credenciais, coleta real, estimativa de custo ou resultados de Lambda neste projeto local. O throughput não é inventado porque o manual não define uma equação para essa resposta; alinhe essa exigência com o professor. As duas pendências estão documentadas também no relatório.

O relatório é gerado automaticamente com a autoria indicada no plano e deve ser revisado antes da entrega. Os testes verificam balanceamento, reprodução, recuperação exata dos parâmetros sem ruído, interação, ótimo teórico, comparação dos blocos, intervalos e rejeição de bases inválidas.

## Organização do código

`doe/simulacao.py` contém a geração; `doe/analise.py`, o ajuste e gráficos; `doe/relatorio.py`, o PDF. `executar.py` coordena as etapas e `app.py` fornece a interface. Todos os cálculos são executados no seu computador.
