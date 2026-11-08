"""Regressões encontradas na validação do recorte RS (2017-2022)."""
import numpy as np
import pandas as pd

from conftest import criar_obitos_limpos
from dcj.cobertura import contar_dcj_fora_da_causa_basica
from dcj.colunas import Bruto, Col
from dcj.ingestao import manter_colunas_e_cids_de_interesse
from dcj.limpeza import marcar_dcj_na_declaracao
from dcj.permutacao_sinan import avaliar_cruzamento_sinan_contra_o_acaso_apenas_a810


def test_permutacao_a810_detecta_vinculos_mesmo_com_um_obito_a810_por_bloco(configuracao):
    # 5 municípios, cada um com 1 óbito A81.0 ligado a uma notificação e 20 óbitos por outras causas.
    linhas, notificacoes = [], []
    for posicao in range(5):
        municipio = f"43{posicao:04d}"
        linhas.append({Col.MUNICIPIO: municipio, Col.CAUSA_BASICA: "A810", Col.DATA_NASCIMENTO: "1950-01-01",
                       Col.DATA_OBITO: "2020-05-01"})
        linhas += [{Col.MUNICIPIO: municipio, Col.CAUSA_BASICA: "F03", Col.DATA_NASCIMENTO: f"{1920 + k}-01-01",
                    Col.DATA_OBITO: "2018-01-01"} for k in range(20)]
        notificacoes.append({Col.MUNICIPIO: municipio, Col.SEXO: "M", Col.ANO_NASCIMENTO: 1950,
                             Col.DATA_PRIMEIROS_SINTOMAS: pd.Timestamp("2020-01-01")})
    resultado = avaliar_cruzamento_sinan_contra_o_acaso_apenas_a810(
        pd.DataFrame(notificacoes), criar_obitos_limpos(*linhas), configuracao)
    final = resultado.iloc[-1]
    assert final["observado"] == 5 and final["media_ao_acaso"] < 1 and final["p_valor_unilateral"] < 0.01


def test_sim_mantem_todos_os_cids_genericos_do_escore(configuracao):
    causas = ["G309", "R54", "I64", "R99", "F03", "A810", "J189"]
    tabela = pd.DataFrame({Bruto.OBITO_CAUSA: causas})
    mantidos = manter_colunas_e_cids_de_interesse(
        tabela, (Bruto.OBITO_CAUSA,), [Bruto.OBITO_CAUSA], configuracao.cids_do_sim)
    assert mantidos[Bruto.OBITO_CAUSA].tolist() == causas[:-1]


def test_sim_mantem_obito_com_a810_so_em_causa_associada(configuracao):
    tabela = pd.DataFrame({Bruto.OBITO_CAUSA: ["J189", "J189"], "LINHAB": ["*A810", "*J449"]})
    mantidos = manter_colunas_e_cids_de_interesse(
        tabela, (Bruto.OBITO_CAUSA, "LINHAB"), [Bruto.OBITO_CAUSA, "LINHAB"], configuracao.cids_do_sim)
    assert mantidos["LINHAB"].tolist() == ["*A810"]


def test_marcacao_e_contagem_de_dcj_fora_da_causa_basica():
    brutos = pd.DataFrame({Bruto.OBITO_CAUSA: ["A810", "G309", "G309"],
                           "LINHAA": ["*A810", "*G309", "*G309"], "LINHAC": [None, "*A810", None]})
    assert marcar_dcj_na_declaracao(brutos).tolist() == [True, True, False]
    obitos = criar_obitos_limpos(*[{Col.DATA_NASCIMENTO: "1950-01-01", Col.DATA_OBITO: "2019-03-01",
                                    Col.CAUSA_BASICA: causa} for causa in brutos[Bruto.OBITO_CAUSA]])
    obitos[Col.DCJ_NA_DECLARACAO] = marcar_dcj_na_declaracao(brutos)
    linha = contar_dcj_fora_da_causa_basica(obitos).loc[2019]
    assert (linha["dcj_causa_basica"], linha["dcj_so_em_causa_associada"]) == (1, 1)
    assert linha["causas_basicas_dos_associados"] == "G309"


def test_parquet_antigo_sem_linhas_usa_so_a_causa_basica():
    assert marcar_dcj_na_declaracao(pd.DataFrame({Bruto.OBITO_CAUSA: ["A810", "F03"]})).tolist() == [True, False]