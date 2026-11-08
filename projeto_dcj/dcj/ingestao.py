"""Download de SIM, SIH e SINAN via PySUS. Grava SOMENTE arquivos brutos, nunca consolidados."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from dcj.colunas import Bruto
from dcj.configuracao import Configuracao
from dcj.fonte_pysus import obter_internacoes_do_pysus, obter_notificacoes_do_pysus, obter_obitos_do_pysus

registro = logging.getLogger(__name__)
ObterObitos = Callable[[str, int], pd.DataFrame]
ObterInternacoes = Callable[[str, int, int], pd.DataFrame]
ObterNotificacoes = Callable[[int], pd.DataFrame]
PREFIXO_DO_AGRAVO_NO_SINAN = "A81"


@dataclass(frozen=True)
class FalhaDeDownload:
    base: str
    periodo: str
    motivo: str


def manter_residentes_da_uf(tabela: pd.DataFrame, prefixo_do_codigo_da_uf: str) -> pd.DataFrame:
    """SINAN: o arquivo nacional é filtrado aqui pela coluna de município da notificação."""
    residentes = tabela[Bruto.NOTIFICACAO_MUNICIPIO].astype("string").str.startswith(prefixo_do_codigo_da_uf, na=False)
    return tabela[residentes]


def manter_residentes_do_sim(tabela: pd.DataFrame, prefixo_do_codigo_da_uf: str) -> pd.DataFrame:
    """SIM 2.x entrega consolidado nacional; mantém só residentes da UF via CODMUNRES.

    Defensivo: se a coluna não existir (mock de teste, base já filtrada pela fonte), devolve intacto.
    """
    if "CODMUNRES" not in tabela.columns:
        return tabela
    residentes = tabela["CODMUNRES"].astype("string").str[:2] == prefixo_do_codigo_da_uf
    return tabela[residentes].reset_index(drop=True)


def manter_colunas_e_cids_de_interesse(tabela: pd.DataFrame, colunas: tuple[str, ...], colunas_de_cid: list[str],
                                       cids: tuple[str, ...]) -> pd.DataFrame:
    reduzida = tabela[[coluna for coluna in colunas if coluna in tabela.columns]]
    de_interesse = pd.Series(False, index=reduzida.index)
    for coluna in (nome for nome in colunas_de_cid if nome in reduzida.columns):
        de_interesse |= reduzida[coluna].astype("string").str.startswith(cids, na=False)
    return reduzida[de_interesse]


def baixar_obitos(configuracao: Configuracao, obter: ObterObitos = obter_obitos_do_pysus) -> list[FalhaDeDownload]:
    falhas: list[FalhaDeDownload] = []
    for ano in configuracao.anos_dos_obitos:
        destino = configuracao.pasta_dos_obitos_brutos / f"sim_{configuracao.sigla_uf.lower()}_{ano}.parquet"

        def _baixar_filtrado(ano: int = ano) -> pd.DataFrame:
            return manter_residentes_do_sim(obter(configuracao.sigla_uf, ano),
                                            configuracao.prefixo_do_codigo_da_uf)

        _baixar_e_gravar(destino, _baixar_filtrado, configuracao.colunas_dos_obitos,
                         [Bruto.OBITO_CAUSA], configuracao, falhas, f"SIM {ano}")
    return falhas


def baixar_internacoes(configuracao: Configuracao,
                       obter: ObterInternacoes = obter_internacoes_do_pysus) -> list[FalhaDeDownload]:
    falhas: list[FalhaDeDownload] = []
    for ano in configuracao.anos_das_internacoes:
        for mes in range(1, 13):
            destino = configuracao.pasta_das_internacoes_brutas / f"sih_{configuracao.sigla_uf.lower()}_{ano}{mes:02d}.parquet"
            _baixar_e_gravar(destino, lambda ano=ano, mes=mes: obter(configuracao.sigla_uf, ano, mes),
                             configuracao.colunas_das_internacoes,
                             [Bruto.INTERNACAO_DIAGNOSTICO, Bruto.INTERNACAO_DIAGNOSTICO_SECUNDARIO],
                             configuracao, falhas, f"SIH {ano}/{mes:02d}")
    return falhas


def baixar_notificacoes(configuracao: Configuracao,
                        obter: ObterNotificacoes = obter_notificacoes_do_pysus) -> list[FalhaDeDownload]:
    falhas: list[FalhaDeDownload] = []
    for ano in configuracao.anos_dos_obitos:
        destino = configuracao.pasta_do_sinan / f"sinan_{configuracao.sigla_uf.lower()}_{ano}.parquet"
        _baixar_e_gravar(
            destino, lambda ano=ano: manter_residentes_da_uf(obter(ano), configuracao.prefixo_do_codigo_da_uf),
            configuracao.colunas_das_notificacoes, [Bruto.NOTIFICACAO_AGRAVO], configuracao, falhas,
            f"SINAN {ano}", (PREFIXO_DO_AGRAVO_NO_SINAN,))
    return falhas


def _baixar_e_gravar(destino: Path, baixar: Callable[[], pd.DataFrame], colunas: tuple[str, ...],
                     colunas_de_cid: list[str], configuracao: Configuracao,
                     falhas: list[FalhaDeDownload], descricao: str,
                     cids: Optional[tuple[str, ...]] = None) -> None:
    if destino.exists():
        return
    try:
        filtrada = manter_colunas_e_cids_de_interesse(
            baixar(), colunas, colunas_de_cid, cids or configuracao.cids_de_interesse)
    except (OSError, ValueError, KeyError, ConnectionError, ImportError, AttributeError) as erro:
        registro.warning("Falha em %s: %s", descricao, erro)
        falhas.append(FalhaDeDownload(descricao.split()[0], descricao, str(erro)))
        return
    # NOVO: parquet vazio NÃO é gravado — garante que nova execução tente de novo
    if filtrada.empty:
        registro.warning("%s: 0 registros após filtro — não gravando", descricao)
        falhas.append(FalhaDeDownload(descricao.split()[0], descricao, "0 registros após filtro"))
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    filtrada.to_parquet(destino, index=False)
    registro.info("%s: %d registros", descricao, len(filtrada))