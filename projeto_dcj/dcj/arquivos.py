from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from dcj.colunas import Bruto
from dcj.configuracao import Configuracao
from dcj.erros import ArquivosNaoEncontradosError


def listar_arquivos_por_padrao(pasta: Path, padrao: str) -> list[Path]:
    """Só aceita nomes que casam INTEIRO com o padrão, para nunca ler um arquivo consolidado."""
    regex = re.compile(padrao)
    return sorted(caminho for caminho in pasta.glob("*.parquet") if regex.fullmatch(caminho.name))


def ler_arquivos_com_origem(caminhos: list[Path]) -> pd.DataFrame:
    tabelas = [pd.read_parquet(caminho).assign(**{Bruto.ORIGEM_DO_ARQUIVO: caminho.name})
               for caminho in caminhos]
    return pd.concat(tabelas, ignore_index=True)


def _carregar_ou_falhar(pasta: Path, padrao: str) -> pd.DataFrame:
    caminhos = listar_arquivos_por_padrao(pasta, padrao)
    if not caminhos:
        raise ArquivosNaoEncontradosError(f"Nenhum arquivo '{padrao}' em {pasta}")
    return ler_arquivos_com_origem(caminhos)


def carregar_obitos_brutos(configuracao: Configuracao) -> pd.DataFrame:
    sigla = configuracao.sigla_uf.lower()
    return _carregar_ou_falhar(configuracao.pasta_dos_obitos_brutos, rf"sim_{sigla}_\d{{4}}\.parquet")


def carregar_internacoes_brutas(configuracao: Configuracao) -> pd.DataFrame:
    sigla = configuracao.sigla_uf.lower()
    return _carregar_ou_falhar(configuracao.pasta_das_internacoes_brutas, rf"sih_{sigla}_\d{{6}}\.parquet")


def carregar_notificacoes_brutas(configuracao: Configuracao) -> pd.DataFrame:
    return _carregar_ou_falhar(configuracao.pasta_do_sinan, padrao_das_notificacoes(configuracao))


def padrao_das_notificacoes(configuracao: Configuracao) -> str:
    return rf"sinan_{configuracao.sigla_uf.lower()}_\d{{4}}\.parquet"


def existem_notificacoes_brutas(configuracao: Configuracao) -> bool:
    return bool(listar_arquivos_por_padrao(configuracao.pasta_do_sinan, padrao_das_notificacoes(configuracao)))
