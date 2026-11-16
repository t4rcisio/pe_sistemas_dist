"""Delineamento e DGP. Nenhuma infraestrutura real é consultada."""
from dataclasses import dataclass, asdict
from itertools import product
import json
from pathlib import Path

import numpy as np
import pandas as pd

FATORES = ["X1", "X2", "X3", "X4"]
REGIOES = {"us-east-1": -15.0, "sa-east-1": 15.0}
NIVEIS = {
    "X1": ("ttl_s", { -1: 15, 1: 120}),
    "X2": ("pool_conexoes", {-1: 20, 1: 100}),
    "X3": ("workers", {-1: 4, 1: 16}),
    "X4": ("eviccao", {-1: "LRU Volatile", 1: "LFU Allkeys"}),
}


@dataclass(frozen=True)
class Config:
    semente: int = 2026
    repeticoes: int = 3
    sigma_ms: float = 3.0
    alfa: float = 0.05
    meta_ms: float = 50.0

    def __post_init__(self):
        if type(self.semente) is not int or self.semente < 0:
            raise ValueError("A semente deve ser um inteiro não negativo.")
        if type(self.repeticoes) is not int or self.repeticoes < 2:
            raise ValueError("Use pelo menos duas repetições para estimar o erro puro.")
        if not np.isfinite(self.sigma_ms) or self.sigma_ms <= 0:
            raise ValueError("sigma_ms deve ser positivo e finito.")
        if not 0 < self.alfa < 1:
            raise ValueError("alfa deve estar entre zero e um.")
        if not np.isfinite(self.meta_ms) or self.meta_ms <= 0:
            raise ValueError("meta_ms deve ser positiva e finita.")

    @classmethod
    def carregar(cls, caminho):
        return cls(**json.loads(Path(caminho).read_text(encoding="utf-8")))

    def salvar(self, caminho):
        Path(caminho).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def media_teorica(dados):
    """Média de uma medição de P99, e não um percentil de requisições geradas."""
    return (85 - 18 * dados.X1 - 12 * dados.X2 - 8 * dados.X3
            + 14 * dados.X2 * dados.X3 + dados.regiao.map(REGIOES))


def gerar(config=Config()):
    # Fluxos separados preservam a independência entre aleatorização e ruído.
    ordem_seed, ruido_seed = np.random.SeedSequence(config.semente).spawn(2)
    rng_ordem = np.random.default_rng(ordem_seed)
    rng_ruido = np.random.default_rng(ruido_seed)
    linhas = []
    for regiao in REGIOES:
        bloco = []
        for repeticao in range(1, config.repeticoes + 1):
            for niveis in product((-1, 1), repeat=4):
                bloco.append(dict(zip(FATORES, niveis), regiao=regiao,
                                  repeticao=repeticao))
        # As réplicas são independentes; a ordem é aleatória dentro da região.
        linhas.extend(bloco[i] for i in rng_ordem.permutation(len(bloco)))
    dados = pd.DataFrame(linhas)
    dados.insert(0, "ordem", np.arange(1, len(dados) + 1))
    dados.insert(1, "id_execucao", [f"SIM-{i:04d}" for i in dados.ordem])
    for fator, (coluna, niveis) in NIVEIS.items():
        dados[coluna] = dados[fator].map(niveis)
    dados["media_teorica_ms"] = media_teorica(dados)
    dados["erro_ms"] = rng_ruido.normal(0, config.sigma_ms, len(dados))
    dados["latencia_p99_ms"] = dados.media_teorica_ms + dados.erro_ms
    return dados


def validar(dados, config):
    obrigatorias = FATORES + ["regiao", "repeticao", "ordem", "latencia_p99_ms"]
    faltando = set(obrigatorias) - set(dados.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes: {sorted(faltando)}")
    if dados[obrigatorias].isna().any().any():
        raise ValueError("A base contém valores ausentes.")
    if not np.isfinite(dados.latencia_p99_ms).all():
        raise ValueError("A resposta contém valores não finitos.")
    if set(dados.regiao) != set(REGIOES):
        raise ValueError("A base deve conter exatamente as duas regiões previstas.")
    if not dados[FATORES].isin([-1, 1]).all().all():
        raise ValueError("Os níveis codificados devem ser -1 ou +1.")
    if len(dados) != 32 * config.repeticoes:
        raise ValueError("Número de observações incompatível com a configuração.")
    grupos = dados.groupby(["regiao"] + FATORES)
    if len(grupos) != 32 or not (grupos.size() == config.repeticoes).all():
        raise ValueError("Matriz incompleta ou desbalanceada.")
    if not grupos.repeticao.apply(lambda x: set(x) == set(range(1, config.repeticoes + 1))).all():
        raise ValueError("Repetições ausentes ou duplicadas em uma célula.")
    if not dados.ordem.is_unique or set(dados.ordem) != set(range(1, len(dados) + 1)):
        raise ValueError("A ordem deve identificar todas as observações uma única vez.")
