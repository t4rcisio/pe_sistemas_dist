"""Ajuste sem consultar a média teórica; verdade populacional só na comparação."""
from itertools import combinations
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols

from .simulacao import FATORES, NIVEIS, gerar, validar

TERMOS = FATORES + [f"{a}:{b}" for a, b in combinations(FATORES, 2)]
FORMULA = "latencia_p99_ms ~ Z + " + " + ".join(TERMOS)
VERDADE = {"Intercept": 85, "Z": 15, "X1": -18, "X2": -12, "X3": -8,
           "X4": 0, **{t: (14 if t == "X2:X3" else 0) for t in TERMOS if ":" in t}}


def ajustar(dados, config):
    validar(dados, config)
    base = dados.copy()
    # Contraste centrado: intercepto = média global e diferença regional = 2*beta_Z.
    base["Z"] = base.regiao.map({"us-east-1": -1, "sa-east-1": 1})
    modelo = ols(FORMULA, data=base).fit()
    sem_bloco = ols("latencia_p99_ms ~ " + " + ".join(TERMOS), data=base).fit()
    return base, modelo, sem_bloco


def analisar(dados, config, destino):
    destino = Path(destino)
    tabelas, graficos = destino / "tabelas", destino / "graficos"
    tabelas.mkdir(parents=True, exist_ok=True)
    graficos.mkdir(parents=True, exist_ok=True)
    base, modelo, sem_bloco = ajustar(dados, config)
    ic = modelo.conf_int(alpha=config.alfa)
    coef = pd.DataFrame({"termo": modelo.params.index, "coeficiente": modelo.params.values,
                        "erro_padrao": modelo.bse.values, "ic_inferior": ic[0].values,
                        "ic_superior": ic[1].values, "p_valor": modelo.pvalues.values})
    coef["valor_teorico"] = coef.termo.map(VERDADE)
    coef["erro_estimacao"] = coef.coeficiente - coef.valor_teorico
    coef["efeito_alto_menos_baixo"] = np.where(coef.termo == "Intercept", np.nan, 2 * coef.coeficiente)
    coef["significativo"] = coef.p_valor < config.alfa
    anova = sm.stats.anova_lm(modelo, typ=2).reset_index(names="termo")
    comparacao = pd.DataFrame([
        {"modelo": nome, "sq_residual": m.ssr, "gl_residual": m.df_resid,
         "qm_residual": m.mse_resid, "r2_ajustado": m.rsquared_adj}
        for nome, m in [("sem_bloco", sem_bloco), ("com_bloco", modelo)]])
    resid = modelo.resid
    shapiro = stats.shapiro(resid)
    # 32 células = região x combinação. Usamos respostas, não resíduos correlatos.
    celulas = [g.latencia_p99_ms.to_numpy() for _, g in base.groupby(["regiao"] + FATORES)]
    levene = stats.levene(*celulas, center="median")
    # Teste de falta de ajuste: erro puro nas réplicas vs modelo de segunda ordem.
    medias_celula = base.groupby(["regiao"] + FATORES).latencia_p99_ms.transform("mean")
    sq_puro = float(((base.latencia_p99_ms - medias_celula) ** 2).sum())
    gl_puro = len(base) - len(celulas)
    gl_falta = int(modelo.df_resid - gl_puro)
    sq_falta = max(0.0, float(modelo.ssr - sq_puro))
    f_falta = (sq_falta / gl_falta) / (sq_puro / gl_puro) if sq_puro > 0 else float("nan")
    diagnosticos = pd.DataFrame([
        {"teste": "Shapiro-Wilk", "estatistica": shapiro.statistic, "p_valor": shapiro.pvalue,
         "agrupamento": "resíduos do modelo com bloco"},
        {"teste": "Levene (Brown-Forsythe)", "estatistica": levene.statistic, "p_valor": levene.pvalue,
         "agrupamento": f"32 células: região x X1 x X2 x X3 x X4; n={config.repeticoes}"},
        {"teste": "Falta de ajuste", "estatistica": f_falta, "p_valor": stats.f.sf(f_falta, gl_falta, gl_puro),
         "agrupamento": f"erro puro: {gl_puro} gl; falta de ajuste: {gl_falta} gl"}])
    influencia = modelo.get_influence()
    residuos = base[["ordem", "regiao"] + FATORES + ["latencia_p99_ms"]].copy()
    residuos["ajustado_ms"] = modelo.fittedvalues
    residuos["residuo_ms"] = resid
    residuos["residuo_studentizado"] = influencia.resid_studentized_internal
    residuos["distancia_cook"] = influencia.cooks_distance[0]
    residuos["influente_4_n"] = residuos.distancia_cook > 4 / len(base)

    grade = gerar(config).drop_duplicates(["regiao"] + FATORES).sort_values(["regiao"] + FATORES)
    grade["Z"] = grade.regiao.map({"us-east-1": -1, "sa-east-1": 1})
    pred = modelo.get_prediction(grade).summary_frame(alpha=config.alfa)
    ranking = grade[["regiao"] + FATORES + [v[0] for v in NIVEIS.values()] + ["media_teorica_ms"]].reset_index(drop=True)
    for origem, alvo in [("mean", "media_ajustada_ms"), ("mean_ci_lower", "ic_media_inferior"),
                         ("mean_ci_upper", "ic_media_superior"), ("obs_ci_lower", "ip_inferior"),
                         ("obs_ci_upper", "ip_superior")]:
        ranking[alvo] = pred[origem].to_numpy()
    ranking["media_abaixo_meta"] = ranking.media_ajustada_ms < config.meta_ms
    ranking["ic_media_abaixo_meta"] = ranking.ic_media_superior < config.meta_ms
    ranking["ip_abaixo_meta"] = ranking.ip_superior < config.meta_ms
    ranking = ranking.sort_values(["regiao", "media_ajustada_ms"])
    resumo = base.groupby(["regiao"] + FATORES).latencia_p99_ms.agg(["count", "mean", "std", "min", "max"]).reset_index()
    for nome, tabela in {"coeficientes": coef, "anova": anova, "comparacao_blocos": comparacao,
                         "diagnosticos": diagnosticos, "residuos": residuos, "ranking": ranking,
                         "resumo_tratamentos": resumo}.items():
        tabela.to_csv(tabelas / f"{nome}.csv", index=False, encoding="utf-8-sig")
    texto_modelo = "\n".join(linha.rstrip() for linha in str(modelo.summary()).splitlines()) + "\n"
    (destino / "modelo.txt").write_text(texto_modelo, encoding="utf-8")
    config.salvar(destino / "configuracao_utilizada.json")
    _graficos(base, modelo, coef, residuos, ranking, config, graficos)
    resultado = {"n_observacoes": len(base), "formula": FORMULA, "alfa": config.alfa,
                 "reducao_sq_residual_pct": float(100 * (1 - modelo.ssr / sem_bloco.ssr)),
                 "diferenca_regional_ms": float(2 * modelo.params["Z"]),
                 "efeito_workers_pool_baixo_ms": float(2 * (modelo.params["X3"] - modelo.params["X2:X3"])),
                 "efeito_workers_pool_alto_ms": float(2 * (modelo.params["X3"] + modelo.params["X2:X3"])),
                 "observacoes_influentes": int(residuos.influente_4_n.sum())}
    (destino / "resumo.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


def _graficos(base, modelo, coef, residuos, ranking, config, pasta):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.prop_cycle": plt.cycler(color=["black", "0.5"])})

    def salvar(fig, nome):
        for ax in fig.axes:
            for linha in ax.lines:
                linha.set_color("black")
                linha.set_markeredgecolor("black")
                linha.set_markerfacecolor("white" if linha.get_marker() == "s" else "black")
        fig.savefig(pasta / nome, dpi=160, bbox_inches="tight")
        plt.close(fig)

    fig, eixos = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    eixos[0, 0].scatter(modelo.fittedvalues, modelo.resid, alpha=.7, color="black")
    eixos[0, 0].axhline(0, color="gray", ls="--")
    eixos[0, 0].set(xlabel="Ajustado (ms)", ylabel="Resíduo (ms)", title="Resíduos vs. ajustados")
    sm.qqplot(modelo.resid, line="s", ax=eixos[0, 1], markerfacecolor="black")
    eixos[0, 1].set_title("Q-Q normal dos resíduos")
    ordenados = residuos.sort_values("ordem")
    eixos[1, 0].plot(ordenados.ordem, ordenados.residuo_ms, ".-", color="black")
    eixos[1, 0].axhline(0, color="gray", ls="--")
    eixos[1, 0].set(xlabel="Ordem de execução", ylabel="Resíduo (ms)", title="Resíduos na ordem de execução")
    eixos[1, 1].stem(residuos.ordem, residuos.distancia_cook, linefmt="k-", markerfmt="k.", basefmt=" ")
    eixos[1, 1].axhline(4 / len(base), color="0.5", ls="--", label="Referência 4/n")
    eixos[1, 1].set(xlabel="Ordem de execução", ylabel="Distância de Cook", title="Influência das observações")
    eixos[1, 1].legend()
    salvar(fig, "diagnosticos.png")

    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    for pool, cor in [(-1, "black"), (1, "0.5")]:
        sub = base[base.X2 == pool].groupby("X3").latencia_p99_ms.mean()
        ax.plot([4, 16], sub.values, "o-" if pool == -1 else "s--", color=cor,
                label=f"Pool: {20 if pool == -1 else 100} conexões")
    ax.set(xlabel="Workers", ylabel="Média de P99 simulado (ms)", title="Interação pool x workers (média sobre TTL, política e região)", xticks=[4, 16])
    ax.legend()
    salvar(fig, "interacao_pool_workers.png")

    efeitos = coef[coef.termo != "Intercept"].copy().sort_values("efeito_alto_menos_baixo", key=abs)
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.barh(efeitos.termo, efeitos.efeito_alto_menos_baixo,
            color="0.65", edgecolor="black", linewidth=.6)
    ax.errorbar(efeitos.efeito_alto_menos_baixo, efeitos.termo,
                xerr=2 * (efeitos.ic_superior - efeitos.coeficiente), fmt="none", color="black", capsize=3)
    ax.axvline(0, color="gray", lw=1)
    ax.set(xlabel=f"Efeito = 2 x coeficiente (ms); IC {(1-config.alfa)*100:.0f}%", title="Efeitos fatoriais e contraste regional Z")
    salvar(fig, "efeitos.png")

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    for regiao, cor in [("us-east-1", "black"), ("sa-east-1", "0.5")]:
        sub = ranking[ranking.regiao == regiao].sort_values(FATORES)
        x = np.arange(16) + (-.1 if regiao == "us-east-1" else .1)
        ax.errorbar(x, sub.media_ajustada_ms,
                    yerr=sub.ic_media_superior - sub.media_ajustada_ms,
                    fmt="o" if regiao == "us-east-1" else "s", capsize=3, label=regiao, color=cor)
    rotulos = ["".join("+" if v == 1 else "-" for v in linha) for linha in sub[FATORES].itertuples(index=False, name=None)]
    ax.set_xticks(np.arange(16), rotulos, rotation=45)
    ax.axhline(config.meta_ms, color="gray", ls="--", label=f"Meta: < {config.meta_ms:g} ms")
    ax.set(xlabel="Configuração codificada X1 X2 X3 X4", ylabel="P99 médio ajustado (ms)", title="Comparação por região com IC da média")
    ax.legend(ncol=3, fontsize=9)
    salvar(fig, "configuracoes.png")
