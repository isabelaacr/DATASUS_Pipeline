"""Quantos pares finais o ACASO produziria? Embaralha o dia/mês de nascimento das internações
e aplica as mesmas travas do pareamento real, para comparar igual com igual."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
import pandas as pd

from dcj.colunas import Col
from dcj.configuracao import Configuracao, CriterioDeDesempate
from dcj.pareamento import manter_um_para_um, preparar_lado

ETAPAS = ("bloco + dia/mês iguais", "+ internação <= óbito", "+ 1:1 (pares finais)")
SUFIXO_DA_INTERNACAO, SUFIXO_DO_OBITO = "_internacao", "_obito"
COLUNA_INTERNACAO_ANTES_DO_OBITO = "internacao_antes_do_obito"


class ContagemPorEtapa(NamedTuple):
    com_mesmo_dia_e_mes: int
    apos_internacao_antes_do_obito: int
    pares_finais: int


@dataclass(frozen=True)
class CandidatosDoBloco:
    pares: pd.DataFrame
    dia_e_mes_das_internacoes: np.ndarray


def montar_bloco(exigir_mesmo_municipio: bool) -> list[str]:
    municipio = [Col.MUNICIPIO] if exigir_mesmo_municipio else []
    return municipio + [Col.SEXO, Col.ANO_NASCIMENTO]


def montar_candidatos_do_bloco(internacoes: pd.DataFrame, obitos: pd.DataFrame,
                               exigir_mesmo_municipio: bool) -> CandidatosDoBloco:
    bloco = montar_bloco(exigir_mesmo_municipio)
    chave_completa = bloco + [Col.MES_DIA_NASCIMENTO]
    do_lado_das_internacoes = preparar_lado(internacoes, chave_completa, Col.ID_INTERNACAO)
    do_lado_dos_obitos = preparar_lado(obitos, chave_completa, Col.ID_OBITO)
    pares = do_lado_das_internacoes[[Col.ID_INTERNACAO, Col.DATA_INTERNACAO, Col.MES_DIA_NASCIMENTO] + bloco].merge(
        do_lado_dos_obitos[[Col.ID_OBITO, Col.DATA_OBITO, Col.MES_DIA_NASCIMENTO] + bloco], on=bloco,
        suffixes=(SUFIXO_DA_INTERNACAO, SUFIXO_DO_OBITO))
    pares[COLUNA_INTERNACAO_ANTES_DO_OBITO] = (pares[Col.DATA_INTERNACAO] <= pares[Col.DATA_OBITO]).to_numpy()
    return CandidatosDoBloco(pares, do_lado_das_internacoes[Col.MES_DIA_NASCIMENTO].to_numpy(dtype=object))


def contar_etapas(candidatos: CandidatosDoBloco, dia_e_mes_das_internacoes: np.ndarray,
                  criterio_de_desempate: CriterioDeDesempate) -> ContagemPorEtapa:
    pares = candidatos.pares
    dia_e_mes_sorteado = dia_e_mes_das_internacoes[pares[Col.ID_INTERNACAO].to_numpy()]
    mesmo_dia_e_mes = dia_e_mes_sorteado == pares[Col.MES_DIA_NASCIMENTO + SUFIXO_DO_OBITO].to_numpy(dtype=object)
    validos = mesmo_dia_e_mes & pares[COLUNA_INTERNACAO_ANTES_DO_OBITO].to_numpy()
    unicos = manter_um_para_um(pares.loc[validos], criterio_de_desempate)
    return ContagemPorEtapa(int(mesmo_dia_e_mes.sum()), int(validos.sum()), len(unicos))


def simular_contagens_ao_acaso(candidatos: CandidatosDoBloco, configuracao: Configuracao) -> np.ndarray:
    gerador = np.random.default_rng(configuracao.semente_aleatoria)
    contagens = [contar_etapas(candidatos, gerador.permutation(candidatos.dia_e_mes_das_internacoes),
                               configuracao.criterio_de_desempate)
                 for _ in range(configuracao.numero_de_permutacoes)]
    return np.array(contagens)


def resumir_permutacao(observado: tuple[int, ...], simuladas: np.ndarray,
                       nomes_das_etapas: tuple[str, ...] = ETAPAS) -> pd.DataFrame:
    total = len(simuladas)
    linhas = [{
        "etapa": nome, "observado": observado[posicao],
        "media_ao_acaso": round(float(simuladas[:, posicao].mean()), 2),
        "percentil_95_ao_acaso": int(np.percentile(simuladas[:, posicao], 95)),
        "excesso": round(float(observado[posicao] - simuladas[:, posicao].mean()), 2),
        "p_valor_unilateral": round((1 + int((simuladas[:, posicao] >= observado[posicao]).sum())) / (1 + total), 4),
    } for posicao, nome in enumerate(nomes_das_etapas)]
    return pd.DataFrame(linhas)


def avaliar_pareamento_contra_o_acaso(internacoes: pd.DataFrame, obitos: pd.DataFrame, configuracao: Configuracao) -> pd.DataFrame:
    candidatos = montar_candidatos_do_bloco(internacoes, obitos, configuracao.exigir_mesmo_municipio)
    observado = contar_etapas(candidatos, candidatos.dia_e_mes_das_internacoes, configuracao.criterio_de_desempate)
    return resumir_permutacao(observado, simular_contagens_ao_acaso(candidatos, configuracao))

def avaliar_cruzamento_sinan_contra_o_acaso_apenas_a810(
    notificacoes: pd.DataFrame, obitos: pd.DataFrame, configuracao: Configuracao
) -> pd.DataFrame:
    """Versão corrigida: restringe a permutação aos óbitos A810."""
    obitos_a810 = obitos[obitos[Col.CAUSA_BASICA].str.startswith("A81", na=False)].copy()
    sorteaveis = preparar_obitos_para_o_sorteio(obitos_a810)
    observado = contar_etapas_do_cruzamento(notificacoes, sorteaveis)
    simuladas = simular_cruzamentos_ao_acaso(notificacoes, sorteaveis, configuracao)
    return resumir_permutacao(observado, simuladas, ETAPAS_DO_SINAN)