from __future__ import annotations

from pathlib import Path

import pandas as pd

from dcj.erros import ArquivosNaoEncontradosError


def salvar_parquet(tabela: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_parquet(caminho, index=False)


def salvar_csv(tabela: pd.DataFrame, caminho: Path, manter_indice: bool = False) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(caminho, index=manter_indice)


def ler_parquet_da_etapa_anterior(caminho: Path, etapa_anterior: str) -> pd.DataFrame:
    if not caminho.exists():
        raise ArquivosNaoEncontradosError(f"{caminho} não existe. Rode antes a etapa '{etapa_anterior}'.")
    return pd.read_parquet(caminho)
