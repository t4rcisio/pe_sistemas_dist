"""Verificações científicas do delineamento e da recuperação dos parâmetros."""
import unittest

import numpy as np
import pandas as pd

from doe.simulacao import Config, FATORES, gerar, media_teorica, validar
from doe.analise import VERDADE, ajustar


class ExperimentoTest(unittest.TestCase):
    def test_balanceamento_e_reproducao(self):
        dados = gerar()
        validar(dados, Config())
        self.assertEqual(len(dados), 96)
        self.assertTrue((dados.groupby(["regiao"] + FATORES).size() == 3).all())
        pd.testing.assert_frame_equal(dados, gerar())
        self.assertFalse(dados.latencia_p99_ms.equals(gerar(Config(semente=7)).latencia_p99_ms))

    def test_recupera_parametros_sem_ruido(self):
        dados = gerar()
        dados["latencia_p99_ms"] = media_teorica(dados)
        _, modelo, _ = ajustar(dados, Config())
        for termo, esperado in VERDADE.items():
            self.assertAlmostEqual(modelo.params[termo], esperado, places=10)
        self.assertAlmostEqual(modelo.params["X3"] * 2 - modelo.params["X2:X3"] * 2, -44)
        self.assertAlmostEqual(modelo.params["X3"] * 2 + modelo.params["X2:X3"] * 2, 12)

    def test_otimo_teorico_e_politica_nula(self):
        dados = gerar()
        for regiao, minimo in [("us-east-1", 34), ("sa-east-1", 64)]:
            sub = dados[dados.regiao == regiao]
            self.assertEqual(sub.media_teorica_ms.min(), minimo)
            melhores = sub[sub.media_teorica_ms == minimo]
            self.assertTrue((melhores.X1 == 1).all())
            self.assertTrue((melhores.X2 == 1).all())
            self.assertTrue((melhores.X3 == -1).all())
            self.assertEqual(set(melhores.X4), {-1, 1})

    def test_bloco_remove_variabilidade_e_intervalos_coerentes(self):
        base, modelo, sem_bloco = ajustar(gerar(), Config())
        self.assertLess(modelo.ssr, sem_bloco.ssr / 10)
        self.assertEqual(modelo.df_resid, 84)
        self.assertEqual(np.linalg.matrix_rank(modelo.model.exog), 12)
        pred = modelo.get_prediction(base).summary_frame()
        self.assertTrue((pred.obs_ci_upper > pred.mean_ci_upper).all())
        self.assertTrue((pred.obs_ci_lower < pred.mean_ci_lower).all())

    def test_nao_usa_verdade_no_ajuste(self):
        dados = gerar()
        _, original, _ = ajustar(dados, Config())
        dados = dados.drop(columns=["media_teorica_ms", "erro_ms"])
        _, cego, _ = ajustar(dados, Config())
        np.testing.assert_array_equal(original.params, cego.params)

    def test_rejeita_base_incompleta_e_config_invalida(self):
        with self.assertRaises(ValueError):
            validar(gerar().iloc[:-1], Config())
        dados = gerar()
        dados.loc[0, "X1"] = 0
        with self.assertRaises(ValueError):
            validar(dados, Config())
        for kwargs in [{"repeticoes": 1}, {"sigma_ms": -3}, {"alfa": 1}, {"semente": -1}]:
            with self.assertRaises(ValueError):
                Config(**kwargs)


if __name__ == "__main__":
    unittest.main()
