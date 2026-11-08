"""Cruzamentos EXPLORATÓRIOS do SINAN com o SIM e com o SIH.

Ref.: Boletim DCJ (dcj/referencias.py), p. 15, 17 e 21: 36,3% das notificações suspeitas ficam sem
classificação final e 55,8% sem evolução; há confirmados registrados como "cura". O campo não é confiável
para estimar proporções.
A chave (ano de nascimento, sexo, município) é fraca e gera colisões: os cruzamentos servem para listar
casos a revisar manualmente. Regras temporais: óbito >= primeiros sintomas; internação >= primeiros
sintomas menos 30 dias (as mesmas do notebook original)."""
from __future__ import annotations

import pandas as pd

from dcj.colunas import Bruto, Col
from dcj.configuracao import Configuracao
from dcj.erros import garantir_colunas
from dcj.padronizacao import limpar_texto_numerico, padronizar_sexo

# Nos dados do notebook original CS_SEXO só trouxe "M" e "F"; qualquer outro código (ex.: "I") é descartado.
MAPA_SEXO_DO_SINAN = {"M": "M", "F": "F"}
COLUNA_DE_SINTOMAS = Bruto.NOTIFICACAO_PRIMEIROS_SINTOMAS
CHAVE_DO_SINAN = [Col.ANO_NASCIMENTO, Col.SEXO, Col.MUNICIPIO]
MARGEM_DA_INTERNACAO_EM_DIAS = 30
# Sobrevida média da DCJ ~5 meses (Boletim DCJ, dcj/referencias.py): óbito mais de 1 ano após os sintomas é implausível.
JANELA_DE_SOBREVIDA_EM_DIAS = 365
COLUNAS_DO_OBITO_NO_CRUZAMENTO = [Col.DATA_OBITO, Col.CAUSA_BASICA, Col.IDADE_ANOS]
CHAVE_DO_INDIVIDUO = CHAVE_DO_SINAN + [Col.DATA_OBITO]


def extrair_ano_de_nascimento(notificacoes: pd.DataFrame) -> pd.Series:
    if Bruto.NOTIFICACAO_ANO_NASCIMENTO in notificacoes.columns:
        return pd.to_numeric(notificacoes[Bruto.NOTIFICACAO_ANO_NASCIMENTO], errors="coerce")
    return pd.to_datetime(notificacoes[Bruto.NOTIFICACAO_NASCIMENTO], errors="coerce").dt.year


def extrair_data_do_obito_notificada(notificacoes: pd.DataFrame) -> pd.Series:
    """Só 18 das 45 notificações do RS (2017-2022) trazem a data; ausência não significa que o paciente sobreviveu."""
    if Bruto.NOTIFICACAO_OBITO not in notificacoes.columns:
        return pd.Series(pd.NaT, index=notificacoes.index, dtype="datetime64[ns]")
    return pd.to_datetime(notificacoes[Bruto.NOTIFICACAO_OBITO], errors="coerce")


def extrair_classificacao_final(notificacoes: pd.DataFrame) -> pd.Series:
    if Bruto.NOTIFICACAO_CLASSIFICACAO_FINAL not in notificacoes.columns:
        return pd.Series(pd.NA, index=notificacoes.index, dtype="string")
    return limpar_texto_numerico(notificacoes[Bruto.NOTIFICACAO_CLASSIFICACAO_FINAL])


def montar_chaves_do_sinan(notificacoes: pd.DataFrame, configuracao: Configuracao) -> pd.DataFrame:
    digitos = configuracao.digitos_do_municipio
    municipios = limpar_texto_numerico(notificacoes[Bruto.NOTIFICACAO_MUNICIPIO]).str.zfill(digitos).str[:digitos]
    return pd.DataFrame({
        Col.ANO_NASCIMENTO: extrair_ano_de_nascimento(notificacoes),
        Col.SEXO: padronizar_sexo(notificacoes[Bruto.NOTIFICACAO_SEXO], MAPA_SEXO_DO_SINAN),
        Col.MUNICIPIO: municipios,
    }).dropna()


def preparar_notificacoes(notificacoes: pd.DataFrame, configuracao: Configuracao) -> pd.DataFrame:
    garantir_colunas(notificacoes, [Bruto.NOTIFICACAO_SEXO, Bruto.NOTIFICACAO_MUNICIPIO, COLUNA_DE_SINTOMAS], "SINAN")
    com_indice_unico = notificacoes.reset_index(drop=True)
    preparadas = montar_chaves_do_sinan(com_indice_unico, configuracao).assign(
        **{Col.DATA_PRIMEIROS_SINTOMAS: pd.to_datetime(com_indice_unico[COLUNA_DE_SINTOMAS], errors="coerce"),
           Col.DATA_OBITO_NOTIFICADA: extrair_data_do_obito_notificada(com_indice_unico),
           Col.CLASSIFICACAO_FINAL: extrair_classificacao_final(com_indice_unico)})
    com_sintomas = preparadas.dropna(subset=[Col.DATA_PRIMEIROS_SINTOMAS])
    return manter_residentes_da_uf(com_sintomas, configuracao).reset_index(drop=True)


