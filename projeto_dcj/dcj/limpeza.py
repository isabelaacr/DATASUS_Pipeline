"""Limpeza dos brutos: UF, duplicatas, janela de anos e colunas derivadas, com funil."""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Callable, Sequence

import pandas as pd

from dcj.colunas import Bruto, Col
from dcj.configuracao import Configuracao
from dcj.erros import garantir_colunas
from dcj.funil import Funil
from dcj.padronizacao import (
    MAPA_SEXO_DAS_INTERNACOES, MAPA_SEXO_DOS_OBITOS, converter_data_aaaammdd, converter_data_ddmmaaaa,
    decodificar_idade_em_anos, padronizar_cid, padronizar_codigo_municipio, padronizar_sexo)

ResultadoDaLimpeza = tuple[pd.DataFrame, pd.DataFrame]


def filtrar_residentes_da_uf(tabela: pd.DataFrame, coluna_do_municipio: str, prefixo_da_uf: str) -> pd.DataFrame:
    return tabela[tabela[coluna_do_municipio].str.startswith(prefixo_da_uf, na=False)]


def remover_duplicatas(tabela: pd.DataFrame, colunas: Sequence[str]) -> pd.DataFrame:
    return tabela.drop_duplicates(subset=list(colunas))


def filtrar_janela_de_anos(tabela: pd.DataFrame, coluna_da_data: str, anos: Sequence[int]) -> pd.DataFrame:
    return tabela[tabela[coluna_da_data].dt.year.isin(anos)]


def colunas_existentes(tabela: pd.DataFrame, preferidas: Sequence[str]) -> list[str]:
    return [coluna for coluna in preferidas if coluna in tabela.columns]


def adicionar_dados_de_nascimento(tabela: pd.DataFrame, datas_de_nascimento: pd.Series) -> pd.DataFrame:
    return tabela.assign(**{
        Col.DATA_NASCIMENTO: datas_de_nascimento,
        Col.ANO_NASCIMENTO: datas_de_nascimento.dt.year,
        Col.MES_DIA_NASCIMENTO: datas_de_nascimento.dt.strftime("%m%d"),
    })


def enriquecer_obitos(tabela: pd.DataFrame) -> pd.DataFrame:
    com_nascimento = adicionar_dados_de_nascimento(tabela, converter_data_ddmmaaaa(tabela[Bruto.OBITO_NASCIMENTO]))
    return com_nascimento.assign(**{
        Col.SEXO: padronizar_sexo(tabela[Bruto.OBITO_SEXO], MAPA_SEXO_DOS_OBITOS),
        Col.MUNICIPIO: tabela[Bruto.OBITO_MUNICIPIO],
        Col.IDADE_ANOS: decodificar_idade_em_anos(tabela[Bruto.OBITO_IDADE]),
        Col.CAUSA_BASICA: padronizar_cid(tabela[Bruto.OBITO_CAUSA]),
    })


def enriquecer_internacoes(tabela: pd.DataFrame) -> pd.DataFrame:
    com_nascimento = adicionar_dados_de_nascimento(tabela, converter_data_aaaammdd(tabela[Bruto.INTERNACAO_NASCIMENTO]))
    return com_nascimento.assign(**{
        Col.SEXO: padronizar_sexo(tabela[Bruto.INTERNACAO_SEXO], MAPA_SEXO_DAS_INTERNACOES),
        Col.MUNICIPIO: tabela[Bruto.INTERNACAO_MUNICIPIO],
        Col.DIAGNOSTICO_PRINCIPAL: padronizar_cid(tabela[Bruto.INTERNACAO_DIAGNOSTICO]),
    })


@dataclass(frozen=True)
class EspecificacaoDaBase:
    """Tudo o que difere entre óbitos e internações na limpeza; o restante é compartilhado."""

    nome: str
    colunas_obrigatorias: tuple[str, ...]
    coluna_do_municipio: str
    coluna_da_data_bruta: str
    coluna_da_data_derivada: str
    converter_data: Callable[[pd.Series], pd.Series]
    escolher_colunas_de_duplicidade: Callable[[pd.DataFrame], list[str]]
    enriquecer: Callable[[pd.DataFrame], pd.DataFrame]


