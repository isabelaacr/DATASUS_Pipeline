"""Permutação do pareamento SIM x SIH para ver quanto do excesso de pares é vínculo real."""
from __future__ import annotations

import numpy as np
import pandas as pd

from dcj.colunas import Col
from dcj.configuracao import Configuracao
from dcj.pareamento import (
    adicionar_dias_ate_o_obito, manter_internacoes_antes_do_obito, manter_um_para_um, preparar_lado)

ETAPAS_DO_PAREAMENTO = ("bloco + dia/mês iguais", "+ internação <= óbito", "+ 1:1 (pares finais)")
BLOCO_DO_EMBARALHAMENTO = [Col.MUNICIPIO, Col.SEXO]


def contar_etapas_do_pareamento(candidatos: pd.DataFrame, configuracao: Configuracao) -> tuple[int, int, int]:
    validos = manter_internacoes_antes_do_obito(candidatos)
    unicos = manter_um_para_um(validos, configuracao.criterio_de_desempate)
    return len(candidatos), len(validos), len(unicos)


def embaralhar_dentro_do_bloco(valores: np.ndarray, identificador_do_bloco: np.ndarray,
                               gerador: np.random.Generator) -> np.ndarray:
    ordem_original = np.argsort(identificador_do_bloco, kind="stable")
    ordem_sorteada = np.lexsort((gerador.random(len(valores)), identificador_do_bloco))
    embaralhados = np.empty_like(valores)
    embaralhados[ordem_original] = valores[ordem_sorteada]
    return embaralhados


def simular_pareamentos_ao_acaso(internacoes_preparadas: pd.DataFrame, obitos_preparados: pd.DataFrame,
                                 configuracao: Configuracao) -> np.ndarray:
    gerador = np.random.default_rng(configuracao.semente_aleatoria)
    chave = BLOCO_DO_EMBARALHAMENTO + [Col.DATA_NASCIMENTO]

    identificador = obitos_preparados.groupby(BLOCO_DO_EMBARALHAMENTO, sort=False).ngroup().to_numpy()
    datas = obitos_preparados[Col.DATA_NASCIMENTO].to_numpy()

    resultados = []
    for _ in range(configuracao.numero_de_permutacoes):
        datas_sorteadas = embaralhar_dentro_do_bloco(datas, identificador, gerador)
        obitos_sorteados = obitos_preparados.assign(**{Col.DATA_NASCIMENTO: datas_sorteadas})
        candidatos = internacoes_preparadas.merge(obitos_sorteados, on=chave, how="inner")
        candidatos = adicionar_dias_ate_o_obito(candidatos)
        resultados.append(contar_etapas_do_pareamento(candidatos, configuracao))
    return np.array(resultados)


def resumir_permutacao(observado: tuple[int, ...], simuladas: np.ndarray, nomes_das_etapas: tuple[str, ...]) -> pd.DataFrame:
    linhas = []
    for posicao, nome in enumerate(nomes_das_etapas):
        linhas.append({
            "etapa": nome, "observado": observado[posicao],
            "media_ao_acaso": round(float(simuladas[:, posicao].mean()), 2),
            "percentil_95_ao_acaso": int(np.percentile(simuladas[:, posicao], 95)),
            "excesso": round(observado[posicao] - simuladas[:, posicao].mean(), 2),
            "p_valor_unilateral": round((1 + int((simuladas[:, posicao] >= observado[posicao]).sum())) / (1 + simuladas.shape[0]), 4),
        })
    return pd.DataFrame(linhas)


def avaliar_pareamento_contra_o_acaso(internacoes: pd.DataFrame, obitos: pd.DataFrame,
                                      configuracao: Configuracao) -> pd.DataFrame:
    chave = [Col.MUNICIPIO, Col.SEXO, Col.DATA_NASCIMENTO]
    internacoes_preparadas = preparar_lado(internacoes, chave, Col.ID_INTERNACAO)
    obitos_preparados = preparar_lado(obitos, chave, Col.ID_OBITO)

    candidatos = internacoes_preparadas.merge(obitos_preparados, on=chave, how="inner")
    if candidatos.empty:
        return pd.DataFrame()

    candidatos = adicionar_dias_ate_o_obito(candidatos)
    observado = contar_etapas_do_pareamento(candidatos, configuracao)
    simuladas = simular_pareamentos_ao_acaso(internacoes_preparadas, obitos_preparados, configuracao)
    return resumir_permutacao(observado, simuladas, ETAPAS_DO_PAREAMENTO)