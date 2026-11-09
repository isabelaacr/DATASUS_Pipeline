"""Limpeza dos brutos: UF, duplicatas, janela de anos e colunas derivadas, com funil."""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Callable, Sequence

import pandas as pd
from dcj.referencias import CID_DA_DCJ
from dcj.colunas import Bruto, Col
from dcj.configuracao import Configuracao
from dcj.erros import garantir_colunas
from dcj.funil import Funil
from dcj.padronizacao import (
    MAPA_SEXO_DAS_INTERNACOES, MAPA_SEXO_DOS_OBITOS, converter_data_aaaammdd, converter_data_ddmmaaaa,
    decodificar_idade_em_anos, padronizar_cid, padronizar_codigo_municipio, padronizar_sexo, limpar_texto_numerico)

ResultadoDaLimpeza = tuple[pd.DataFrame, pd.DataFrame]
CAMPOS_PREENCHIDOS = "_campos_preenchidos"


def filtrar_residentes_da_uf(tabela: pd.DataFrame, coluna_do_municipio: str, prefixo_da_uf: str) -> pd.DataFrame:
    return tabela[tabela[coluna_do_municipio].str.startswith(prefixo_da_uf, na=False)]


def normalizar_identificador(valores: pd.Series) -> pd.Series:
    """NUMERODO / N_AIH sem espaços nem sufixo '.0'; se for só dígitos, também sem zeros à esquerda. Vazio vira NA."""
    texto = limpar_texto_numerico(valores).str.replace(r"\s", "", regex=True).str.upper()
    so_digitos = texto.str.fullmatch(r"\d+", na=False)
    texto = texto.mask(so_digitos, texto.str.lstrip("0"))
    return texto.mask(texto.isna() | (texto == ""))


