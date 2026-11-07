"""Escore de suspeição de DCJ (0-100): heurística de triagem para revisão clínica, não diagnóstico."""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

from dcj.colunas import Col
from dcj.configuracao import (
    ROTULO_FORA_DA_JANELA, ROTULO_PANDEMIA, ROTULO_PRE_PANDEMIA, Configuracao, RegrasDoEscore)
from dcj.erros import garantir_colunas
from dcj.pareamento import parear
from dcj.referencias import IDADE_MAXIMA_PLAUSIVEL, REFERENCIA_DO_BOLETIM

Z_DE_95_POR_CENTO = 1.96


def pontuar_declinio_rapido(dias_ate_o_obito: pd.Series, regras: RegrasDoEscore) -> np.ndarray:
    dentro_da_janela = dias_ate_o_obito.between(*regras.janela_do_declinio_em_dias)
    return np.where(dentro_da_janela, regras.pontos_declinio_rapido, 0)


def pontuar_faixa_etaria(idades_em_anos: pd.Series, regras: RegrasDoEscore) -> np.ndarray:
    dentro_da_faixa = idades_em_anos.between(*regras.faixa_etaria_em_anos)
    return np.where(dentro_da_faixa, regras.pontos_faixa_etaria, 0)


def pontuar_cid_generico(causas_basicas: pd.Series, regras: RegrasDoEscore) -> np.ndarray:
    comeca_com_cid_generico = causas_basicas.str.startswith(regras.cids_genericos).fillna(False)
    return np.where(comeca_com_cid_generico.to_numpy(dtype=bool), regras.pontos_cid_generico, 0)


def classificar_periodo(datas_do_obito: pd.Series, configuracao: Configuracao) -> np.ndarray:
    anos = datas_do_obito.dt.year
    return np.select([anos.isin(configuracao.periodo_pre_pandemia), anos.isin(configuracao.periodo_pandemia)],
                     [ROTULO_PRE_PANDEMIA, ROTULO_PANDEMIA], default=ROTULO_FORA_DA_JANELA)


def calcular_escore(pares: pd.DataFrame, configuracao: Configuracao) -> pd.DataFrame:
    garantir_colunas(pares, [Col.DIAS_ATE_OBITO, Col.IDADE_ANOS, Col.CAUSA_BASICA, Col.DATA_OBITO], "pares")
    regras = configuracao.regras_do_escore
    pontuados = pares.assign(**{
        Col.PONTOS_DECLINIO: pontuar_declinio_rapido(pares[Col.DIAS_ATE_OBITO], regras),
        Col.PONTOS_IDADE: pontuar_faixa_etaria(pares[Col.IDADE_ANOS], regras),
        Col.PONTOS_CID: pontuar_cid_generico(pares[Col.CAUSA_BASICA], regras),
        Col.PERIODO: classificar_periodo(pares[Col.DATA_OBITO], configuracao),
    })
    pontuados[Col.ESCORE] = pontuados[[Col.PONTOS_DECLINIO, Col.PONTOS_IDADE, Col.PONTOS_CID]].sum(axis=1)
    pontuados[Col.SINALIZADO] = pontuados[Col.ESCORE] >= regras.limiar_de_sinalizacao
    return pontuados


def intervalo_de_wilson(sucessos: int, total: int) -> tuple[float, float]:
    """Intervalo de confiança de 95% em %, adequado a proporções com poucos casos."""
    if total == 0:
        return (np.nan, np.nan)
    proporcao, z_ao_quadrado = sucessos / total, Z_DE_95_POR_CENTO ** 2
    denominador = 1 + z_ao_quadrado / total
    centro = (proporcao + z_ao_quadrado / (2 * total)) / denominador
    margem = Z_DE_95_POR_CENTO * np.sqrt(proporcao * (1 - proporcao) / total + z_ao_quadrado / (4 * total ** 2)) / denominador
    return 100 * (centro - margem), 100 * (centro + margem)


def resumir_por_periodo(pares_com_escore: pd.DataFrame) -> pd.DataFrame:
    resumo = pares_com_escore.groupby(Col.PERIODO).agg(
        total_de_pares=(Col.ESCORE, "size"), escore_medio=(Col.ESCORE, "mean"), sinalizados=(Col.SINALIZADO, "sum"))
    resumo["taxa_percentual"] = (100 * resumo["sinalizados"] / resumo["total_de_pares"]).round(1)
    intervalos = [intervalo_de_wilson(int(casos), int(total)) for casos, total in zip(resumo["sinalizados"], resumo["total_de_pares"])]
    resumo["intervalo_de_confianca_95"] = [f"{baixo:.1f}-{alto:.1f}" for baixo, alto in intervalos]
    return resumo


