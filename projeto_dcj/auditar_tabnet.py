"""Óbitos por categoria CID-10 e ano (bruto e sem duplicatas), no formato do TabNet, para auditar a ingestão."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

from dcj.arquivos import carregar_obitos_brutos
from dcj.colunas import Bruto, Col
from dcj.configuracao import carregar_configuracao
from dcj.limpeza import limpar_obitos

TAMANHO_DA_CATEGORIA = 3
TAMANHO_DO_ANO = 4


def contar_por_categoria_e_ano(causas: pd.Series, anos: pd.Series) -> pd.DataFrame:
    """Cria uma tabela cruzada de CIDs (3 dígitos) por Ano, com uma coluna de total."""
    tabela = pd.crosstab(causas.astype("string").str[:TAMANHO_DA_CATEGORIA], anos.astype("string"))
    tabela = tabela.sort_index(axis=1) # Garante ordem cronológica dos anos
    return tabela.assign(total=tabela.sum(axis=1)).sort_values("total", ascending=False)


def filtrar_causa_basica(tabela: pd.DataFrame, coluna_causa: str, cids: tuple[str, ...]) -> pd.DataFrame:
    """Filtra apenas os óbitos cujo CID está na causa básica (como o TabNet faz)."""
    return tabela[tabela[coluna_causa].astype(str).str.startswith(cids, na=False)]


def contar_brutos(brutos: pd.DataFrame, configuracao) -> pd.DataFrame:
    # O DTOBITO bruto está no formato DDMMYYYY, então pegamos os últimos 4 caracteres
    anos = brutos[Bruto.OBITO_DATA].astype("string").str[-TAMANHO_DO_ANO:]
    # Filtra apenas causa básica para ser comparável ao TabNet
    brutos_filtrados = filtrar_causa_basica(brutos, Bruto.OBITO_CAUSA, configuracao.cids_do_sim)
    return contar_por_categoria_e_ano(brutos_filtrados[Bruto.OBITO_CAUSA], anos)


def contar_sem_duplicatas(limpos: pd.DataFrame) -> pd.DataFrame:
    # Após a limpeza, a data já é datetime, então usamos .dt.year
    return contar_por_categoria_e_ano(limpos[Col.CAUSA_BASICA], limpos[Col.DATA_OBITO].dt.year)


def imprimir_e_salvar(titulo: str, tabela: pd.DataFrame, caminho_saida: Path) -> None:
    print(f"\n=== {titulo} ===")
    print(tabela.to_string())
    tabela.to_csv(caminho_saida)
    print(f"✅ Salvo em: {caminho_saida.name}")


def comparar(pasta_dos_dados: Optional[Path]) -> None:
    configuracao = carregar_configuracao(pasta_dos_dados)
    brutos = carregar_obitos_brutos(configuracao)
    limpos, _ = limpar_obitos(brutos, configuracao)
    
    pasta_resultados = configuracao.pasta_dos_resultados
    pasta_resultados.mkdir(parents=True, exist_ok=True)
    
    imprimir_e_salvar(
        "BRUTO (filtrado por causa básica, com duplicatas)", 
        contar_brutos(brutos, configuracao),
        pasta_resultados / "auditoria_tabnet_bruto.csv"
    )
    imprimir_e_salvar(
        "SEM DUPLICATAS (pipeline, causa básica)", 
        contar_sem_duplicatas(limpos),
        pasta_resultados / "auditoria_tabnet_limpo.csv"
    )


def executar(argumentos: Optional[Sequence[str]] = None) -> None:
    leitor = argparse.ArgumentParser(description="Contagens por categoria CID-10 para comparar com o TabNet")
    leitor.add_argument("--dados", type=Path, help="pasta dos dados (padrão: variável DCJ_DADOS)")
    comparar(leitor.parse_args(argumentos).dados)


if __name__ == "__main__":
    executar()