def chave_dos_obitos(tabela: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    # Normaliza as strings de data antes de comparar
    def normalizar_data(serie: pd.Series) -> pd.Series:
        return serie.astype("string").str.replace(r"\D", "", regex=True).str.zfill(8).str[:8]

    # Normaliza o município para 6 dígitos
    def normalizar_municipio(serie: pd.Series) -> pd.Series:
        return serie.astype("string").str.replace(r"\D", "", regex=True).str.zfill(6).str[:6]

    chave = pd.DataFrame({
        "municipio": normalizar_municipio(tabela[Bruto.OBITO_MUNICIPIO]),
        "sexo": tabela[Bruto.OBITO_SEXO].astype("string").str.strip().str.upper(),
        "nascimento": normalizar_data(tabela[Bruto.OBITO_NASCIMENTO]),
        "obito": normalizar_data(tabela[Bruto.OBITO_DATA]),
    }, index=tabela.index)
    
    numero = Bruto.OBITO_NUMERO_DA_DECLARACAO
    if numero in tabela.columns:
        identificador = normalizar_identificador(tabela[numero])
    else:
        identificador = pd.Series(pd.NA, index=tabela.index, dtype="string")
    return chave, identificador


def chave_das_internacoes(tabela: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    chave = pd.DataFrame({
        "municipio": tabela[Bruto.INTERNACAO_MUNICIPIO],
        "sexo": padronizar_sexo(tabela[Bruto.INTERNACAO_SEXO], MAPA_SEXO_DAS_INTERNACOES),
        "nascimento": converter_data_aaaammdd(tabela[Bruto.INTERNACAO_NASCIMENTO]),
        "internacao": converter_data_aaaammdd(tabela[Bruto.INTERNACAO_DATA]),
        "diagnostico": padronizar_cid(tabela[Bruto.INTERNACAO_DIAGNOSTICO]),
    }, index=tabela.index)
    
    numero = Bruto.INTERNACAO_NUMERO_DA_AIH
    identificador = (normalizar_identificador(tabela[numero]) if numero in tabela.columns
                     else pd.Series(pd.NA, index=tabela.index, dtype="string"))
    return chave, identificador


def marcar_duplicatas(chave_demografica: pd.DataFrame, identificador: pd.Series) -> pd.Series:
    """True para as linhas a remover.
    
    - Com identificador (NUMERODO, N_AIH): duplicata = mesmo identificador de uma linha anterior.
    - Sem identificador: duplicata = mesma chave demográfica normalizada.
    """
    tem_id = identificador.notna()
    repetido_pelo_id = tem_id & identificador.duplicated(keep="first")
    
    tuplas = pd.Series(list(chave_demografica.astype("string").fillna("<NA>").itertuples(index=False, name=None)),
                       index=chave_demografica.index)
    
    chaves_com_id = set(tuplas[tem_id])
    sem_id = ~tem_id
    repetido_sem_id = pd.Series(False, index=chave_demografica.index)
    repetido_sem_id[sem_id] = tuplas[sem_id].isin(chaves_com_id) | tuplas[sem_id].duplicated(keep="first")
    
    return repetido_pelo_id | repetido_sem_id


def contar_campos_preenchidos(tabela: pd.DataFrame) -> pd.Series:
    return tabela.notna().sum(axis=1)


def remover_duplicatas(tabela: pd.DataFrame,
                       montar_chave: Callable[[pd.DataFrame], tuple[pd.DataFrame, pd.Series]]) -> pd.DataFrame:
    if tabela.empty:
        return tabela
        
    # Adiciona contagem de campos preenchidos para manter a cópia mais completa
    tabela_com_contagem = tabela.assign(**{CAMPOS_PREENCHIDOS: contar_campos_preenchidos(tabela)})
    # Ordena decrescentemente para que a cópia mais preenchida seja a primeira
    tabela_ordenada = tabela_com_contagem.sort_values(CAMPOS_PREENCHIDOS, ascending=False, kind="stable")
    
    chave, identificador = montar_chave(tabela_ordenada)
    duplicatas = marcar_duplicatas(chave, identificador)
    
    # Remove as duplicatas e a coluna auxiliar
    filtrada = tabela_ordenada[~duplicatas].drop(columns=CAMPOS_PREENCHIDOS)
    return filtrada


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


def marcar_dcj_na_declaracao(tabela: pd.DataFrame) -> pd.Series:
    """A81.0 em qualquer linha da declaração (inclui a causa básica). Parquets sem as linhas: só a causa básica."""
    campos = [Bruto.OBITO_CAUSA, *(c for c in Bruto.OBITO_LINHAS_DA_DECLARACAO if c in tabela.columns)]
    marcado = pd.Series(False, index=tabela.index)
    for campo in campos:
        marcado |= tabela[campo].astype("string").str.upper().str.contains(
            rf"(?:^|\*)\s*{CID_DA_DCJ}", regex=True, na=False)
    return marcado


def enriquecer_obitos(tabela: pd.DataFrame) -> pd.DataFrame:
    com_nascimento = adicionar_dados_de_nascimento(tabela, converter_data_ddmmaaaa(tabela[Bruto.OBITO_NASCIMENTO]))
    return com_nascimento.assign(**{
        Col.SEXO: padronizar_sexo(tabela[Bruto.OBITO_SEXO], MAPA_SEXO_DOS_OBITOS),
        Col.MUNICIPIO: tabela[Bruto.OBITO_MUNICIPIO],
        Col.IDADE_ANOS: decodificar_idade_em_anos(tabela[Bruto.OBITO_IDADE]),
        Col.CAUSA_BASICA: padronizar_cid(tabela[Bruto.OBITO_CAUSA]),
        Col.DCJ_NA_DECLARACAO: marcar_dcj_na_declaracao(tabela),  
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
    montar_chave_de_duplicidade: Callable[[pd.DataFrame], tuple[pd.DataFrame, pd.Series]]
    enriquecer: Callable[[pd.DataFrame], pd.DataFrame]
    descricao_da_duplicidade: str = ""


def limpar_base(brutos: pd.DataFrame, especificacao: EspecificacaoDaBase, anos: Sequence[int],
                configuracao: Configuracao) -> ResultadoDaLimpeza:
    garantir_colunas(brutos, especificacao.colunas_obrigatorias, f"{especificacao.nome} brutos")
    funil = Funil()
    funil.registrar("1. Arquivos brutos", brutos)
    padronizados = padronizar_municipio(brutos, especificacao.coluna_do_municipio, configuracao)
    residentes = funil.aplicar(f"2. Residentes da UF (prefixo {configuracao.prefixo_do_codigo_da_uf})", padronizados,
                               partial(filtrar_residentes_da_uf, coluna_do_municipio=especificacao.coluna_do_municipio,
                                       prefixo_da_uf=configuracao.prefixo_do_codigo_da_uf))
    
    unicos = funil.aplicar(f"3. Sem duplicatas ({especificacao.descricao_da_duplicidade})", residentes,
                           partial(remover_duplicatas, montar_chave=especificacao.montar_chave_de_duplicidade))
    
    datas = especificacao.converter_data(unicos[especificacao.coluna_da_data_bruta])
    com_data = unicos.assign(**{especificacao.coluna_da_data_derivada: datas})
    
    na_janela = funil.aplicar(f"4. Data na janela {min(anos)}-{max(anos)}", com_data, partial(
        filtrar_janela_de_anos, coluna_da_data=especificacao.coluna_da_data_derivada, anos=anos))
    
    return especificacao.enriquecer(na_janela).reset_index(drop=True), funil.como_tabela()


def padronizar_municipio(tabela: pd.DataFrame, coluna: str, configuracao: Configuracao) -> pd.DataFrame:
    codigos = padronizar_codigo_municipio(tabela[coluna], configuracao.digitos_do_municipio)
    return tabela.assign(**{coluna: codigos})


def especificacao_dos_obitos(configuracao: Configuracao) -> EspecificacaoDaBase:
    return EspecificacaoDaBase(
        nome="óbitos",
        colunas_obrigatorias=configuracao.colunas_dos_obitos[:-1],
        coluna_do_municipio=Bruto.OBITO_MUNICIPIO,
        coluna_da_data_bruta=Bruto.OBITO_DATA,
        coluna_da_data_derivada=Col.DATA_OBITO,
        converter_data=converter_data_ddmmaaaa,
        montar_chave_de_duplicidade=chave_dos_obitos,
        enriquecer=enriquecer_obitos,
        descricao_da_duplicidade="NUMERODO; sem ele, chave demográfica")


def especificacao_das_internacoes(configuracao: Configuracao) -> EspecificacaoDaBase:
    return EspecificacaoDaBase(
        nome="internações",
        colunas_obrigatorias=configuracao.colunas_das_internacoes[:5],
        coluna_do_municipio=Bruto.INTERNACAO_MUNICIPIO,
        coluna_da_data_bruta=Bruto.INTERNACAO_DATA,
        coluna_da_data_derivada=Col.DATA_INTERNACAO,
        converter_data=converter_data_aaaammdd,
        montar_chave_de_duplicidade=chave_das_internacoes,
        enriquecer=enriquecer_internacoes,
        descricao_da_duplicidade="N_AIH; sem ele, chave demográfica")


def limpar_obitos(brutos: pd.DataFrame, configuracao: Configuracao) -> ResultadoDaLimpeza:
    return limpar_base(brutos, especificacao_dos_obitos(configuracao), configuracao.anos_dos_obitos, configuracao)


def limpar_internacoes(brutas: pd.DataFrame, configuracao: Configuracao) -> ResultadoDaLimpeza:
    return limpar_base(brutas, especificacao_das_internacoes(configuracao), configuracao.anos_das_internacoes,
                       configuracao)