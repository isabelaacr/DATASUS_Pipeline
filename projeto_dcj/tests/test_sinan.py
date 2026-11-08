import pandas as pd
import pytest

from conftest import criar_internacoes_limpas, criar_obitos_limpos
from dcj.colunas import Col
from dcj.erros import ColunasAusentesError
from dcj.etapas import executar_sinan
from dcj.sinan import (
    cruzar_sinan_com_internacoes, cruzar_sinan_com_obitos, preparar_notificacoes,
    resumir_cruzamentos)


def criar_notificacoes_brutas(sintomas: str = "2020-03-01") -> pd.DataFrame:
    return pd.DataFrame({"ID_AGRAVO": ["A810"], "CS_SEXO": ["M"], "ID_MN_RESI": ["431490"],
                         "ANO_NASC": ["1950"], "DT_SIN_PRI": [sintomas]})


def test_preparar_notificacoes_monta_chave_e_descarta_sem_sintomas(configuracao):
    brutas = pd.concat([criar_notificacoes_brutas(), criar_notificacoes_brutas(None)], ignore_index=True)
    preparadas = preparar_notificacoes(brutas, configuracao)
    assert len(preparadas) == 1
    assert preparadas.loc[0, Col.SEXO] == "M" and preparadas.loc[0, Col.MUNICIPIO] == "431490"


def test_preparar_notificacoes_exige_coluna_de_sintomas(configuracao):
    with pytest.raises(ColunasAusentesError):
        preparar_notificacoes(criar_notificacoes_brutas().drop(columns="DT_SIN_PRI"), configuracao)


def test_obito_antes_dos_sintomas_e_descartado(configuracao):
    notificacoes = preparar_notificacoes(criar_notificacoes_brutas("2020-03-01"), configuracao)
    obitos = criar_obitos_limpos({Col.DATA_NASCIMENTO: "1950-05-05", Col.DATA_OBITO: "2020-02-01"},
                                 {Col.DATA_NASCIMENTO: "1950-06-06", Col.DATA_OBITO: "2020-04-01"})
    por_chave, validos = cruzar_sinan_com_obitos(notificacoes, obitos)
    assert len(por_chave) == 2 and len(validos) == 1


def test_internacao_aceita_margem_de_30_dias_antes_dos_sintomas(configuracao):
    notificacoes = preparar_notificacoes(criar_notificacoes_brutas("2020-03-01"), configuracao)
    internacoes = criar_internacoes_limpas({Col.DATA_NASCIMENTO: "1950-05-05", Col.DATA_INTERNACAO: "2020-02-05"},
                                           {Col.DATA_NASCIMENTO: "1950-05-05", Col.DATA_INTERNACAO: "2020-01-20"})
    por_chave, validos = cruzar_sinan_com_internacoes(notificacoes, internacoes)
    assert len(por_chave) == 2 and len(validos) == 1


def test_resumo_conta_cada_etapa_do_cruzamento(configuracao):
    notificacoes = preparar_notificacoes(criar_notificacoes_brutas(), configuracao)
    vazio_obitos = cruzar_sinan_com_obitos(notificacoes, criar_obitos_limpos(
        {Col.DATA_NASCIMENTO: "1960-01-01", Col.DATA_OBITO: "2020-04-01"}))
    vazio_internacoes = cruzar_sinan_com_internacoes(notificacoes, criar_internacoes_limpas(
        {Col.DATA_NASCIMENTO: "1960-01-01", Col.DATA_INTERNACAO: "2020-04-01"}))
    resumo = resumir_cruzamentos(5, notificacoes, vazio_obitos, vazio_internacoes)["valor"]
    assert resumo["notificacoes_brutas"] == 5 and resumo["notificacoes_a81_com_chave_e_sintomas"] == 1 and resumo["sinan_x_sim_por_chave"] == 0


def test_etapa_sinan_sem_arquivo_e_ignorada_com_aviso(configuracao, caplog):
    executar_sinan(configuracao)
    assert "sinan_AAAA" in caplog.text


def test_etapa_sinan_gera_resumo_e_pares_validos(configuracao):
    obitos = criar_obitos_limpos({Col.DATA_NASCIMENTO: "1950-05-05", Col.DATA_OBITO: "2020-04-01"})
    internacoes = criar_internacoes_limpas({Col.DATA_NASCIMENTO: "1950-05-05", Col.DATA_INTERNACAO: "2020-03-10"})
    configuracao.arquivo_processado("obitos_limpos").parent.mkdir(parents=True, exist_ok=True)
    obitos.to_parquet(configuracao.arquivo_processado("obitos_limpos"))
    internacoes.to_parquet(configuracao.arquivo_processado("internacoes_limpas"))
    configuracao.pasta_do_sinan.mkdir(parents=True, exist_ok=True)
    criar_notificacoes_brutas().to_parquet(configuracao.pasta_do_sinan / "sinan_rs_2020.parquet")
    executar_sinan(configuracao)
    resumo = pd.read_csv(configuracao.arquivo_de_resultado("sinan_resumo"), index_col=0)["valor"]
    assert resumo["sinan_x_sim_validos"] == 1 and resumo["sinan_x_sih_validos"] == 1


def test_preparar_notificacoes_descarta_residentes_de_outras_ufs(configuracao):
    nacional = pd.concat([criar_notificacoes_brutas(), criar_notificacoes_brutas().assign(ID_MN_RESI="355030")],
                         ignore_index=True)
    preparadas = preparar_notificacoes(nacional, configuracao)
    assert preparadas[Col.MUNICIPIO].tolist() == ["431490"]


def test_preparar_notificacoes_leva_data_de_obito_e_classificacao_final(configuracao):
    brutas = criar_notificacoes_brutas().assign(DT_OBITO=["2020-05-01"], CLASSI_FIN=["1 "])
    preparadas = preparar_notificacoes(brutas, configuracao)
    assert preparadas.loc[0, Col.DATA_OBITO_NOTIFICADA] == pd.Timestamp("2020-05-01")
    assert preparadas.loc[0, Col.CLASSIFICACAO_FINAL] == "1"


def test_preparar_notificacoes_sem_colunas_opcionais_deixa_data_ausente(configuracao):
    preparadas = preparar_notificacoes(criar_notificacoes_brutas(), configuracao)
    assert preparadas[Col.DATA_OBITO_NOTIFICADA].isna().all() and preparadas[Col.CLASSIFICACAO_FINAL].isna().all()
