"""Gera bases BRUTAS sintéticas com os defeitos dos dados reais: outras UFs, linhas duplicadas,
ano fora da janela, arquivo consolidado na pasta e sexo codificado de forma diferente no SIH."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

MUNICIPIOS_DO_RS = [f"43{numero:04d}" for numero in range(1000, 1030)]


@dataclass(frozen=True)
class PessoaSintetica:
    nascimento: pd.Timestamp
    obito: pd.Timestamp
    internacao: pd.Timestamp
    municipio: str
    sexo: str


def sortear_data(gerador: np.random.Generator, inicio: str, dias: int) -> pd.Timestamp:
    return pd.Timestamp(inicio) + pd.Timedelta(days=int(gerador.integers(0, dias)))


def sortear_pessoa(gerador: np.random.Generator) -> PessoaSintetica:
    obito = sortear_data(gerador, "2017-03-01", 365 * 5 + 200)
    return PessoaSintetica(
        nascimento=sortear_data(gerador, "1925-01-01", 365 * 65), obito=obito,
        internacao=obito - pd.Timedelta(days=int(gerador.integers(10, 300))),
        municipio=str(gerador.choice(MUNICIPIOS_DO_RS)), sexo=str(gerador.choice(["M", "F"])))


def linha_de_obito(pessoa: PessoaSintetica, gerador: np.random.Generator) -> dict:
    idade = int((pessoa.obito - pessoa.nascimento).days // 365.25)
    return {"SEXO": "1" if pessoa.sexo == "M" else "2", "DTNASC": pessoa.nascimento.strftime("%d%m%Y"),
            "CODMUNRES": pessoa.municipio, "DTOBITO": pessoa.obito.strftime("%d%m%Y"),
            "CAUSABAS": str(gerador.choice(["G311", "G319", "F03", "A810"])),
            "IDADE": f"4{min(idade, 99):02d}", "NUMERODO": str(gerador.integers(10**8, 10**9))}


def linha_de_internacao(pessoa: PessoaSintetica, numero_da_aih: str, gerador: np.random.Generator) -> dict:
    return {"SEXO": "1" if pessoa.sexo == "M" else "3", "NASC": pessoa.nascimento.strftime("%Y%m%d"),
            "MUNIC_RES": pessoa.municipio, "DT_INTER": pessoa.internacao.strftime("%Y%m%d"),
            "DIAG_PRINC": str(gerador.choice(["G318", "F03", "G936"])), "DIAG_SECUN": "", "N_AIH": numero_da_aih}


def montar_obitos(pessoas_reais: list[PessoaSintetica], ruido: list[PessoaSintetica],
                  gerador: np.random.Generator) -> pd.DataFrame:
    obitos = pd.DataFrame([linha_de_obito(p, gerador) for p in pessoas_reais + ruido])
    de_outras_ufs = obitos.sample(150, random_state=1).assign(
        CODMUNRES=lambda t: [f"35{n:04d}" for n in range(len(t))], NUMERODO=lambda t: [f"X{n}" for n in range(len(t))])
    duplicatas = obitos.sample(100, random_state=2)
    return pd.concat([obitos, de_outras_ufs, duplicatas], ignore_index=True)


def gravar_obitos_por_ano(obitos: pd.DataFrame, pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    anos = pd.to_datetime(obitos["DTOBITO"], format="%d%m%Y").dt.year
    for ano in range(2017, 2023):
        obitos[anos == ano].to_parquet(pasta / f"sim_rs_{ano}.parquet", index=False)
    obitos.iloc[:8].assign(DTOBITO="10012023").to_parquet(pasta / "sim_rs_2023.parquet", index=False)
    obitos.to_parquet(pasta / "sim_rs_PRONTO_LINKAGE.parquet", index=False)


def gravar_internacoes_por_mes(internacoes: pd.DataFrame, pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    meses = pd.to_datetime(internacoes["DT_INTER"], format="%Y%m%d").dt.strftime("%Y%m")
    for mes, grupo in internacoes.groupby(meses):
        grupo.to_parquet(pasta / f"sih_rs_{mes}.parquet", index=False)


def gerar_dados_brutos(raiz: Path, quantidade_de_pares: int = 40, ruido_por_base: int = 400,
                       semente: int = 0) -> list[PessoaSintetica]:
    gerador = np.random.default_rng(semente)
    reais = [sortear_pessoa(gerador) for _ in range(quantidade_de_pares)]
    ruido_obitos = [sortear_pessoa(gerador) for _ in range(ruido_por_base)]
    ruido_internacoes = [sortear_pessoa(gerador) for _ in range(ruido_por_base)]
    gravar_obitos_por_ano(montar_obitos(reais, ruido_obitos, gerador), raiz / "sim")
    linhas = [linha_de_internacao(p, f"R{n:05d}", gerador) for n, p in enumerate(reais)]
    linhas += [linha_de_internacao(p, f"S{n:05d}", gerador) for n, p in enumerate(ruido_internacoes)]
    internacoes = pd.DataFrame(linhas)
    gravar_internacoes_por_mes(pd.concat([internacoes, internacoes.sample(20, random_state=3)], ignore_index=True),
                               raiz / "sih")
    return reais
