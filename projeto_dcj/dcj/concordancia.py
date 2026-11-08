"""Concordância entre o diagnóstico da internação (SIH) e a causa básica do óbito (SIM).

Os dois campos medem coisas diferentes e não precisam concordar: baixa concordância não é
erro de código, é o fenômeno que o estudo investiga."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from dcj.colunas import Col

CID_DEMENCIA_NAO_ESPECIFICADA = "F03"
CID_DOENCA_DEGENERATIVA = "G31"
TAMANHO_DO_GRUPO_DE_CID = 3


def calcular_kappa_de_cohen(rotulos_a: list[str], rotulos_b: list[str]) -> float:
    """NaN quando o kappa é indefinido (por exemplo, uma única categoria em ambos os lados)."""
    categorias = sorted(set(rotulos_a) | set(rotulos_b))
    if len(rotulos_a) == 0 or len(categorias) < 2:
        return float("nan")
    return float(cohen_kappa_score(rotulos_a, rotulos_b, labels=categorias))


def calcular_concordancia_observada(rotulos_a: list[str], rotulos_b: list[str]) -> float:
    if not rotulos_a:
        return float("nan")
    return float(np.mean([rotulo_a == rotulo_b for rotulo_a, rotulo_b in zip(rotulos_a, rotulos_b)]))


def reduzir_ao_grupo(cids: list[str]) -> list[str]:
    return [cid[:TAMANHO_DO_GRUPO_DE_CID] for cid in cids]


def tratar_f03_como_g31(cids: list[str]) -> list[str]:
    return [CID_DOENCA_DEGENERATIVA + cid[TAMANHO_DO_GRUPO_DE_CID:] if cid.startswith(CID_DEMENCIA_NAO_ESPECIFICADA)
            else cid for cid in cids]


def calcular_concordancia(pares: pd.DataFrame) -> dict[str, float]:
    from sklearn.metrics import cohen_kappa_score

    diagnosticos = pares[Col.DIAGNOSTICO_PRINCIPAL].astype(str).tolist()
    causas = pares[Col.CAUSA_BASICA].astype(str).tolist()

    # 4 dígitos
    kappa_4 = cohen_kappa_score(diagnosticos, causas)
    concordancia_obs = calcular_concordancia_observada(diagnosticos, causas)

    # 3 dígitos padrão
    kappa_3 = cohen_kappa_score(reduzir_ao_grupo(diagnosticos), reduzir_ao_grupo(causas))

    # 3 dígitos com F03 -> G31 (CORRIGIDO: aplica no prefixo de 3 dígitos)
    cid_int_3_f03 = tratar_f03_como_g31(reduzir_ao_grupo(diagnosticos))
    cid_obt_3_f03 = tratar_f03_como_g31(reduzir_ao_grupo(causas))
    kappa_f03 = cohen_kappa_score(cid_int_3_f03, cid_obt_3_f03)

    return {
        "pares": float(len(pares)),
        "concordancia_observada": round(concordancia_obs, 4),
        "kappa_4_digitos": round(kappa_4, 4),
        "kappa_3_digitos": round(kappa_3, 4),
        "kappa_exploratorio_f03_igual_g31": round(kappa_f03, 4),
    }
