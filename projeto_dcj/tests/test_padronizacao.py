import numpy as np
import pandas as pd

from dcj.padronizacao import (
    MAPA_SEXO_DAS_INTERNACOES, MAPA_SEXO_DOS_OBITOS, converter_data_aaaammdd, converter_data_ddmmaaaa,
    decodificar_idade_em_anos, limpar_texto_numerico, padronizar_cid, padronizar_codigo_municipio, padronizar_sexo)


def test_limpar_texto_numerico_remove_espacos_e_sufixo_decimal():
    assert limpar_texto_numerico(pd.Series([" 431490.0 ", "12"])).tolist() == ["431490", "12"]


def test_codigo_de_municipio_preserva_zeros_a_esquerda_e_corta_digitos():
    resultado = padronizar_codigo_municipio(pd.Series(["43149", "4314902"]), digitos=6)
    assert resultado.tolist() == ["043149", "431490"]


def test_sexo_feminino_e_2_no_sim_e_3_no_sih():
    assert padronizar_sexo(pd.Series(["2"]), MAPA_SEXO_DOS_OBITOS).tolist() == ["F"]
    assert padronizar_sexo(pd.Series(["3"]), MAPA_SEXO_DAS_INTERNACOES).tolist() == ["F"]
    assert pd.isna(padronizar_sexo(pd.Series(["3"]), MAPA_SEXO_DOS_OBITOS).iloc[0])


def test_sexo_ignorado_vira_nulo():
    assert pd.isna(padronizar_sexo(pd.Series(["0"]), MAPA_SEXO_DOS_OBITOS).iloc[0])


def test_data_ddmmaaaa_recupera_zero_a_esquerda_e_invalida_vira_nat():
    datas = converter_data_ddmmaaaa(pd.Series(["1012023", "99999999", None]))
    assert pd.isna(datas.iloc[1]) and pd.isna(datas.iloc[2])


def test_data_ddmmaaaa_com_oito_digitos():
    assert converter_data_ddmmaaaa(pd.Series(["28081963"])).iloc[0] == pd.Timestamp("1963-08-28")


def test_data_aaaammdd():
    assert converter_data_aaaammdd(pd.Series(["19630828"])).iloc[0] == pd.Timestamp("1963-08-28")


def test_data_ja_convertida_passa_direto():
    datas = pd.Series(pd.to_datetime(["2020-05-01"]))
    assert converter_data_aaaammdd(datas).equals(datas)


def test_idade_decodificada_em_anos_centenarios_e_menores_de_um_ano():
    idades = decodificar_idade_em_anos(pd.Series(["445", "512", "230", "999", None]))
    assert idades.iloc[:3].tolist() == [45.0, 112.0, 0.0]
    assert np.isnan(idades.iloc[3])


def test_cid_padronizado_sem_ponto_e_em_maiusculas():
    assert padronizar_cid(pd.Series([" g31.1 ", "A81.0"])).tolist() == ["G311", "A810"]
