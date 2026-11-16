"""Entrada de linha de comando. Ex.: python executar.py --saida resultados."""
import argparse
import json
from pathlib import Path

import pandas as pd

from doe.simulacao import Config, gerar
from doe.analise import analisar
from doe.ambiente import coletar

RAIZ = Path(__file__).resolve().parent


def executar(config, destino, etapa="tudo", entrada=None):
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    arquivo_dados = Path(entrada) if entrada else destino / "dados_simulados.csv"
    if etapa in ("tudo", "gerar"):
        if entrada:
            raise ValueError("--entrada só pode ser usado com a etapa analisar.")
        dados = gerar(config)
        dados.to_csv(arquivo_dados, index=False, encoding="utf-8-sig")
        config.salvar(destino / "configuracao_utilizada.json")
    else:
        if not arquivo_dados.exists():
            raise ValueError(f"Base não encontrada: {arquivo_dados}. Execute primeiro a etapa gerar.")
        dados = pd.read_csv(arquivo_dados)
    # Registra o ambiente usado no experimento.
    ambiente = coletar()
    (destino / "ambiente.json").write_text(json.dumps(ambiente, ensure_ascii=False, indent=2), encoding="utf-8")
    if etapa != "gerar":
        resumo = analisar(dados, config, destino)
    else:
        resumo = {"n_observacoes": len(dados)}
    return resumo


def main():
    parser = argparse.ArgumentParser(description="DoE local: simulação, ANOVA e gráficos do Projeto 5.")
    parser.add_argument("etapa", nargs="?", choices=["tudo", "gerar", "analisar"], default="tudo")
    parser.add_argument("--config", type=Path, default=RAIZ / "configuracoes" / "simulacao.json")
    parser.add_argument("--saida", type=Path, default=RAIZ / "resultados")
    parser.add_argument("--entrada", type=Path, help="CSV para análise separada; exige configuração compatível.")
    args = parser.parse_args()
    try:
        resumo = executar(Config.carregar(args.config), args.saida, args.etapa, args.entrada)
    except (ValueError, OSError, TypeError) as erro:
        parser.exit(1, f"Erro: {erro}\n")
    print(f"Concluído: {resumo['n_observacoes']} observações. Saída: {args.saida.resolve()}")


if __name__ == "__main__":
    main()
