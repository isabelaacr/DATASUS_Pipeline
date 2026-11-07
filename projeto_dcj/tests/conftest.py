from __future__ import annotations

import pandas as pd
import pytest

from dcj.colunas import Col
from dcj.configuracao import Configuracao

try:
    import pyarrow  # noqa: F401
except ImportError:  # ambiente sem parquet: simula com pickle só para os testes
    pd.DataFrame.to_parquet = lambda self, caminho, index=False, **_: self.to_pickle(str(caminho))
    pd.read_parquet = lambda caminho, **_: pd.read_pickle(str(caminho))


@pytest.fixture
def configuracao(tmp_path) -> Configuracao:
    return Configuracao(pasta_raiz=tmp_path, numero_de_permutacoes=200)


def criar_obitos_limpos(*linhas: dict) -> pd.DataFrame:
    padrao = {Col.MUNICIPIO: "431490", Col.SEXO: "M", Col.IDADE_ANOS: 60.0, Col.CAUSA_BASICA: "G311"}
    tabela = pd.DataFrame([{**padrao, **linha} for linha in linhas])
    for coluna in (Col.DATA_NASCIMENTO, Col.DATA_OBITO):
        tabela[coluna] = pd.to_datetime(tabela[coluna])
    tabela[Col.ANO_NASCIMENTO] = tabela[Col.DATA_NASCIMENTO].dt.year
    tabela[Col.MES_DIA_NASCIMENTO] = tabela[Col.DATA_NASCIMENTO].dt.strftime("%m%d")
    return tabela


def criar_internacoes_limpas(*linhas: dict) -> pd.DataFrame:
    padrao = {Col.MUNICIPIO: "431490", Col.SEXO: "M", Col.DIAGNOSTICO_PRINCIPAL: "G318"}
    tabela = pd.DataFrame([{**padrao, **linha} for linha in linhas])
    for coluna in (Col.DATA_NASCIMENTO, Col.DATA_INTERNACAO):
        tabela[coluna] = pd.to_datetime(tabela[coluna])
    tabela[Col.ANO_NASCIMENTO] = tabela[Col.DATA_NASCIMENTO].dt.year
    tabela[Col.MES_DIA_NASCIMENTO] = tabela[Col.DATA_NASCIMENTO].dt.strftime("%m%d")
    return tabela
