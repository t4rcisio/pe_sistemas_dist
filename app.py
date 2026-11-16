"""Interface opcional: python -m streamlit run app.py"""
import json
import pandas as pd
import streamlit as st

from executar import RAIZ, executar
from doe.simulacao import Config

st.set_page_config(page_title="DoE | Projeto 5", page_icon="📊", layout="wide")
st.title("Experimento de desempenho de e-commerce")
st.caption("Projeto 5 · Fatorial 2⁴ · Duas regiões · Dados simulados")
st.info("As regiões e configurações são fatores de uma equação matemática. Não há conexão com serviços AWS.")
with st.sidebar:
    st.header("Simulação")
    semente = st.number_input("Semente", min_value=0, value=2026, step=1)
    repeticoes = st.number_input("Repetições por célula", min_value=2, max_value=100, value=3, step=1)
    sigma = st.number_input("Desvio padrão do erro (ms)", min_value=0.1, value=3.0, step=0.1)
    st.caption("Meta: < 50 ms · Significância: 5%")
    rodar = st.button("Executar experimento", type="primary")
    st.caption("A interface salva sua execução em resultados_interface/.")
destino = RAIZ / "resultados_interface"
if rodar:
    with st.spinner("Gerando dados e análises…"):
        executar(Config(semente=int(semente), repeticoes=int(repeticoes), sigma_ms=float(sigma)), destino)
    st.success("Experimento concluído.")
if not (destino / "resumo.json").exists():
    destino = RAIZ / "resultados"
if not (destino / "resumo.json").exists():
    st.write("Selecione os parâmetros e clique em Executar experimento.")
    st.stop()
resumo = json.loads((destino / "resumo.json").read_text(encoding="utf-8"))
config = Config.carregar(destino / "configuracao_utilizada.json")
st.caption(f"Resultados exibidos: semente {config.semente}, {config.repeticoes} repetições, σ={config.sigma_ms:g} ms.")
a, b, c = st.columns(3)
a.metric("Observações", resumo["n_observacoes"])
b.metric("Redução da SQ residual com bloco", f"{resumo['reducao_sq_residual_pct']:.1f}%")
c.metric("Diferença regional estimada", f"{resumo['diferenca_regional_ms']:.2f} ms")
abas = st.tabs(["Configurações", "ANOVA e efeitos", "Diagnósticos", "Dados e relatório"])
ler = lambda nome: pd.read_csv(destino / "tabelas" / f"{nome}.csv")
with abas[0]:
    st.image(str(destino / "graficos" / "configuracoes.png"))
    regiao = st.selectbox("Região", ["us-east-1", "sa-east-1"])
    ranking = ler("ranking")
    st.dataframe(ranking[ranking.regiao == regiao], hide_index=True)
    st.caption("IC: incerteza da média. IP: uma futura medição simulada de P99. X4 tem efeito populacional zero.")
with abas[1]:
    st.dataframe(ler("anova"), hide_index=True)
    st.dataframe(ler("coeficientes"), hide_index=True)
    st.image(str(destino / "graficos" / "interacao_pool_workers.png"))
    st.image(str(destino / "graficos" / "efeitos.png"))
with abas[2]:
    st.dataframe(ler("comparacao_blocos"), hide_index=True)
    st.dataframe(ler("diagnosticos"), hide_index=True)
    st.image(str(destino / "graficos" / "diagnosticos.png"))
    st.caption("Testes que não rejeitam H0 não comprovam os pressupostos. Levene tem baixa potência com poucas réplicas por célula.")
with abas[3]:
    st.dataframe(pd.read_csv(destino / "dados_simulados.csv"), hide_index=True)
    st.download_button("Baixar dados CSV", (destino / "dados_simulados.csv").read_bytes(), "dados_simulados.csv", "text/csv")
    relatorio = RAIZ / "resultados" / "relatorio.pdf"
    if relatorio.exists():
        st.download_button("Baixar relatório do trabalho", relatorio.read_bytes(), "relatorio.pdf", "application/pdf")
