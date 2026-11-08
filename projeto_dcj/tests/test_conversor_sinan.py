import pandas as pd

from dcj import conversor_sinan
from dcj.conversor_sinan import (
    converter_pasta, padronizar_tabela, renomear_campos_duplicados, resolver_residencia_duplicada)
from dcj.fonte_pysus import _com_colunas_em_maiusculas


def criar_tabela_nacional() -> pd.DataFrame:
    return pd.DataFrame({"id_agravo": ["A810", "A810", "A819"], "id_mn_resi": ["431490", "355030", "431490"],
                         "cs_sexo": ["M", "F", "M"], "dt_sin_pri": [None, "2019-01-04", "2019-02-01"]})


def test_campos_duplicados_ganham_sufixo_a_partir_da_segunda_ocorrencia():
    assert renomear_campos_duplicados(["A", "B", "A", "A"]) == ["A", "B", "A_2", "A_3"]


def test_residencia_repetida_assume_a_segunda_ocorrencia():
    tabela = pd.DataFrame({"ID_MN_RESI": ["notificacao"], "ID_MN_RESI_2": ["residencia"]})
    assert resolver_residencia_duplicada(tabela)["ID_MN_RESI"].tolist() == ["residencia"]


def test_padronizar_tabela_poe_colunas_em_maiusculas_e_texto_como_string():
    padronizada = padronizar_tabela(criar_tabela_nacional())
    assert "ID_MN_RESI" in padronizada.columns
    assert not pd.api.types.is_object_dtype(padronizada["CS_SEXO"]) and pd.api.types.is_string_dtype(padronizada["CS_SEXO"])


def test_converter_pasta_grava_so_residentes_da_uf_e_agravo_a81(configuracao, monkeypatch):
    configuracao.pasta_do_sinan.mkdir(parents=True)
    (configuracao.pasta_do_sinan / "DCRJBR19.dbc").write_bytes(b"")
    monkeypatch.setattr(conversor_sinan, "converter_dbc_em_tabela", lambda caminho: criar_tabela_nacional())
    gravados = converter_pasta(configuracao)
    resultado = pd.read_parquet(configuracao.pasta_do_sinan / "sinan_rs_2019.parquet")
    assert [caminho.name for caminho in gravados] == ["sinan_rs_2019.parquet"]
    assert len(resultado) == 2 and set(resultado["ID_MN_RESI"]) == {"431490"}


def test_pysus_com_colunas_minusculas_e_normalizado():
    assert list(_com_colunas_em_maiusculas(pd.DataFrame({" causabas ": [1], "Sexo": [2]})).columns) == ["CAUSABAS", "SEXO"]
