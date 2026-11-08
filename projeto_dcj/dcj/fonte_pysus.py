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

# Prefixos IBGE das UFs; usados para filtrar SIM (que baixa consolidado nacional).
_PREFIXOS_DAS_UFS = {
    "AC": "12", "AL": "27", "AP": "16", "AM": "13", "BA": "29", "CE": "23",
    "DF": "53", "ES": "32", "GO": "52", "MA": "21", "MT": "51", "MS": "50",
    "MG": "31", "PA": "15", "PB": "25", "PR": "41", "PE": "26", "PI": "22",
    "RJ": "33", "RN": "24", "RS": "43", "RO": "11", "RR": "14", "SC": "42",
    "SP": "35", "SE": "28", "TO": "17",
}


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
    if resultado.empty:
        raise ValueError("DataFrame vazio — nada baixado")
    return resultado


def _com_colunas_em_maiusculas(tabela: pd.DataFrame) -> pd.DataFrame:
    """O pipeline usa os nomes do DATASUS em maiúsculas; versões do PySUS podem devolver minúsculas."""
    return tabela.rename(columns=lambda coluna: str(coluna).strip().upper())


def _manter_residentes_da_uf(tabela: pd.DataFrame, sigla_uf: str) -> pd.DataFrame:
    """SIM 2.x entrega o consolidado nacional; mantém só residentes da UF via CODMUNRES."""
    prefixo = _PREFIXOS_DAS_UFS.get(sigla_uf)
    if prefixo is None or "CODMUNRES" not in tabela.columns:
        return tabela  # mock em teste, ou base que já vem filtrada
    return tabela[tabela["CODMUNRES"].astype(str).str[:2] == prefixo].reset_index(drop=True)


def _importar_pysus() -> ModuleType:
    import pysus
    return pysus


def _consultar_pelo_cliente(**filtros: object) -> pd.DataFrame:
    from pysus.api.client import PySUS

    async def consultar() -> pd.DataFrame:
        async with PySUS() as cliente:
            return await cliente.query(as_dataframe=True, **filtros)
    return asyncio.run(consultar())


def obter_obitos_do_pysus(sigla_uf: str, ano: int) -> pd.DataFrame:
    return _manter_residentes_da_uf(
        _com_colunas_em_maiusculas(executar_primeira_tentativa_valida({
            "pysus.ftp.sim (state=)": lambda: _importar_pysus().ftp.sim(
                state=sigla_uf, year=ano, as_dataframe=True),
            "pysus.ftp.sim (uf=)": lambda: _importar_pysus().ftp.sim(
                uf=sigla_uf, year=ano, as_dataframe=True),
            "pysus.sim (legado)": lambda: _importar_pysus().sim(sigla_uf, ano, as_dataframe=True),
            "PySUS.query": lambda: _consultar_pelo_cliente(dataset="sim", state=sigla_uf, year=ano)})),
        sigla_uf,
    )


def obter_internacoes_do_pysus(sigla_uf: str, ano: int, mes: int) -> pd.DataFrame:
    """SIH 2.x já entrega por UF (arquivos RDRS/SPRS); não precisa filtrar."""
    return _com_colunas_em_maiusculas(executar_primeira_tentativa_valida({
        "pysus.ftp.sih (state=)": lambda: _importar_pysus().ftp.sih(
            state=sigla_uf, year=ano, month=mes, as_dataframe=True),
        "pysus.ftp.sih (uf=)": lambda: _importar_pysus().ftp.sih(
            uf=sigla_uf, year=ano, month=mes, as_dataframe=True),
        "pysus.sih (legado)": lambda: _importar_pysus().sih(sigla_uf, ano, mes, as_dataframe=True),
        "PySUS.query": lambda: _consultar_pelo_cliente(dataset="sih", state=sigla_uf, year=ano, month=mes)}))


def obter_notificacoes_do_pysus(ano: int) -> pd.DataFrame:
    """Arquivo nacional do agravo (DCRJBRAA); o filtro por UF é feito depois."""
    agravo = CODIGO_DO_AGRAVO_DCJ_NO_SINAN
    return _com_colunas_em_maiusculas(executar_primeira_tentativa_valida({
        "pysus.ftp.sinan": lambda: _importar_pysus().ftp.sinan(disease=agravo, year=ano, as_dataframe=True),
        "pysus.sinan (legado)": lambda: _importar_pysus().sinan(agravo, ano, as_dataframe=True),
        "PySUS.query": lambda: _consultar_pelo_cliente(dataset="sinan", group=agravo, year=ano)}))


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
    except Exception as erro:  ## sonda de diagnóstico: qualquer falha vira texto, nunca derruba o comando.
        return f"não verificável ({type(erro).__name__})"