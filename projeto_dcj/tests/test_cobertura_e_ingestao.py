import pandas as pd

from conftest import criar_internacoes_limpas, criar_obitos_limpos
from dcj.arquivos import carregar_obitos_brutos
from dcj.cobertura import auditar_obitos_brutos, calcular_cobertura_por_ano
from dcj.colunas import Col
from dcj.ingestao import baixar_notificacoes, baixar_obitos
from dados_sinteticos import gerar_dados_brutos


def test_auditoria_mostra_outras_ufs_e_duplicatas(configuracao):
    gerar_dados_brutos(configuracao.pasta_raiz)
    auditoria = auditar_obitos_brutos(carregar_obitos_brutos(configuracao), configuracao)
    assert auditoria["duplicatas_integrais"] >= 100
    assert auditoria["percentual_de_residentes_da_uf"] < 100
    assert "35" in auditoria["ufs_de_residencia_mais_comuns"]


def test_cobertura_por_ano_normaliza_pela_mediana():
    obitos = criar_obitos_limpos(*[{Col.DATA_NASCIMENTO: "1950-01-01", Col.DATA_OBITO: f"{ano}-05-01"}
                                    for ano in (2017, 2018, 2018, 2019, 2019, 2019)])
    internacoes = criar_internacoes_limpas({Col.DATA_NASCIMENTO: "1950-01-01", Col.DATA_INTERNACAO: "2017-01-01"})
    cobertura = calcular_cobertura_por_ano(obitos, internacoes)
    assert cobertura.loc[2018, "obitos_sobre_mediana"] == 1.0 and cobertura.loc[2019, "obitos_sobre_mediana"] == 1.5


def test_download_com_falha_e_registrado_sem_derrubar_o_pipeline(configuracao):
    def obter_com_falha(sigla_uf: str, ano: int) -> pd.DataFrame:
        raise ConnectionError("FTP fora do ar")
    falhas = baixar_obitos(configuracao, obter_com_falha)
    assert len(falhas) == len(configuracao.anos_dos_obitos) and "FTP" in falhas[0].motivo


def test_download_existente_nao_e_baixado_de_novo(configuracao):
    gerar_dados_brutos(configuracao.pasta_raiz)
    chamadas: list[int] = []
    baixar_obitos(configuracao, lambda sigla, ano: chamadas.append(ano) or pd.DataFrame())
    assert chamadas == []


def test_download_do_sinan_filtra_uf_e_agravo_e_grava_por_ano(configuracao):
    nacional = pd.DataFrame({"ID_AGRAVO": ["A810", "A810", "A809"], "ID_MN_RESI": ["431490", "355030", "431490"],
                             "CS_SEXO": ["M", "F", "M"], "DT_SIN_PRI": ["2020-01-01"] * 3, "OUTRA": [1, 2, 3]})
    falhas = baixar_notificacoes(configuracao, lambda ano: nacional)
    gravado = pd.read_parquet(configuracao.pasta_do_sinan / "sinan_rs_2017.parquet")
    assert falhas == [] and len(gravado) == 1 and "OUTRA" not in gravado.columns


def test_download_do_sinan_com_agravo_ausente_no_pysus_vira_falha(configuracao):
    def sem_agravo(ano: int) -> pd.DataFrame:
        raise ValueError("agravo não listado")
    falhas = baixar_notificacoes(configuracao, sem_agravo)
    assert len(falhas) == len(configuracao.anos_dos_obitos) and falhas[0].base == "SINAN"


def test_pysus_tenta_a_proxima_api_quando_a_primeira_e_incompativel():
    from dcj.fonte_pysus import executar_primeira_tentativa_valida

    def api_inexistente() -> pd.DataFrame:
        raise ImportError("sem módulo")
    resultado = executar_primeira_tentativa_valida({"a": api_inexistente, "b": lambda: pd.DataFrame({"x": [1]})})
    assert len(resultado) == 1


def test_pysus_sem_nenhuma_api_valida_lista_o_motivo_de_cada_tentativa():
    import pytest
    from dcj.fonte_pysus import executar_primeira_tentativa_valida

    def falha_a() -> pd.DataFrame:
        raise AttributeError("sem sim")
    with pytest.raises(ValueError, match="a: AttributeError"):
        executar_primeira_tentativa_valida({"a": falha_a})


def test_sonda_do_pysus_sempre_informa_a_versao():
    from dcj.fonte_pysus import descrever_pysus_instalado
    assert "versao" in descrever_pysus_instalado()


def test_obitos_usam_a_interface_por_namespace_do_pysus(monkeypatch):
    import sys
    import types
    from dcj.fonte_pysus import obter_obitos_do_pysus
    chamadas: list[dict] = []
    namespace = types.SimpleNamespace(sim=lambda **filtros: chamadas.append(filtros) or pd.DataFrame({"x": [1]}))
    monkeypatch.setitem(sys.modules, "pysus", types.SimpleNamespace(ftp=namespace))
    assert len(obter_obitos_do_pysus("RS", 2019)) == 1
    assert chamadas == [{"state": "RS", "year": 2019, "as_dataframe": True}]

def test_internacoes_caem_para_a_funcao_legada_quando_o_namespace_nao_existe(monkeypatch):
    import sys
    import types
    from dcj.fonte_pysus import obter_internacoes_do_pysus
    legado = types.SimpleNamespace(sih=lambda uf, ano, mes, as_dataframe: pd.DataFrame({"x": [uf, ano, mes]}))
    monkeypatch.setitem(sys.modules, "pysus", legado)
    assert len(obter_internacoes_do_pysus("RS", 2019, 3)) == 3


def test_resultado_que_nao_e_tabela_conta_como_api_incompativel():
    import pytest
    from dcj.fonte_pysus import executar_primeira_tentativa_valida
    with pytest.raises(ValueError, match="TypeError"):
        executar_primeira_tentativa_valida({"a": lambda: ["caminho.parquet"]})


def test_namespace_do_pysus_aceita_uf_ou_state(monkeypatch):
    import sys
    import types
    from dcj.fonte_pysus import obter_obitos_do_pysus

    def sim_so_com_uf(uf: str, year: int, as_dataframe: bool) -> pd.DataFrame:
        return pd.DataFrame({"SEXO": [uf]})
    monkeypatch.setitem(sys.modules, "pysus", types.SimpleNamespace(ftp=types.SimpleNamespace(sim=sim_so_com_uf)))
    assert obter_obitos_do_pysus("RS", 2019)["SEXO"].tolist() == ["RS"]