def manter_residentes_da_uf(notificacoes: pd.DataFrame, configuracao: Configuracao) -> pd.DataFrame:
    """O arquivo do SINAN é nacional: sem este filtro a permutação embaralharia notificações de outras UFs."""
    return notificacoes[notificacoes[Col.MUNICIPIO].str.startswith(configuracao.prefixo_do_codigo_da_uf)]


def cruzar_por_chave(notificacoes: pd.DataFrame, outra_base: pd.DataFrame, colunas_da_outra_base: list[str]) -> pd.DataFrame:
    colunas = CHAVE_DO_SINAN + colunas_da_outra_base
    return notificacoes.merge(outra_base[colunas].dropna(subset=CHAVE_DO_SINAN), on=CHAVE_DO_SINAN, how="inner")


def manter_obitos_a_partir_dos_sintomas(cruzados: pd.DataFrame) -> pd.DataFrame:
    return cruzados[cruzados[Col.DATA_OBITO] >= cruzados[Col.DATA_PRIMEIROS_SINTOMAS]]


def manter_obitos_na_janela_de_sobrevida(cruzados_validos: pd.DataFrame,
                                         janela_em_dias: int = JANELA_DE_SOBREVIDA_EM_DIAS) -> pd.DataFrame:
    dias = (cruzados_validos[Col.DATA_OBITO] - cruzados_validos[Col.DATA_PRIMEIROS_SINTOMAS]).dt.days
    return cruzados_validos[dias <= janela_em_dias]


def manter_internacoes_com_margem(cruzados: pd.DataFrame, margem_em_dias: int) -> pd.DataFrame:
    """A margem absorve erro de preenchimento da data de primeiros sintomas."""
    limite = cruzados[Col.DATA_PRIMEIROS_SINTOMAS] - pd.Timedelta(margem_em_dias, unit="D")
    return cruzados[cruzados[Col.DATA_INTERNACAO] >= limite]


def cruzar_sinan_com_obitos(notificacoes: pd.DataFrame, obitos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cruzados = cruzar_por_chave(notificacoes, obitos, COLUNAS_DO_OBITO_NO_CRUZAMENTO)
    return cruzados, manter_obitos_a_partir_dos_sintomas(cruzados)


def cruzar_sinan_com_internacoes(notificacoes: pd.DataFrame, internacoes: pd.DataFrame,
                                 margem_em_dias: int = MARGEM_DA_INTERNACAO_EM_DIAS) -> tuple[pd.DataFrame, pd.DataFrame]:
    cruzados = cruzar_por_chave(notificacoes, internacoes, [Col.DATA_INTERNACAO, Col.DIAGNOSTICO_PRINCIPAL])
    return cruzados, manter_internacoes_com_margem(cruzados, margem_em_dias)


def resumir_cruzamentos(total_de_notificacoes_brutas: int, notificacoes: pd.DataFrame, com_obito: tuple[pd.DataFrame, pd.DataFrame],
                        com_internacao: tuple[pd.DataFrame, pd.DataFrame]) -> pd.DataFrame:
    linhas = {"notificacoes_brutas": total_de_notificacoes_brutas,
              "notificacoes_a81_com_chave_e_sintomas": len(notificacoes),
              "sinan_x_sim_por_chave": len(com_obito[0]), "sinan_x_sim_validos": len(com_obito[1]),
              "sinan_x_sim_na_janela_de_sobrevida": len(manter_obitos_na_janela_de_sobrevida(com_obito[1])),
              "sinan_x_sih_por_chave": len(com_internacao[0]), "sinan_x_sih_validos": len(com_internacao[1])}
    return pd.DataFrame({"valor": linhas})


def listar_individuos_do_cruzamento(cruzados_validos: pd.DataFrame) -> pd.DataFrame:
    """Um óbito por chave e data de óbito (mesma regra do notebook). São óbitos COMPATÍVEIS com alguma
    notificação, não pacientes confirmados: compare com a permutação antes de interpretar."""
    return cruzados_validos.drop_duplicates(subset=CHAVE_DO_INDIVIDUO).reset_index(drop=True)


def resumir_perfil_dos_individuos(individuos: pd.DataFrame, quantidade_de_causas: int = 10) -> pd.DataFrame:
    indicadores: dict[str, float] = {"individuos_unicos": len(individuos),
                                     "idade_media_ao_obito": round(individuos[Col.IDADE_ANOS].mean(), 1),
                                     "idade_mediana_ao_obito": individuos[Col.IDADE_ANOS].median()}
    for sexo, total in individuos[Col.SEXO].value_counts().items():
        indicadores[f"sexo_{sexo}"] = total
    for causa, total in individuos[Col.CAUSA_BASICA].value_counts().head(quantidade_de_causas).items():
        indicadores[f"causa_{causa}"] = total
    return pd.DataFrame({"valor": indicadores})