"""Funções puras que padronizam colunas do DATASUS. Nenhuma lê ou grava arquivo."""
from __future__ import annotations

import numpy as np
import pandas as pd

MAPA_SEXO_DOS_OBITOS = {"1": "M", "M": "M", "MASCULINO": "M", "2": "F", "F": "F", "FEMININO": "F"}
# No SIH o código feminino é 3 (no SIM é 2); o 2 é aceito por segurança.
MAPA_SEXO_DAS_INTERNACOES = {**MAPA_SEXO_DOS_OBITOS, "3": "F"}
UNIDADES_DE_IDADE_MENOR_QUE_UM_ANO = ("0", "1", "2", "3")
UNIDADE_DE_IDADE_EM_ANOS = "4"
UNIDADE_DE_IDADE_CENTENARIA = "5"
LARGURA_DA_DATA_DDMMAAAA = 8
LARGURA_DO_CODIGO_DE_IDADE = 3


def limpar_texto_numerico(valores: pd.Series) -> pd.Series:
    """Remove espaços e o sufixo '.0' que o parquet acrescenta a inteiros lidos como float."""
    return valores.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def padronizar_codigo_municipio(codigos: pd.Series, digitos: int) -> pd.Series:
    return limpar_texto_numerico(codigos).str.zfill(6).str[:digitos]


def padronizar_cid(cids: pd.Series) -> pd.Series:
    return cids.astype("string").str.upper().str.replace(".", "", regex=False).str.strip()


def padronizar_sexo(valores: pd.Series, mapa: dict[str, str]) -> pd.Series:
    texto = limpar_texto_numerico(valores).str.upper()
    return texto.astype("object").map(mapa)


def converter_data_ddmmaaaa(textos: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(textos):
        return textos
    preenchidos = limpar_texto_numerico(textos).str.zfill(LARGURA_DA_DATA_DDMMAAAA)
    return pd.to_datetime(preenchidos, format="%d%m%Y", errors="coerce")


def converter_data_aaaammdd(textos: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(textos):
        return textos
    return pd.to_datetime(limpar_texto_numerico(textos), format="%Y%m%d", errors="coerce")


def decodificar_idade_em_anos(codigos: pd.Series) -> pd.Series:
    """Código do SIM: 4xx = anos, 5xx = 100 + xx anos, 0xx a 3xx = menos de 1 ano."""
    texto = limpar_texto_numerico(codigos).str.zfill(LARGURA_DO_CODIGO_DE_IDADE)
    unidade = texto.str[0].fillna("").to_numpy(dtype=object)
    valor = pd.to_numeric(texto.str[1:], errors="coerce").to_numpy(dtype=float)
    anos = np.select(
        [unidade == UNIDADE_DE_IDADE_EM_ANOS, unidade == UNIDADE_DE_IDADE_CENTENARIA,
         np.isin(unidade, UNIDADES_DE_IDADE_MENOR_QUE_UM_ANO)],
        [valor, 100 + valor, 0.0], default=np.nan)
    return pd.Series(anos, index=codigos.index)
