"""Pareamento internação x óbito por município, sexo e data de nascimento completa."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from dcj.colunas import Col
from dcj.configuracao import Configuracao, CriterioDeDesempate
from dcj.erros import garantir_colunas

# NOVO: janela máxima entre internação e óbito (alinhada à literatura clínica e ao SINAN)
JANELA_MAXIMA_ENTRE_INTERNACAO_E_OBITO_EM_DIAS = 365


@dataclass(frozen=True)
class ResultadoDoPareamento:
    pares: pd.DataFrame
    candidatos: int
    apos_internacao_antes_do_obito: int

    @property
    def total_de_pares(self) -> int:
        return len(self.pares)


def montar_chave_de_pareamento(exigir_mesmo_municipio: bool) -> list[str]:
    municipio = [Col.MUNICIPIO] if exigir_mesmo_municipio else []
    return municipio + [Col.SEXO, Col.DATA_NASCIMENTO]


def preparar_lado(tabela: pd.DataFrame, chave: list[str], coluna_de_identificador: str) -> pd.DataFrame:
    """Sem chave completa não há pareamento possível; o identificador é posicional e estável."""
    completa = tabela.dropna(subset=chave).reset_index(drop=True)
    return completa.assign(**{coluna_de_identificador: range(len(completa))})


def encontrar_candidatos(internacoes: pd.DataFrame, obitos: pd.DataFrame, chave: list[str]) -> pd.DataFrame:
    colunas_da_internacao = [Col.ID_INTERNACAO, Col.DATA_INTERNACAO, Col.DIAGNOSTICO_PRINCIPAL] + chave
    colunas_do_obito = [Col.ID_OBITO, Col.DATA_OBITO, Col.CAUSA_BASICA, Col.IDADE_ANOS, Col.ANO_NASCIMENTO] + chave
    return internacoes[colunas_da_internacao].merge(obitos[colunas_do_obito], on=chave, how="inner")


def manter_internacoes_antes_do_obito(pares: pd.DataFrame,
                                      janela_em_dias: int = JANELA_MAXIMA_ENTRE_INTERNACAO_E_OBITO_EM_DIAS) -> pd.DataFrame:
    """Mantém apenas pares onde o óbito ocorreu entre 0 e 365 dias após a internação.
    
    A janela de 1 ano é clinicamente plausível para a DCJ (sobrevida média de 5 meses)
    e está alinhada com a regra usada no cruzamento com o SINAN.
    """
    dias = (pares[Col.DATA_OBITO] - pares[Col.DATA_INTERNACAO]).dt.days
    return pares[dias.between(0, janela_em_dias)]


def manter_um_para_um(pares: pd.DataFrame, criterio_de_desempate: CriterioDeDesempate) -> pd.DataFrame:
    """Uma internação por óbito (a última ou a primeira) e um óbito por internação."""
    mais_antiga_primeiro = criterio_de_desempate == "primeira"
    ordenados = pares.sort_values([Col.DATA_INTERNACAO, Col.ID_INTERNACAO], ascending=[mais_antiga_primeiro, True])
    return ordenados.drop_duplicates(Col.ID_OBITO).drop_duplicates(Col.ID_INTERNACAO)


def adicionar_dias_ate_o_obito(pares: pd.DataFrame) -> pd.DataFrame:
    return pares.assign(**{Col.DIAS_ATE_OBITO: (pares[Col.DATA_OBITO] - pares[Col.DATA_INTERNACAO]).dt.days})


def parear(internacoes: pd.DataFrame, obitos: pd.DataFrame, configuracao: Configuracao) -> ResultadoDoPareamento:
    chave = montar_chave_de_pareamento(configuracao.exigir_mesmo_municipio)
    garantir_colunas(internacoes, chave + [Col.DATA_INTERNACAO, Col.DIAGNOSTICO_PRINCIPAL], "internações limpas")
    garantir_colunas(obitos, chave + [Col.DATA_OBITO, Col.CAUSA_BASICA, Col.IDADE_ANOS], "óbitos limpos")
    candidatos = encontrar_candidatos(preparar_lado(internacoes, chave, Col.ID_INTERNACAO),
                                      preparar_lado(obitos, chave, Col.ID_OBITO), chave)
    # ALTERADO: agora usa a janela de 365 dias em vez de apenas "antes do óbito"
    validos = manter_internacoes_antes_do_obito(candidatos)
    unicos = manter_um_para_um(validos, configuracao.criterio_de_desempate)
    pares = adicionar_dias_ate_o_obito(unicos.sort_values(Col.DATA_INTERNACAO).reset_index(drop=True))
    return ResultadoDoPareamento(pares, len(candidatos), len(validos))