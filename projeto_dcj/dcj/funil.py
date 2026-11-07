from __future__ import annotations

from typing import Callable

import pandas as pd

Transformacao = Callable[[pd.DataFrame], pd.DataFrame]


class Funil:
    """Registra quantas linhas restam após cada etapa de limpeza."""

    def __init__(self) -> None:
        self._etapas: list[dict[str, object]] = []

    def registrar(self, nome_da_etapa: str, tabela: pd.DataFrame) -> None:
        total = len(tabela)
        total_inicial = self._etapas[0]["registros"] if self._etapas else total
        total_anterior = self._etapas[-1]["registros"] if self._etapas else total
        self._etapas.append({
            "etapa": nome_da_etapa,
            "registros": total,
            "percentual_do_bruto": round(100 * total / total_inicial, 2) if total_inicial else 0.0,
            "removidos_na_etapa": total_anterior - total,
        })

    def aplicar(self, nome_da_etapa: str, tabela: pd.DataFrame, transformacao: Transformacao) -> pd.DataFrame:
        resultado = transformacao(tabela)
        self.registrar(nome_da_etapa, resultado)
        return resultado

    def como_tabela(self) -> pd.DataFrame:
        return pd.DataFrame(self._etapas)
