import pandas as pd
import pytest

from conftest import criar_obitos_limpos
from dcj.cenarios_de_captura import (
    contar_notificacoes_distintas, listar_cruzamentos_na_janela, manter_datas_de_obito_coerentes,
    montar_cenarios_de_captura, selecionar_obitos_por_dcj)
from dcj.colunas import Col


def criar_notificacoes(*linhas: dict) -> pd.DataFrame:
    padrao = {Col.SEXO: "M", Col.MUNICIPIO: "431490", Col.CLASSIFICACAO_FINAL: "1",
              Col.DATA_PRIMEIROS_SINTOMAS: "2020-01-01", Col.DATA_OBITO_NOTIFICADA: pd.NaT}
    tabela = pd.DataFrame([{**padrao, **linha} for linha in linhas])
    for coluna in (Col.DATA_PRIMEIROS_SINTOMAS, Col.DATA_OBITO_NOTIFICADA):
        tabela[coluna] = pd.to_datetime(tabela[coluna])
    return tabela


def criar_obitos(*linhas: dict) -> pd.DataFrame:
    return criar_obitos_limpos(*({Col.CAUSA_BASICA: "A810", **linha} for linha in linhas))


NASCIDO_EM_1950 = {Col.ANO_NASCIMENTO: 1950}
OBITO_DE_1950 = {Col.DATA_NASCIMENTO: "1950-05-05", Col.DATA_OBITO: "2020-03-01"}


def test_selecao_mantem_so_a810():
    obitos = criar_obitos(OBITO_DE_1950, {**OBITO_DE_1950, Col.CAUSA_BASICA: "G311"})
    assert len(selecionar_obitos_por_dcj(obitos)) == 1


def test_cruzamento_descarta_obito_antes_dos_sintomas_e_apos_um_ano():
    notificacoes = criar_notificacoes(NASCIDO_EM_1950)
    obitos = criar_obitos(OBITO_DE_1950, {**OBITO_DE_1950, Col.DATA_OBITO: "2019-12-01"},
                          {**OBITO_DE_1950, Col.DATA_OBITO: "2021-06-01"})
    assert len(listar_cruzamentos_na_janela(notificacoes, obitos)) == 1


def test_chave_forte_exige_data_de_obito_do_sinan_proxima():
    notificacoes = criar_notificacoes({**NASCIDO_EM_1950, Col.DATA_OBITO_NOTIFICADA: "2020-03-10"},
                                      {**NASCIDO_EM_1950, Col.MUNICIPIO: "431490", Col.DATA_OBITO_NOTIFICADA: "2020-08-01"},
                                      NASCIDO_EM_1950)
    cruzados = listar_cruzamentos_na_janela(notificacoes, criar_obitos(OBITO_DE_1950))
    assert contar_notificacoes_distintas(manter_datas_de_obito_coerentes(cruzados)) == 1
    assert contar_notificacoes_distintas(cruzados) == 3


def test_cenarios_trazem_forte_fraca_e_extrapolada_para_cada_recorte(configuracao):
    notificacoes = criar_notificacoes({**NASCIDO_EM_1950, Col.DATA_OBITO_NOTIFICADA: "2020-03-01"},
                                      {**NASCIDO_EM_1950, Col.CLASSIFICACAO_FINAL: "2"})
    cenarios = montar_cenarios_de_captura(notificacoes, criar_obitos(OBITO_DE_1950), configuracao)
    assert len(cenarios) == 6
    forte = cenarios["todas (2) | chave forte observada"]
    assert (forte.total_da_primeira, forte.total_da_segunda, forte.em_ambas) == (2, 1, 1)
    assert cenarios["CLASSI_FIN=1 (1) | chave forte observada"].total_da_primeira == 1


def test_sem_nenhuma_data_de_obito_nao_ha_cenario_extrapolado(configuracao):
    cenarios = montar_cenarios_de_captura(criar_notificacoes(NASCIDO_EM_1950), criar_obitos(OBITO_DE_1950), configuracao)
    assert not any("extrapolada" in nome for nome in cenarios)


def test_pares_nunca_excedem_o_total_de_obitos_a810(configuracao):
    notificacoes = criar_notificacoes(*[{**NASCIDO_EM_1950, Col.DATA_OBITO_NOTIFICADA: "2020-03-01"}] * 3)
    for listas in montar_cenarios_de_captura(notificacoes, criar_obitos(OBITO_DE_1950), configuracao).values():
        assert listas.em_ambas <= listas.total_da_segunda