def p_valor_de_fisher_entre_periodos(pares_com_escore: pd.DataFrame) -> float:
    """NaN quando falta um dos períodos: o teste exige as duas colunas da tabela 2x2."""
    nos_periodos = pares_com_escore[pares_com_escore[Col.PERIODO].isin([ROTULO_PRE_PANDEMIA, ROTULO_PANDEMIA])]
    if nos_periodos[Col.PERIODO].nunique() < 2:
        return float("nan")
    tabela = pd.crosstab(nos_periodos[Col.PERIODO], nos_periodos[Col.SINALIZADO])
    return float(fisher_exact(tabela.reindex(columns=[False, True], fill_value=0).values)[1])


def calcular_taxa_normalizada(pares_com_escore: pd.DataFrame, internacoes: pd.DataFrame,
                              configuracao: Configuracao) -> pd.DataFrame:
    """Sinalizados por 100 internações elegíveis, pelo ano da internação, para comparar coberturas."""
    periodos = {ROTULO_PRE_PANDEMIA: configuracao.periodo_pre_pandemia, ROTULO_PANDEMIA: configuracao.periodo_pandemia}
    linhas = [_linha_da_taxa_normalizada(rotulo, anos, pares_com_escore, internacoes)
              for rotulo, anos in periodos.items()]
    return pd.DataFrame(linhas)


def _linha_da_taxa_normalizada(rotulo: str, anos: tuple[int, ...], pares: pd.DataFrame,
                               internacoes: pd.DataFrame) -> dict[str, object]:
    total_de_internacoes = int(internacoes[Col.DATA_INTERNACAO].dt.year.isin(anos).sum())
    sinalizados = int((pares[Col.SINALIZADO] & pares[Col.DATA_INTERNACAO].dt.year.isin(anos)).sum())
    taxa = round(100 * sinalizados / total_de_internacoes, 2) if total_de_internacoes else np.nan
    return {"periodo_da_internacao": rotulo, "internacoes": total_de_internacoes,
            "sinalizados": sinalizados, "por_100_internacoes": taxa}


def comparar_criterios_de_desempate(internacoes: pd.DataFrame, obitos: pd.DataFrame,
                                    configuracao: Configuracao) -> pd.DataFrame:
    linhas = []
    for criterio in ("ultima", "primeira"):
        pares = parear(internacoes, obitos, replace(configuracao, criterio_de_desempate=criterio)).pares
        pontuados = calcular_escore(pares, configuracao)
        linhas.append({"criterio_de_desempate": criterio, "pares": len(pontuados),
                       "sinalizados": int(pontuados[Col.SINALIZADO].sum()),
                       "mediana_de_dias_ate_o_obito": pontuados[Col.DIAS_ATE_OBITO].median()})
    return pd.DataFrame(linhas)


def montar_cenarios_de_faixa_etaria(configuracao: Configuracao) -> dict[str, tuple[int, int]]:
    """Ref.: Boletim DCJ, p. 18: 60,2% das notificações suspeitas têm 55 a 74 anos."""
    return {
        "configurada": configuracao.regras_do_escore.faixa_etaria_em_anos,
        "pico_de_notificacoes_do_boletim": REFERENCIA_DO_BOLETIM.faixa_etaria_de_maior_notificacao,
        "sem_restricao_de_idade": (0, IDADE_MAXIMA_PLAUSIVEL),
    }


def comparar_faixas_etarias(pares: pd.DataFrame, configuracao: Configuracao) -> pd.DataFrame:
    """O pareamento não depende da faixa: só o escore é recalculado sobre os mesmos pares."""
    linhas = []
    for nome, faixa in montar_cenarios_de_faixa_etaria(configuracao).items():
        regras = replace(configuracao.regras_do_escore, faixa_etaria_em_anos=faixa)
        pontuados = calcular_escore(pares, replace(configuracao, regras_do_escore=regras))
        linhas.append({"cenario": nome, "faixa_etaria": f"{faixa[0]}-{faixa[1]}", "pares": len(pontuados),
                       "sinalizados": int(pontuados[Col.SINALIZADO].sum())})
    return pd.DataFrame(linhas)