def limpar_base(brutos: pd.DataFrame, especificacao: EspecificacaoDaBase, anos: Sequence[int],
                configuracao: Configuracao) -> ResultadoDaLimpeza:
    garantir_colunas(brutos, especificacao.colunas_obrigatorias, f"{especificacao.nome} brutos")
    funil = Funil()
    funil.registrar("1. Arquivos brutos", brutos)
    padronizados = padronizar_municipio(brutos, especificacao.coluna_do_municipio, configuracao)
    residentes = funil.aplicar(f"2. Residentes da UF (prefixo {configuracao.prefixo_do_codigo_da_uf})", padronizados,
                               partial(filtrar_residentes_da_uf, coluna_do_municipio=especificacao.coluna_do_municipio,
                                       prefixo_da_uf=configuracao.prefixo_do_codigo_da_uf))
    colunas_de_duplicidade = especificacao.escolher_colunas_de_duplicidade(residentes)
    unicos = funil.aplicar("3. Sem duplicatas", residentes, partial(remover_duplicatas, colunas=colunas_de_duplicidade))
    datas = especificacao.converter_data(unicos[especificacao.coluna_da_data_bruta])
    com_data = unicos.assign(**{especificacao.coluna_da_data_derivada: datas})
    na_janela = funil.aplicar(f"4. Data na janela {min(anos)}-{max(anos)}", com_data, partial(
        filtrar_janela_de_anos, coluna_da_data=especificacao.coluna_da_data_derivada, anos=anos))
    return especificacao.enriquecer(na_janela).reset_index(drop=True), funil.como_tabela()


def padronizar_municipio(tabela: pd.DataFrame, coluna: str, configuracao: Configuracao) -> pd.DataFrame:
    codigos = padronizar_codigo_municipio(tabela[coluna], configuracao.digitos_do_municipio)
    return tabela.assign(**{coluna: codigos})


def colunas_de_duplicidade_das_internacoes(tabela: pd.DataFrame, configuracao: Configuracao) -> list[str]:
    """Usa o número da AIH quando existe; sem ele, só linhas integralmente iguais são duplicatas."""
    numero_da_aih = Bruto.INTERNACAO_NUMERO_DA_AIH
    if numero_da_aih in tabela.columns and tabela[numero_da_aih].notna().any():
        return [numero_da_aih]
    return colunas_existentes(tabela, configuracao.colunas_das_internacoes)


def especificacao_dos_obitos(configuracao: Configuracao) -> EspecificacaoDaBase:
    return EspecificacaoDaBase(
        nome="óbitos",
        colunas_obrigatorias=configuracao.colunas_dos_obitos[:-1],
        coluna_do_municipio=Bruto.OBITO_MUNICIPIO,
        coluna_da_data_bruta=Bruto.OBITO_DATA,
        coluna_da_data_derivada=Col.DATA_OBITO,
        converter_data=converter_data_ddmmaaaa,
        escolher_colunas_de_duplicidade=partial(colunas_existentes, preferidas=configuracao.colunas_dos_obitos),
        enriquecer=enriquecer_obitos)


def especificacao_das_internacoes(configuracao: Configuracao) -> EspecificacaoDaBase:
    return EspecificacaoDaBase(
        nome="internações",
        colunas_obrigatorias=configuracao.colunas_das_internacoes[:5],
        coluna_do_municipio=Bruto.INTERNACAO_MUNICIPIO,
        coluna_da_data_bruta=Bruto.INTERNACAO_DATA,
        coluna_da_data_derivada=Col.DATA_INTERNACAO,
        converter_data=converter_data_aaaammdd,
        escolher_colunas_de_duplicidade=partial(colunas_de_duplicidade_das_internacoes, configuracao=configuracao),
        enriquecer=enriquecer_internacoes)


def limpar_obitos(brutos: pd.DataFrame, configuracao: Configuracao) -> ResultadoDaLimpeza:
    return limpar_base(brutos, especificacao_dos_obitos(configuracao), configuracao.anos_dos_obitos, configuracao)


def limpar_internacoes(brutas: pd.DataFrame, configuracao: Configuracao) -> ResultadoDaLimpeza:
    return limpar_base(brutas, especificacao_das_internacoes(configuracao), configuracao.anos_das_internacoes,
                       configuracao)
