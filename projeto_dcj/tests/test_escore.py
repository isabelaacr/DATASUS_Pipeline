import numpy as np
import pandas as pd

from conftest import criar_internacoes_limpas
from dcj.colunas import Col
from dcj.configuracao import ROTULO_PANDEMIA, ROTULO_PRE_PANDEMIA, RegrasDoEscore
from dcj.escore import (
    calcular_escore, calcular_taxa_normalizada, intervalo_de_wilson, p_valor_de_fisher_entre_periodos,
    pontuar_cid_generico, pontuar_declinio_rapido, pontuar_faixa_etaria, resumir_por_periodo)

REGRAS = RegrasDoEscore()


def criar_pares(dias: int, idade: float, causa: str, data_obito: str = "2020-06-01") -> pd.DataFrame:
    return pd.DataFrame({Col.DIAS_ATE_OBITO: [dias], Col.IDADE_ANOS: [idade], Col.CAUSA_BASICA: [causa],
                         Col.DATA_OBITO: pd.to_datetime([data_obito]),
                         Col.DATA_INTERNACAO: pd.to_datetime([data_obito]) - pd.Timedelta(days=dias)})


def test_declinio_rapido_inclui_os_limites_da_janela():
    dias = pd.Series([-1, 0, 365, 366])
    assert pontuar_declinio_rapido(dias, REGRAS).tolist() == [0, 40, 40, 0]


def test_faixa_etaria_inclui_30_e_64():
    assert pontuar_faixa_etaria(pd.Series([29, 30, 64, 65, np.nan]), REGRAS).tolist() == [0, 30, 30, 0, 0]


def test_cid_generico_por_prefixo_e_nulo_nao_pontua():
    causas = pd.Series(["G319", "A810", "F03", None], dtype="string")
    assert pontuar_cid_generico(causas, REGRAS).tolist() == [30, 0, 30, 0]


def test_sinaliza_com_declinio_mais_idade_ou_cid(configuracao):
    so_declinio = calcular_escore(criar_pares(100, 80, "A810"), configuracao)
    declinio_e_idade = calcular_escore(criar_pares(100, 50, "A810"), configuracao)
    declinio_e_cid = calcular_escore(criar_pares(100, 80, "G319"), configuracao)
    tudo = calcular_escore(criar_pares(100, 50, "G319"), configuracao)
    assert [so_declinio, declinio_e_idade, declinio_e_cid, tudo][0][Col.SINALIZADO].iloc[0] is np.False_
    assert declinio_e_idade[Col.ESCORE].iloc[0] == 70 and declinio_e_idade[Col.SINALIZADO].iloc[0]
    assert declinio_e_cid[Col.SINALIZADO].iloc[0] and tudo[Col.ESCORE].iloc[0] == 100


def test_periodo_classificado_pelo_ano_do_obito(configuracao):
    antes = calcular_escore(criar_pares(10, 50, "G319", "2018-05-01"), configuracao)
    durante = calcular_escore(criar_pares(10, 50, "G319", "2021-05-01"), configuracao)
    assert antes[Col.PERIODO].iloc[0] == ROTULO_PRE_PANDEMIA and durante[Col.PERIODO].iloc[0] == ROTULO_PANDEMIA


def test_intervalo_de_wilson_conhecido_e_total_zero():
    baixo, alto = intervalo_de_wilson(5, 10)
    assert round(baixo, 1) == 23.7 and round(alto, 1) == 76.3
    assert np.isnan(intervalo_de_wilson(0, 0)[0])


def test_fisher_retorna_nan_sem_os_dois_periodos(configuracao):
    pontuado = calcular_escore(criar_pares(10, 50, "G319"), configuracao)
    assert np.isnan(p_valor_de_fisher_entre_periodos(pontuado))


def test_resumo_por_periodo_conta_sinalizados(configuracao):
    pares = pd.concat([criar_pares(10, 50, "G319", "2018-05-01"), criar_pares(900, 80, "A810", "2021-05-01")])
    resumo = resumir_por_periodo(calcular_escore(pares, configuracao))
    assert resumo.loc[ROTULO_PRE_PANDEMIA, "sinalizados"] == 1 and resumo.loc[ROTULO_PANDEMIA, "sinalizados"] == 0


def test_taxa_normalizada_divide_pelo_total_de_internacoes(configuracao):
    pares = calcular_escore(criar_pares(10, 50, "G319", "2018-05-01"), configuracao)
    internacoes = criar_internacoes_limpas(*[{Col.DATA_NASCIMENTO: "1950-01-01", Col.DATA_INTERNACAO: "2018-03-01"}] * 4)
    taxa = calcular_taxa_normalizada(pares, internacoes, configuracao)
    assert taxa.loc[0, "por_100_internacoes"] == 25.0 and np.isnan(taxa.loc[1, "por_100_internacoes"])
