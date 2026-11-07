import pandas as pd
import pytest

from dcj.arquivos import carregar_obitos_brutos, listar_arquivos_por_padrao
from dcj.erros import ArquivosNaoEncontradosError, ColunasAusentesError
from dcj.limpeza import filtrar_janela_de_anos, filtrar_residentes_da_uf, limpar_internacoes, limpar_obitos, remover_duplicatas
from dados_sinteticos import gerar_dados_brutos


def test_filtrar_residentes_mantem_so_o_prefixo_da_uf():
    tabela = pd.DataFrame({"m": ["431490", "355030", None]})
    assert filtrar_residentes_da_uf(tabela, "m", "43")["m"].tolist() == ["431490"]


def test_remover_duplicatas_usa_so_as_colunas_indicadas():
    tabela = pd.DataFrame({"a": [1, 1, 2], "b": [9, 8, 7]})
    assert len(remover_duplicatas(tabela, ["a"])) == 2


def test_filtrar_janela_de_anos():
    tabela = pd.DataFrame({"d": pd.to_datetime(["2016-12-31", "2017-01-01", "2023-01-01"])})
    assert len(filtrar_janela_de_anos(tabela, "d", [2017, 2018])) == 1


def test_arquivo_consolidado_nunca_e_lido(tmp_path):
    gerar_dados_brutos(tmp_path)
    nomes = [caminho.name for caminho in listar_arquivos_por_padrao(tmp_path / "sim", r"sim_rs_\d{4}\.parquet")]
    assert "sim_rs_PRONTO_LINKAGE.parquet" not in nomes and "sim_rs_2017.parquet" in nomes


def test_pasta_sem_arquivos_levanta_erro_claro(configuracao):
    with pytest.raises(ArquivosNaoEncontradosError):
        carregar_obitos_brutos(configuracao)


def test_limpar_obitos_gera_funil_decrescente_e_sem_duplicatas(configuracao):
    gerar_dados_brutos(configuracao.pasta_raiz)
    obitos, funil = limpar_obitos(carregar_obitos_brutos(configuracao), configuracao)
    assert funil["registros"].is_monotonic_decreasing
    assert obitos["municipio"].str.startswith("43").all()
    assert not obitos["NUMERODO"].duplicated().any()
    assert obitos["data_obito"].dt.year.between(2017, 2022).all()


def test_limpar_internacoes_recodifica_sexo_e_remove_aih_repetida(configuracao):
    from dcj.arquivos import carregar_internacoes_brutas
    gerar_dados_brutos(configuracao.pasta_raiz)
    internacoes, _ = limpar_internacoes(carregar_internacoes_brutas(configuracao), configuracao)
    assert set(internacoes["sexo"].dropna()) == {"M", "F"}
    assert not internacoes["N_AIH"].duplicated().any()


def test_limpar_obitos_sem_coluna_obrigatoria_levanta_erro(configuracao):
    with pytest.raises(ColunasAusentesError):
        limpar_obitos(pd.DataFrame({"SEXO": ["1"]}), configuracao)
