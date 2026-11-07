"""Único ponto de contato com o PySUS 2.x (documentação 2.11.7, pysus.readthedocs.io).

Cada base tenta, em ordem: a interface por namespace (`pysus.ftp.sim`), as funções planas legadas (`pysus.sim`,
com aviso de depreciação) e o cliente de baixo nível (`PySUS.query`). Se todas falharem, o erro lista o motivo
de cada tentativa e a versão instalada."""
from __future__ import annotations

import asyncio
from importlib import metadata
from types import ModuleType
from typing import Callable

import pandas as pd

CODIGO_DO_AGRAVO_DCJ_NO_SINAN = "DCRJ"
Tentativa = Callable[[], pd.DataFrame]
ERROS_DE_API_INCOMPATIVEL = (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError)


def versao_do_pysus() -> str:
    try:
        return "pysus " + metadata.version("pysus")
    except metadata.PackageNotFoundError:
        return "pysus não instalado"


def executar_primeira_tentativa_valida(tentativas: dict[str, Tentativa]) -> pd.DataFrame:
    motivos: list[str] = []
    for nome, tentativa in tentativas.items():
        try:
            return _exigir_tabela(tentativa())
        except ERROS_DE_API_INCOMPATIVEL as erro:
            motivos.append(f"{nome}: {type(erro).__name__}: {erro}")
    raise ValueError("Nenhuma API do PySUS funcionou (" + versao_do_pysus() + "). " + " | ".join(motivos))


def _exigir_tabela(resultado: object) -> pd.DataFrame:
    if not isinstance(resultado, pd.DataFrame):
        raise TypeError(f"esperava DataFrame, veio {type(resultado).__name__}")
    return resultado


def _importar_pysus() -> ModuleType:
    import pysus
    return pysus


def _consultar_pelo_cliente(**filtros: object) -> pd.DataFrame:
    from pysus.api.client import PySUS

    async def consultar() -> pd.DataFrame:
        async with PySUS() as cliente:
            return await cliente.query(as_dataframe=True, **filtros)
    return asyncio.run(consultar())


# --- TRADUTORES DE COLUNAS (PySUS 2.11+ usa minúsculas e parâmetros diferentes) ---
def _traduzir_sim(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    mapa = {"sexo": "SEXO", "dtnasc": "DTNASC", "codmunres": "CODMUNRES", "dtobito": "DTOBITO",
            "causabas": "CAUSABAS", "idade": "IDADE", "numerodo": "NUMERODO"}
    df.columns = [mapa.get(c.lower().strip(), c.upper().strip()) for c in df.columns]
    if "CAUSABAS" in df.columns:
        df["CAUSABAS"] = df["CAUSABAS"].astype(str).str.strip().str.upper()
    return df


def _traduzir_sih(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    mapa = {"sexo": "SEXO", "nasc": "NASC", "munic_res": "MUNIC_RES", "dt_inter": "DT_INTER",
            "diag_princ": "DIAG_PRINC", "diag_secun": "DIAG_SECUN", "n_aih": "N_AIH"}
    df.columns = [mapa.get(c.lower().strip(), c.upper().strip()) for c in df.columns]
    return df


def _traduzir_sinan(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    mapa = {"id_agravo": "ID_AGRAVO", "cs_sexo": "CS_SEXO", "id_municip": "ID_MN_RESI", 
            "id_mn_resi": "ID_MN_RESI", "ano_nasc": "ANO_NASC", "dt_nasc": "DT_NASC",
            "dt_sin_pri": "DT_SIN_PRI", "dt_notific": "DT_NOTIFIC", 
            "classi_fin": "CLASSI_FIN", "evolucao": "EVOLUCAO"}
    df.columns = [mapa.get(c.lower().strip(), c.upper().strip()) for c in df.columns]
    return df


def obter_obitos_do_pysus(sigla_uf: str, ano: int) -> pd.DataFrame:
    def baixar():
        return executar_primeira_tentativa_valida({
            # CORREÇÃO: usamos uf= em vez de state= na API nova do PySUS 2.11+
            "pysus.ftp.sim": lambda: _importar_pysus().ftp.sim(uf=sigla_uf, year=ano, as_dataframe=True),
            "pysus.sim (legado)": lambda: _importar_pysus().sim(sigla_uf, ano, as_dataframe=True),
            "PySUS.query": lambda: _consultar_pelo_cliente(dataset="sim", state=sigla_uf, year=ano)})
    return _traduzir_sim(baixar())


def obter_internacoes_do_pysus(sigla_uf: str, ano: int, mes: int) -> pd.DataFrame:
    def baixar():
        return executar_primeira_tentativa_valida({
            # CORREÇÃO: usamos uf= em vez de state= na API nova
            "pysus.ftp.sih": lambda: _importar_pysus().ftp.sih(uf=sigla_uf, year=ano, month=mes, as_dataframe=True),
            "pysus.sih (legado)": lambda: _importar_pysus().sih(sigla_uf, ano, mes, as_dataframe=True),
            "PySUS.query": lambda: _consultar_pelo_cliente(dataset="sih", state=sigla_uf, year=ano, month=mes)})
    return _traduzir_sih(baixar())


def obter_notificacoes_do_pysus(ano: int) -> pd.DataFrame:
    """Arquivo nacional do agravo (DCRJBRAA); o filtro por UF é feito depois."""
    agravo = CODIGO_DO_AGRAVO_DCJ_NO_SINAN
    def baixar():
        return executar_primeira_tentativa_valida({
            "pysus.ftp.sinan": lambda: _importar_pysus().ftp.sinan(disease=agravo, year=ano, as_dataframe=True),
            "pysus.sinan (legado)": lambda: _importar_pysus().sinan(agravo, ano, as_dataframe=True),
            "PySUS.query": lambda: _consultar_pelo_cliente(dataset="sinan", group=agravo, year=ano)})
    return _traduzir_sinan(baixar())


def descrever_pysus_instalado() -> dict[str, object]:
    """Sonda sem download: mostra quais entradas da API existem na versão instalada."""
    try:
        pysus = _importar_pysus()
    except ImportError:
        return {"versao": versao_do_pysus()}
    namespace = getattr(pysus, "ftp", None)
    return {"versao": versao_do_pysus(),
            "pysus.ftp.sim/sih/sinan": [hasattr(namespace, nome) for nome in ("sim", "sih", "sinan")],
            "pysus.sim/sih/sinan (legado)": [hasattr(pysus, nome) for nome in ("sim", "sih", "sinan")],
            "agravos_do_sinan_com_DCRJ": _agravo_dcj_listado_no_pysus()}


def _agravo_dcj_listado_no_pysus() -> str:
    try:
        from pysus.api.ftp.databases import SINAN
        definicoes = getattr(SINAN, "group_definitions", None)
        return "sim" if definicoes and CODIGO_DO_AGRAVO_DCJ_NO_SINAN in definicoes else f"não confirmado ({type(definicoes).__name__})"
    except Exception as erro:
        return f"não verificável ({type(erro).__name__})"