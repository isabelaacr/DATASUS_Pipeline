import numpy as np
import pandas as pd

from dcj.colunas import Col
from dcj.concordancia import calcular_concordancia, calcular_kappa_de_cohen, tratar_f03_como_g31


def test_kappa_perfeito_e_kappa_indefinido_com_uma_categoria():
    assert calcular_kappa_de_cohen(["A", "B", "A"], ["A", "B", "A"]) == 1.0
    assert np.isnan(calcular_kappa_de_cohen(["A", "A"], ["A", "A"]))
    assert np.isnan(calcular_kappa_de_cohen([], []))


def test_f03_tratado_como_g31_so_no_prefixo():
    assert tratar_f03_como_g31(["F030", "G311", "F02"]) == ["G310", "G311", "F02"]


def test_concordancia_total_e_parcial():
    pares = pd.DataFrame({Col.DIAGNOSTICO_PRINCIPAL: ["G311", "F03", "G318"],
                          Col.CAUSA_BASICA: ["G311", "G311", "G319"]})
    resultado = calcular_concordancia(pares)
    assert resultado["concordancia_observada"] == round(1 / 3, 4)
    assert resultado["pares"] == 3.0


def test_kappa_exploratorio_agrupa_f03_e_g31():
    """Este teste falha se o agrupamento F03 -> G31 não for aplicado no prefixo de 3 dígitos."""
    # Cria 4 pares: 2 com F03 no diagnóstico e G31 na causa (devem ser agrupados)
    # e 2 com códigos que não se cruzam em 3 dígitos.
    pares = pd.DataFrame({
        Col.DIAGNOSTICO_PRINCIPAL: ["F03", "F031", "G318", "G311"],
        Col.CAUSA_BASICA:          ["G31", "G311", "G319", "G319"]
    })
    resultado = calcular_concordancia(pares)
    
    # Com agrupamento, F03 vira G31 e F031 vira G31.
    # Então a concordância em 3 dígitos fica altíssima.
    # Se o agrupamento falhar, o kappa exploratório será igual ao de 4 dígitos.
    assert resultado["kappa_exploratorio_f03_igual_g31"] > resultado["kappa_4_digitos"]