from __future__ import annotations

from typing import Iterable

import pandas as pd


class ErroDoPipeline(Exception):
    """Base de todos os erros previstos do pipeline."""


class ArquivosNaoEncontradosError(ErroDoPipeline):
    pass


class ColunasAusentesError(ErroDoPipeline):
    pass


def garantir_colunas(tabela: pd.DataFrame, colunas: Iterable[str], contexto: str) -> None:
    ausentes = [coluna for coluna in colunas if coluna not in tabela.columns]
    if ausentes:
        raise ColunasAusentesError(f"{contexto}: colunas ausentes {ausentes}")
