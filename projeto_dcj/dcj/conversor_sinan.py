"""Converte os .dbc nacionais do SINAN (DCRJBRAA.dbc) em sinan_<uf>_AAAA.parquet, só com residentes da UF.

Uso: python -m dcj.conversor_sinan [--dados PASTA]  (lê e grava em <PASTA>/sinan). Precisa de pyreaddbc e dbf."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

from dcj.armazenamento import salvar_parquet
from dcj.colunas import Bruto
from dcj.configuracao import Configuracao, carregar_configuracao
from dcj.ingestao import PREFIXO_DO_AGRAVO_NO_SINAN, manter_colunas_e_cids_de_interesse, manter_residentes_da_uf

registro = logging.getLogger(__name__)
RESIDENCIA_DUPLICADA = "ID_MN_RESI_2"


def renomear_campos_duplicados(campos: list[str]) -> list[str]:
    """O DBF pode repetir nomes; a primeira ocorrência fica como está e as seguintes ganham _2, _3..."""
    ocorrencias: dict[str, int] = {}
    nomes: list[str] = []
    for campo in campos:
        ocorrencias[campo] = ocorrencias.get(campo, 0) + 1
        nomes.append(campo if ocorrencias[campo] == 1 else f"{campo}_{ocorrencias[campo]}")
    return nomes


def resolver_residencia_duplicada(tabela: pd.DataFrame) -> pd.DataFrame:
    """Hipótese a conferir: com o campo repetido, a segunda ocorrência é o município de residência."""
    if RESIDENCIA_DUPLICADA not in tabela.columns:
        return tabela
    registro.warning("ID_MN_RESI repetido no DBF: assumindo a segunda ocorrência como residência; confira as contagens")
    return tabela.rename(columns={"ID_MN_RESI": "ID_MN_RESI_1", RESIDENCIA_DUPLICADA: "ID_MN_RESI"})


def padronizar_tabela(tabela: pd.DataFrame) -> pd.DataFrame:
    resolvida = resolver_residencia_duplicada(tabela)
    resolvida.columns = [str(coluna).upper().strip() for coluna in resolvida.columns]
    colunas_de_texto = [coluna for coluna in resolvida.columns if pd.api.types.is_object_dtype(resolvida[coluna])]
    return resolvida.astype({coluna: "string" for coluna in colunas_de_texto})


def ler_tabela_dbf(caminho: Path) -> pd.DataFrame:
    import dbf
    tabela = dbf.Table(str(caminho))
    tabela.open(mode=dbf.READ_ONLY)
    try:
        return pd.DataFrame([list(linha) for linha in tabela],
                            columns=renomear_campos_duplicados(list(tabela.field_names)))
    finally:
        tabela.close()


def converter_dbc_em_tabela(caminho_dbc: Path) -> pd.DataFrame:
    import pyreaddbc
    caminho_dbf = caminho_dbc.with_suffix(".dbf")
    pyreaddbc.dbc2dbf(str(caminho_dbc), str(caminho_dbf))
    try:
        return ler_tabela_dbf(caminho_dbf)
    finally:
        caminho_dbf.unlink(missing_ok=True)


def converter_ano(pasta: Path, ano: int, configuracao: Configuracao) -> Optional[Path]:
    arquivo_dbc = pasta / f"DCRJBR{ano % 100:02d}.dbc"
    if not arquivo_dbc.exists():
        registro.warning("Sem %s: ano %d ignorado", arquivo_dbc.name, ano)
        return None
    nacional = padronizar_tabela(converter_dbc_em_tabela(arquivo_dbc))
    residentes = manter_residentes_da_uf(nacional, configuracao.prefixo_do_codigo_da_uf)
    reduzida = manter_colunas_e_cids_de_interesse(
        residentes, configuracao.colunas_das_notificacoes, [Bruto.NOTIFICACAO_AGRAVO], (PREFIXO_DO_AGRAVO_NO_SINAN,))
    destino = pasta / f"sinan_{configuracao.sigla_uf.lower()}_{ano}.parquet"
    salvar_parquet(reduzida, destino)
    registro.info("%d: %d no Brasil, %d residentes de %s", ano, len(nacional), len(reduzida), configuracao.sigla_uf)
    return destino


def converter_pasta(configuracao: Configuracao) -> list[Path]:
    gravados = (converter_ano(configuracao.pasta_do_sinan, ano, configuracao) for ano in configuracao.anos_dos_obitos)
    return [caminho for caminho in gravados if caminho is not None]


def executar_conversao(argumentos: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    leitor = argparse.ArgumentParser(prog="python -m dcj.conversor_sinan")
    leitor.add_argument("--dados", type=Path, help="pasta dos dados (padrão: variável DCJ_DADOS)")
    configuracao = carregar_configuracao(leitor.parse_args(argumentos).dados)
    return 0 if converter_pasta(configuracao) else 1


if __name__ == "__main__":
    raise SystemExit(executar_conversao())
