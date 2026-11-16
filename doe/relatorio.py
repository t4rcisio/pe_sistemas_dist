"""Relatório acadêmico com linguagem direta e apresentação em preto e branco."""
from pathlib import Path
import json
import os
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

INSTITUICAO = "CENTRO FEDERAL DE EDUCAÇÃO TECNOLÓGICA DE MINAS GERAIS"
DISCIPLINA = "Tópicos Especiais em Sistemas Inteligentes: Planejamento de Experimentos em Computação"


def _fontes():
    pasta = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    if (pasta / "times.ttf").exists() and (pasta / "timesbd.ttf").exists():
        pdfmetrics.registerFont(TTFont("TimesProjeto", str(pasta / "times.ttf")))
        pdfmetrics.registerFont(TTFont("TimesProjeto-Bold", str(pasta / "timesbd.ttf")))
        pdfmetrics.registerFontFamily("TimesProjeto", normal="TimesProjeto", bold="TimesProjeto-Bold")
        return "TimesProjeto", "TimesProjeto-Bold"
    return "Times-Roman", "Times-Bold"


def gerar_relatorio(destino, config):
    destino = Path(destino)
    ler = lambda nome: pd.read_csv(destino / "tabelas" / f"{nome}.csv")
    coef, anova, blocos, testes, ranking = map(ler, ["coeficientes", "anova", "comparacao_blocos", "diagnosticos", "ranking"])
    resumo = json.loads((destino / "resumo.json").read_text(encoding="utf-8"))
    normal, negrito = _fontes()
    estilos = {
        "texto": ParagraphStyle("texto", fontName=normal, fontSize=12, leading=18,
                                alignment=TA_JUSTIFY, firstLineIndent=1.25*cm, spaceAfter=0),
        "secao": ParagraphStyle("secao", fontName=negrito, fontSize=12, leading=18,
                                spaceBefore=18, spaceAfter=18, keepWithNext=True),
        "titulo": ParagraphStyle("titulo", fontName=negrito, fontSize=12, leading=18,
                                 alignment=TA_CENTER, spaceAfter=18),
        "cabecalho": ParagraphStyle("cabecalho", fontName=normal, fontSize=12, leading=15,
                                    alignment=TA_CENTER, spaceAfter=9),
        "tabela": ParagraphStyle("tabela", fontName=normal, fontSize=10, leading=12, alignment=TA_LEFT),
        "rotulo": ParagraphStyle("rotulo", fontName=normal, fontSize=10, leading=12,
                                 spaceBefore=9, spaceAfter=5, keepWithNext=True),
        "fonte": ParagraphStyle("fonte", fontName=normal, fontSize=10, leading=12, spaceBefore=4, spaceAfter=9),
        "referencia": ParagraphStyle("referencia", fontName=normal, fontSize=12, leading=12,
                                     alignment=TA_LEFT, spaceAfter=12),
    }
    elementos = []

    def p(texto, estilo="texto"):
        elementos.append(Paragraph(texto, estilos[estilo]))

    def numero(valor, casas=2):
        return f"{valor:.{casas}f}".replace(".", ",")

    def prob(valor):
        if pd.isna(valor):
            return "-"
        return "< 0,001" if valor < .001 else numero(valor, 3)

    def tabela(titulo, colunas, linhas, larguras):
        cab = [Paragraph(f"<b>{escape(str(x))}</b>", estilos["tabela"]) for x in colunas]
        dados = [cab] + [[Paragraph(escape(str(x)), estilos["tabela"]) for x in linha] for linha in linhas]
        t = Table(dados, colWidths=[x*cm for x in larguras], repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEABOVE", (0, 0), (-1, 0), .7, colors.black),
            ("LINEBELOW", (0, 0), (-1, 0), .5, colors.black),
            ("LINEBELOW", (0, -1), (-1, -1), .7, colors.black),
        ]))
        elementos.append(KeepTogether([Paragraph(titulo, estilos["rotulo"]), t,
                                       Paragraph("Fonte: elaboração própria (2026).", estilos["fonte"])]))

    def figura(nome, titulo, largura=16*cm):
        img = Image(str(destino / "graficos" / nome))
        img.drawHeight *= largura / img.drawWidth
        img.drawWidth = largura
        elementos.append(KeepTogether([Paragraph(titulo, estilos["rotulo"]), img,
                                       Paragraph("Fonte: elaboração própria (2026).", estilos["fonte"])]))

    p(INSTITUICAO, "cabecalho")
    p(DISCIPLINA, "cabecalho")
    elementos.append(Spacer(1, .4*cm))
    p("ANÁLISE DA LATÊNCIA DE UMA PLATAFORMA DE E-COMMERCE", "titulo")
    p("Tarcísio Batista Prates", "cabecalho")
    p("1 INTRODUÇÃO", "secao")
    p("O tempo de resposta de uma loja virtual depende das configurações de cache, banco de dados "
      "e processamento. Este trabalho usa uma simulação para comparar essas configurações e identificar "
      "quais reduzem a latência P99. Essa medida indica o tempo que não é ultrapassado por 99% das "
      "requisições de um conjunto.")
    p(f"O objetivo é encontrar uma configuração com latência inferior a {numero(config.meta_ms, 0)} ms. "
      "O estudo segue o Projeto 5 do manual da disciplina e dá atenção à relação entre o número "
      "de conexões com o banco e o número de workers, que são as threads usadas no processamento.")
    p("2 PLANEJAMENTO DO EXPERIMENTO", "secao")
    p("Foram comparados quatro fatores, cada um com dois níveis. A região foi tratada como bloco, "
      "para separar sua influência dos efeitos das configurações. Os níveis são apresentados na Tabela 1.")
    tabela("Tabela 1 - Fatores e níveis do experimento", ["Fator", "Nível baixo (-1)", "Nível alto (+1)"], [
        ["X1: tempo do cache (TTL)", "15 segundos", "120 segundos"],
        ["X2: conexões com o banco", "20 conexões", "100 conexões"],
        ["X3: workers", "4 threads", "16 threads"],
        ["X4: política do cache", "LRU Volatile", "LFU Allkeys"],
        ["Z: região", "us-east-1 (Virgínia)", "sa-east-1 (São Paulo)"],
    ], [6, 5, 5])
    p(f"As 16 combinações foram repetidas {config.repeticoes} vezes em cada região, totalizando "
      f"{resumo['n_observacoes']} observações. A ordem foi sorteada dentro de cada região. "
      f"A semente {config.semente} permite reproduzir os mesmos dados em uma nova execução.")

    elementos.append(PageBreak())
    p("3 GERAÇÃO DOS DADOS", "secao")
    p("A latência foi calculada pela equação fornecida no manual da disciplina (Manual prático [...], s.d.). "
      "Os fatores X1 a X4 assumem os valores -1 ou +1. Para a região, Z vale -1 na Virgínia e +1 em São Paulo.")
    p("Y = 85 - 18 X1 - 12 X2 - 8 X3 + 14 X2 X3 + 15 Z + erro", "cabecalho")
    p(f"O erro foi sorteado de uma distribuição normal com média zero e desvio padrão de "
      f"{numero(config.sigma_ms)} ms. Cada observação representa uma medição simulada de P99. "
      "As diferenças entre regiões foram definidas pela equação e não resultam de medições na AWS.")
    p("4 COMPARAÇÃO ENTRE OS VALORES ESPERADOS E ESTIMADOS", "secao")
    p("A análise foi feita sem usar a coluna que guarda a resposta esperada. Depois, os valores "
      "estimados foram comparados aos da equação. A Tabela 2 apresenta os coeficientes, "
      "isto é, os valores que multiplicam cada termo no modelo.")
    tabela("Tabela 2 - Coeficientes da equação e da análise", ["Termo", "Esperado", "Estimado", "p-valor"],
           [[r.termo, numero(r.valor_teorico), numero(r.coeficiente), prob(r.p_valor)] for r in coef.itertuples()],
           [4, 4, 4, 4])
    p(f"Foi adotado o limite de {numero(config.alfa*100, 0)}% para avaliar os p-valores. "
      "Um valor abaixo desse limite sinaliza uma diferença que merece atenção, mas não garante "
      "que ela corresponda a um efeito real.")
    falsos = coef[(coef.termo != "Intercept") & (coef.p_valor < config.alfa) & (coef.valor_teorico == 0)]
    if not falsos.empty:
        p("Nesta execução, " + ", ".join(falsos.termo) + " apresentou esse sinal, embora tenha "
          "valor zero na equação original. É um falso positivo da amostra. Por isso, esse resultado "
          "não foi usado para atribuir uma vantagem à política de cache.")

    elementos.append(PageBreak())
    p("5 ANÁLISE DE VARIÂNCIA E EFEITO DA REGIÃO", "secao")
    p("A análise de variância (ANOVA) compara a variação associada aos fatores com a variação "
      "que permanece sem explicação. O modelo inclui os quatro fatores, as combinações entre "
      "pares de fatores e a região. A Tabela 3 reúne os resultados.")
    tabela("Tabela 3 - Análise de variância", ["Termo", "Soma de quadrados", "Graus de liberdade", "F", "p-valor"],
           [[r["termo"], numero(r["sum_sq"]), numero(r["df"], 0),
             numero(r["F"]) if pd.notna(r["F"]) else "-", prob(r["PR(>F)"])] for _, r in anova.iterrows()],
           [3, 4, 3, 3, 3])
    p("A soma de quadrados residual resume a variação que o modelo não explica. Para avaliar "
      "o bloqueamento, o mesmo modelo foi ajustado com e sem a região (Tabela 4).")
    tabela("Tabela 4 - Comparação dos modelos", ["Modelo", "Soma de quadrados residual", "Quadrado médio residual"],
           [["Com região" if r.modelo == "com_bloco" else "Sem região", numero(r.sq_residual), numero(r.qm_residual)]
            for r in blocos.itertuples()], [5, 5.5, 5.5])
    p(f"A inclusão da região reduziu essa variação em {numero(resumo['reducao_sq_residual_pct'])}%. "
      f"A diferença estimada entre São Paulo e Virgínia foi de {numero(resumo['diferenca_regional_ms'])} ms, "
      "próxima dos 30 ms definidos na simulação. Assim, o bloqueamento separou a diferença regional "
      "da variação atribuída às configurações.")

    elementos.append(PageBreak())
    p("6 RELAÇÃO ENTRE CONEXÕES E WORKERS", "secao")
    p("O efeito dos workers depende do número de conexões disponíveis. Isso pode ser observado "
      "na Figura 1: aumentar o número de threads produz resultados diferentes nos dois níveis do pool de conexões.")
    figura("interacao_pool_workers.png", "Figura 1 - Latência média por número de conexões e workers", 14*cm)
    p(f"Com 20 conexões, passar de 4 para 16 workers alterou a latência em "
      f"{numero(resumo['efeito_workers_pool_baixo_ms'])} ms. Com 100 conexões, a alteração foi de "
      f"{numero(resumo['efeito_workers_pool_alto_ms'])} ms. O primeiro caso representa uma redução; "
      "o segundo, um aumento. A equação prevê essa penalização quando ambos os fatores estão no nível alto.")
    p("O aumento do tempo de permanência no cache também reduziu a latência. Já a política "
      "de cache não altera a resposta esperada na equação. As pequenas diferenças entre políticas "
      "observadas nesta amostra são explicadas pela variação aleatória.")

    elementos.append(PageBreak())
    p("7 VERIFICAÇÃO DOS RESULTADOS", "secao")
    p("Os resíduos são as diferenças entre os valores observados e os calculados pelo modelo. "
      "Os gráficos da Figura 2 ajudam a verificar se há padrões que possam prejudicar a análise.")
    figura("diagnosticos.png", "Figura 2 - Verificação dos resíduos e da influência das observações", 13.5*cm)
    tabela("Tabela 5 - Testes de verificação", ["Teste", "Estatística", "p-valor"],
           [[r.teste, numero(r.estatistica, 3), prob(r.p_valor)] for r in testes.itertuples()], [8, 4, 4])
    nomes = {"Shapiro-Wilk": "normalidade dos erros", "Levene (Brown-Forsythe)": "igualdade das variâncias",
             "Falta de ajuste": "adequação do modelo"}
    sinais = testes[testes.p_valor < config.alfa]
    if sinais.empty:
        p("Os testes não apontaram problemas de normalidade, igualdade das variâncias ou falta de ajuste. "
          "Isso permite manter a análise proposta, mas não comprova que todos os pressupostos sejam atendidos.")
    else:
        p("Os testes sinalizaram a necessidade de examinar " + ", ".join(nomes[x] for x in sinais.teste) +
          ". Esses resultados devem ser considerados antes de usar as estimativas para tomar decisões.")
    p(f"O teste de Levene comparou 32 grupos, um para cada combinação de configuração e região, "
      f"com {config.repeticoes} observações por grupo. Grupos pequenos dificultam a identificação "
      "de diferenças. A medida de Cook também sinalizou "
      f"{resumo['observacoes_influentes']} observações para inspeção. Nenhuma delas foi retirada da base.")

    elementos.append(PageBreak())
    p("8 CONCLUSÃO", "secao")
    p("A configuração com menor latência estimada pode ser comparada entre regiões na Figura 3. "
      "As marcas mostram as médias ajustadas e os intervalos de confiança.")
    figura("configuracoes.png", "Figura 3 - Comparação das configurações nas duas regiões")
    for regiao, descricao in [("us-east-1", "Virgínia"), ("sa-east-1", "São Paulo")]:
        r = ranking[ranking.regiao == regiao].iloc[0]
        p(f"Na região de {descricao}, a menor média estimada foi de {numero(r.media_ajustada_ms)} ms, "
          f"com TTL de {r.ttl_s} segundos, {r.pool_conexoes} conexões e {r.workers} workers. "
          f"O intervalo de confiança de {(1-config.alfa)*100:.0f}% para essa média foi de "
          f"{numero(r.ic_media_inferior)} a {numero(r.ic_media_superior)} ms.")
    p("Na equação original, TTL de 120 segundos, 100 conexões e 4 workers produzem a menor "
      "latência nas duas regiões. As médias esperadas são de 34 ms na Virgínia e 64 ms em São Paulo, "
      "para ambas as políticas de cache. Portanto, entre os cenários previstos no manual, "
      "apenas a Virgínia permite atingir uma média inferior a 50 ms.")
    p("A principal conclusão é que aumentar os recursos de forma isolada pode piorar o resultado. "
      "O número de workers precisa ser escolhido junto com o pool de conexões. A diferença entre "
      "regiões também precisa ser considerada na análise.")
    p("Os resultados valem para a simulação. Uma média abaixo da meta não garante que toda "
      "medição futura ficará abaixo dela. A aplicação em um sistema real exige uma nova coleta. "
      "A etapa com AWS Lambda não foi executada, e o throughput não foi simulado porque o manual "
      "não fornece uma equação para essa resposta.")

    elementos.append(PageBreak())
    p("REFERÊNCIAS", "titulo")
    p("MANUAL prático de ensino superior &amp; pós-graduação: planejamento e análise de experimentos "
      "(DoE). [S. l.: s. n.], [s. d.]. Material da disciplina. Arquivo: Manual_Projetos_Pesquisa_DoE.pdf.", "referencia")
    p("PRATES, Tarcísio Batista. <b>Plano do trabalho final: planejamento de experimentos em sistemas "
      "distribuídos</b>. [S. l.], 2026. Documento de planejamento do projeto. "
      "Arquivo: plano_experimento_doe_lambda.md.", "referencia")

    def pagina(canvas, doc):
        canvas.setFillColor(colors.black)
        canvas.setFont(normal, 10)
        canvas.drawRightString(19*cm, 27.7*cm, str(doc.page))

    arquivo = destino / "relatorio.pdf"
    doc = SimpleDocTemplate(str(arquivo), pagesize=(21*cm, 29.7*cm), leftMargin=3*cm,
                            rightMargin=2*cm, topMargin=3*cm, bottomMargin=2*cm,
                            title="Análise da latência de uma plataforma de e-commerce",
                            author="Tarcísio Batista Prates")
    doc.build(elementos, onFirstPage=pagina, onLaterPages=pagina)
    return arquivo
