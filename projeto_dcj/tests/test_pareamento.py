import pandas as pd
import pytest

from conftest import criar_internacoes_limpas, criar_obitos_limpos
from dcj.colunas import Col
from dcj.erros import ColunasAusentesError
from dcj.pareamento import manter_um_para_um, montar_chave_de_pareamento, parear

NASCIMENTO = "1950-05-17"


def test_chave_inclui_municipio_apenas_quando_exigido():
    assert montar_chave_de_pareamento(True) == ["municipio", "sexo", "data_nascimento"]
    assert montar_chave_de_pareamento(False) == ["sexo", "data_nascimento"]


def test_pareia_mesma_pessoa_e_calcula_dias_ate_o_obito(configuracao):
    obitos = criar_obitos_limpos({Col.DATA_NASCIMENTO: NASCIMENTO, Col.DATA_OBITO: "2020-03-10"})
    internacoes = criar_internacoes_limpas({Col.DATA_NASCIMENTO: NASCIMENTO, Col.DATA_INTERNACAO: "2020-01-10"})
    resultado = parear(internacoes, obitos, configuracao)
    assert resultado.total_de_pares == 1
    assert resultado.pares[Col.DIAS_ATE_OBITO].iloc[0] == 60


def test_nao_pareia_internacao_posterior_ao_obito(configuracao):
    obitos = criar_obitos_limpos({Col.DATA_NASCIMENTO: NASCIMENTO, Col.DATA_OBITO: "2020-03-10"})
    internacoes = criar_internacoes_limpas({Col.DATA_NASCIMENTO: NASCIMENTO, Col.DATA_INTERNACAO: "2020-04-01"})
    resultado = parear(internacoes, obitos, configuracao)
    assert resultado.candidatos == 1 and resultado.total_de_pares == 0


@pytest.mark.parametrize("campo,valor", [(Col.SEXO, "F"), (Col.MUNICIPIO, "355030"),
                                          (Col.DATA_NASCIMENTO, "1950-05-18")])
def test_nao_pareia_quando_um_campo_da_chave_difere(configuracao, campo, valor):
    obitos = criar_obitos_limpos({Col.DATA_NASCIMENTO: NASCIMENTO, Col.DATA_OBITO: "2020-03-10"})
    internacoes = criar_internacoes_limpas({Col.DATA_NASCIMENTO: NASCIMENTO, Col.DATA_INTERNACAO: "2020-01-10", campo: valor})
    assert parear(internacoes, obitos, configuracao).total_de_pares == 0


def test_desempate_mantem_a_ultima_ou_a_primeira_internacao():
    pares = pd.DataFrame({Col.ID_OBITO: [0, 0], Col.ID_INTERNACAO: [0, 1],
                          Col.DATA_INTERNACAO: pd.to_datetime(["2020-01-01", "2020-02-01"])})
    assert manter_um_para_um(pares, "ultima")[Col.ID_INTERNACAO].tolist() == [1]
    assert manter_um_para_um(pares, "primeira")[Col.ID_INTERNACAO].tolist() == [0]


def test_cada_internacao_pareia_com_um_unico_obito():
    pares = pd.DataFrame({Col.ID_OBITO: [0, 1], Col.ID_INTERNACAO: [0, 0],
                          Col.DATA_INTERNACAO: pd.to_datetime(["2020-01-01", "2020-01-01"])})
    assert len(manter_um_para_um(pares, "ultima")) == 1


def test_chave_com_valor_nulo_nao_pareia(configuracao):
    obitos = criar_obitos_limpos({Col.DATA_NASCIMENTO: NASCIMENTO, Col.DATA_OBITO: "2020-03-10", Col.SEXO: None})
    internacoes = criar_internacoes_limpas({Col.DATA_NASCIMENTO: NASCIMENTO, Col.DATA_INTERNACAO: "2020-01-10", Col.SEXO: None})
    assert parear(internacoes, obitos, configuracao).total_de_pares == 0


def test_entrada_sem_colunas_obrigatorias_levanta_erro(configuracao):
    with pytest.raises(ColunasAusentesError):
        parear(pd.DataFrame({"x": [1]}), pd.DataFrame({"y": [1]}), configuracao)
