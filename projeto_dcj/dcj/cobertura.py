"""Diagnóstico das bases: o que a ingestão trouxe de errado e se os anos são comparáveis."""
from __future__ import annotations

from typing import Sequence

import pandas as pd

from dcj.colunas import Bruto, Col
from dcj.configuracao import Configuracao
from dcj.padronizacao import limpar_texto_numerico
from dcj.referencias import CID_DA_DCJ, calcular_obitos_esperados_por_ano

LARGURA_DO_CODIGO_DO_MUNICIPIO = 6
TAMANHO_DO_PREFIXO_DA_UF = 2


def calcular_codigos_de_uf(obitos_brutos: pd.DataFrame) -> pd.Series:
    municipios = limpar_texto_numerico(obitos_brutos[Bruto.OBITO_MUNICIPIO]).str.zfill(LARGURA_DO_CODIGO_DO_MUNICIPIO)
    return municipios.str[:TAMANHO_DO_PREFIXO_DA_UF]


def contar_declaracoes_com_a810_discordante(
    obitos: pd.DataFrame, chave: list[str], linhas: Sequence[str]
) -> int:
    """Conta declarações em que o A81.0 está presente em uma cópia mas não na outra.
    
    Uma cópia discordante é uma declaração em que o código A81.0 aparece nas linhas 
    da declaração (LINHAA-D) ou na causa básica em uma cópia, mas não na outra.
    """
    chave_existente = [c for c in chave if c in obitos.columns]
    colunas_linhas = [c for c in linhas if c in obitos.columns]
    
    if not chave_existente:
        return 0
    
    # Marca A810 na causa básica
    tem_a810_basica = obitos[Bruto.OBITO_CAUSA].astype(str).str.startswith("A810", na=False)
    
    # Marca A810 em qualquer uma das linhas da declaração
    if colunas_linhas:
        tem_a810_linhas = obitos[colunas_linhas].astype("string").apply(
            lambda col: col.str.contains("A810", na=False)).any(axis=1)
    else:
        tem_a810_linhas = pd.Series(False, index=obitos.index)
    
    tem_a810 = tem_a810_basica | tem_a810_linhas
    
    por_declaracao = (obitos.assign(tem_a810=tem_a810)
                      .groupby(chave_existente, dropna=False)["tem_a810"]
                      .agg(["min", "max", "size"]))
    
    return int(((por_declaracao["size"] > 1) & (por_declaracao["min"] != por_declaracao["max"])).sum())


def auditar_obitos_brutos(obitos_brutos: pd.DataFrame, configuracao: Configuracao) -> dict[str, object]:
    colunas_de_dados = [coluna for coluna in obitos_brutos.columns if coluna != Bruto.ORIGEM_DO_ARQUIVO]
    ufs = calcular_codigos_de_uf(obitos_brutos)
    return {
        "linhas_brutas": len(obitos_brutos),
        "duplicatas_integrais": int(obitos_brutos.duplicated(subset=colunas_de_dados).sum()),
        "declaracoes_com_a810_discordante": contar_declaracoes_com_a810_discordante(
            obitos_brutos, configuracao.colunas_dos_obitos, Bruto.OBITO_LINHAS_DA_DECLARACAO
        ),
        "percentual_de_residentes_da_uf": round(100 * float((ufs == configuracao.prefixo_do_codigo_da_uf).mean()), 1),
        "ufs_de_residencia_mais_comuns": (100 * ufs.value_counts(normalize=True).head(5)).round(1).to_dict(),
        "linhas_por_arquivo": obitos_brutos[Bruto.ORIGEM_DO_ARQUIVO].value_counts().sort_index().to_dict(),
    }


def calcular_cobertura_por_ano(obitos: pd.DataFrame, internacoes: pd.DataFrame) -> pd.DataFrame:
    """Colunas *_sobre_mediana longe de 1,0 indicam ano com cobertura anômala."""
    obitos_por_ano = obitos[Col.DATA_OBITO].dt.year.value_counts().rename("obitos")
    internacoes_por_ano = internacoes[Col.DATA_INTERNACAO].dt.year.value_counts().rename("internacoes")
    tabela = pd.concat([obitos_por_ano, internacoes_por_ano], axis=1).fillna(0).astype(int).sort_index()
    for coluna in ("obitos", "internacoes"):
        tabela[f"{coluna}_sobre_mediana"] = (tabela[coluna] / tabela[coluna].median()).round(2)
    return tabela


def contar_dcj_fora_da_causa_basica(obitos: pd.DataFrame) -> pd.DataFrame:
    """Óbitos com A81.0 em alguma linha da declaração, separados pela causa básica: os da coluna
    `dcj_so_em_causa_associada` são mascaramento documentado na própria declaração."""
    basica = obitos[Col.CAUSA_BASICA].str.startswith(CID_DA_DCJ, na=False)
    associada = obitos[Col.DCJ_NA_DECLARACAO] & ~basica
    ano = obitos[Col.DATA_OBITO].dt.year.rename("ano")
    tabela = pd.DataFrame({"dcj_causa_basica": basica, "dcj_so_em_causa_associada": associada}).groupby(ano).sum()
    tabela["causas_basicas_dos_associados"] = (
        obitos[associada].groupby(ano[associada])[Col.CAUSA_BASICA].agg(lambda c: ", ".join(sorted(set(c)))))
    return tabela.fillna({"causas_basicas_dos_associados": ""})

def comparar_obitos_por_dcj_com_esperado(obitos: pd.DataFrame, populacao: int) -> pd.DataFrame:
    """Ref.: Boletim DCJ, p. 12 (1 a 2 mortes por milhão por ano). Valores abaixo do mínimo esperado
    são compatíveis com mascaramento diagnóstico, mas também com cobertura incompleta do SIM."""
    minimo, maximo = calcular_obitos_esperados_por_ano(populacao)
    eh_dcj = obitos[Col.CAUSA_BASICA].str.startswith(CID_DA_DCJ, na=False)
    por_ano = obitos[eh_dcj][Col.DATA_OBITO].dt.year.value_counts().sort_index().rename("obitos_a810_observados").rename_axis("ano")
    tabela = por_ano.to_frame().assign(esperado_minimo=round(minimo, 1), esperado_maximo=round(maximo, 1))
    tabela["abaixo_do_minimo_esperado"] = tabela["obitos_a810_observados"] < minimo
    return tabela