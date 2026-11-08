import numpy as np
import pandas as pd

from conftest import criar_obitos_limpos
from dcj.colunas import Col
from dcj.permutacao_sinan import (
    avaliar_cruzamento_sinan_contra_o_acaso, contar_etapas_do_cruzamento, embaralhar_dentro_do_bloco)
from dcj.sinan import (
    listar_individuos_do_cruzamento, manter_obitos_na_janela_de_sobrevida, resumir_perfil_dos_individuos)


def criar_cruzados(*dias_ate_o_obito: int) -> pd.DataFrame:
    sintomas = pd.Timestamp("2020-01-01")
    return pd.DataFrame({
        Col.ANO_NASCIMENTO: range(1940, 1940 + len(dias_ate_o_obito)), Col.SEXO: "F", Col.MUNICIPIO: "431490",
        Col.DATA_PRIMEIROS_SINTOMAS: sintomas,
        Col.DATA_OBITO: [sintomas + np.timedelta64(int(dias), "D") for dias in dias_ate_o_obito],        Col.CAUSA_BASICA: "G311", Col.IDADE_ANOS: 80.0})


def test_embaralhar_preserva_o_conjunto_de_valores_de_cada_bloco():
    valores = np.array([10, 20, 30, 40, 50, 60])
    blocos = np.array([0, 1, 0, 1, 0, 1])
    resultado = embaralhar_dentro_do_bloco(valores, blocos, np.random.default_rng(1))
    assert sorted(resultado[blocos == 0]) == [10, 30, 50] and sorted(resultado[blocos == 1]) == [20, 40, 60]


def test_janela_de_sobrevida_descarta_obito_apos_um_ano():
    assert len(manter_obitos_na_janela_de_sobrevida(criar_cruzados(30, 400))) == 1


def test_individuos_unicos_colapsa_notificacoes_duplicadas_do_mesmo_obito():
    cruzados = pd.concat([criar_cruzados(30), criar_cruzados(30)], ignore_index=True)
    assert len(listar_individuos_do_cruzamento(cruzados)) == 1


def test_perfil_resume_idade_sexo_e_causa():
    perfil = resumir_perfil_dos_individuos(criar_cruzados(30, 60))["valor"]
    assert perfil["individuos_unicos"] == 2 and perfil["sexo_F"] == 2 and perfil["causa_G311"] == 2
    assert perfil["idade_mediana_ao_obito"] == 80.0


def test_permutacao_sinan_distingue_vinculo_temporal_coerente_de_colisao(configuracao):
    nascimentos = [f"19{40 + indice}-05-05" for indice in range(30)]
    obitos = criar_obitos_limpos(*[
        {Col.DATA_NASCIMENTO: nascimento, Col.DATA_OBITO: "2020-02-01", Col.SEXO: "F"} for nascimento in nascimentos])
    obitos[Col.ANO_NASCIMENTO] = range(1940, 1970)
    obitos[Col.DATA_OBITO] = pd.to_datetime("2020-02-01") + pd.to_timedelta(np.arange(30) * 200, unit="D")
    notificacoes = pd.DataFrame({Col.ANO_NASCIMENTO: [1940, 1941], Col.SEXO: "F", Col.MUNICIPIO: "431490",
                                 Col.DATA_PRIMEIROS_SINTOMAS: pd.to_datetime("2020-01-01")})
    assert contar_etapas_do_cruzamento(notificacoes, obitos) == (2, 2, 2, 2)
    resultado = avaliar_cruzamento_sinan_contra_o_acaso(notificacoes, obitos, configuracao)
    assert resultado.loc[0, "p_valor_unilateral"] == 1.0
    assert resultado.loc[2, "media_ao_acaso"] < resultado.loc[2, "observado"]
