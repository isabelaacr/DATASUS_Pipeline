import pandas as pd

from dcj.funil import Funil


def test_funil_registra_percentuais_e_remocoes():
    funil = Funil()
    funil.registrar("bruto", pd.DataFrame({"x": range(10)}))
    funil.aplicar("metade", pd.DataFrame({"x": range(10)}), lambda tabela: tabela.head(5))
    tabela = funil.como_tabela()
    assert tabela["registros"].tolist() == [10, 5]
    assert tabela["percentual_do_bruto"].tolist() == [100.0, 50.0]
    assert tabela["removidos_na_etapa"].tolist() == [0, 5]


def test_funil_vazio_nao_quebra_com_base_zerada():
    funil = Funil()
    funil.registrar("bruto", pd.DataFrame({"x": []}))
    assert funil.como_tabela()["percentual_do_bruto"].tolist() == [0.0]
