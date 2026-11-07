import pandas as pd
import pytest

from conftest import criar_obitos_limpos
from dcj.cobertura import comparar_obitos_por_dcj_com_esperado
from dcj.colunas import Col
from dcj.escore import comparar_faixas_etarias, montar_cenarios_de_faixa_etaria
from dcj.referencias import REFERENCIA_DO_BOLETIM, calcular_obitos_esperados_por_ano


def criar_pares(*idades: float) -> pd.DataFrame:
    quantidade = len(idades)
    return pd.DataFrame({Col.DIAS_ATE_OBITO: [100] * quantidade, Col.IDADE_ANOS: list(idades),
                         Col.CAUSA_BASICA: ["A810"] * quantidade,
                         Col.DATA_OBITO: pd.to_datetime(["2020-06-01"] * quantidade)})


def test_esperado_para_populacao_de_11_milhoes():
    assert calcular_obitos_esperados_por_ano(11_000_000) == (11.0, 22.0)


@pytest.mark.parametrize("populacao", [0, -5])
def test_esperado_rejeita_populacao_nao_positiva(populacao):
    with pytest.raises(ValueError):
        calcular_obitos_esperados_por_ano(populacao)


def test_referencia_do_boletim_guarda_os_valores_citados():
    assert REFERENCIA_DO_BOLETIM.faixa_etaria_de_maior_notificacao == (55, 74)
    assert REFERENCIA_DO_BOLETIM.mortes_por_milhao_por_ano == (1.0, 2.0)


def test_cenarios_incluem_faixa_configurada_boletim_e_sem_restricao(configuracao):
    cenarios = montar_cenarios_de_faixa_etaria(configuracao)
    assert cenarios["configurada"] == configuracao.regras_do_escore.faixa_etaria_em_anos
    assert cenarios["pico_de_notificacoes_do_boletim"] == (55, 74)
    assert cenarios["sem_restricao_de_idade"] == (0, 120)


def test_faixas_etarias_mudam_so_o_numero_de_sinalizados(configuracao):
    resultado = comparar_faixas_etarias(criar_pares(40, 70, 80), configuracao).set_index("cenario")
    assert resultado["pares"].nunique() == 1
    assert resultado.loc["configurada", "sinalizados"] == 1
    assert resultado.loc["pico_de_notificacoes_do_boletim", "sinalizados"] == 1
    assert resultado.loc["sem_restricao_de_idade", "sinalizados"] == 3


def test_obitos_a810_abaixo_do_minimo_esperado():
    obitos = criar_obitos_limpos(
        {Col.DATA_NASCIMENTO: "1950-01-01", Col.DATA_OBITO: "2019-01-01", Col.CAUSA_BASICA: "A810"},
        {Col.DATA_NASCIMENTO: "1951-01-01", Col.DATA_OBITO: "2019-02-01", Col.CAUSA_BASICA: "G319"})
    tabela = comparar_obitos_por_dcj_com_esperado(obitos, 11_000_000)
    assert tabela.loc[2019, "obitos_a810_observados"] == 1
    assert bool(tabela.loc[2019, "abaixo_do_minimo_esperado"])
