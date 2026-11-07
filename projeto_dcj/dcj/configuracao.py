from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

from dcj.colunas import Bruto

CriterioDeDesempate = Literal["ultima", "primeira"]
VARIAVEL_DE_AMBIENTE_DOS_DADOS = "DCJ_DADOS"
ROTULO_PRE_PANDEMIA = "Pré-pandemia (2017-2019)"
ROTULO_PANDEMIA = "Pandemia (2020-2022)"
ROTULO_FORA_DA_JANELA = "Fora da janela"


@dataclass(frozen=True)
class RegrasDoEscore:
    cids_genericos: tuple[str, ...] = ("F03", "G309", "G310", "G319", "R54", "I64", "R99")
    pontos_declinio_rapido: int = 40
    pontos_faixa_etaria: int = 30
    pontos_cid_generico: int = 30
    janela_do_declinio_em_dias: tuple[int, int] = (0, 365)
    # Ref.: Boletim DCJ (dcj/referencias.py), p. 12 e 18. Esta faixa privilegia idades abaixo do
    # típico das demências comuns, mas exclui ~44% das notificações suspeitas do país (65+).
    # Esses casos só chegam ao limiar pelo CID genérico; ver comparar_faixas_etarias().
    faixa_etaria_em_anos: tuple[int, int] = (30, 64)
    limiar_de_sinalizacao: int = 70


@dataclass(frozen=True)
class Configuracao:
    pasta_raiz: Path
    sigla_uf: str = "RS"
    prefixo_do_codigo_da_uf: str = "43"
    periodo_pre_pandemia: tuple[int, ...] = (2017, 2018, 2019)
    periodo_pandemia: tuple[int, ...] = (2020, 2021, 2022)
    cids_de_interesse: tuple[str, ...] = ("A81", "F03", "G31", "G93", "R41")
    digitos_do_municipio: int = 6
    exigir_mesmo_municipio: bool = True
    criterio_de_desempate: CriterioDeDesempate = "ultima"
    regras_do_escore: RegrasDoEscore = field(default_factory=RegrasDoEscore)
    numero_de_permutacoes: int = 2000
    semente_aleatoria: int = 42
    populacao_da_uf: Optional[int] = None

    @property
    def anos_dos_obitos(self) -> tuple[int, ...]:
        return self.periodo_pre_pandemia + self.periodo_pandemia

    @property
    def anos_das_internacoes(self) -> tuple[int, ...]:
        return (min(self.anos_dos_obitos) - 1,) + self.anos_dos_obitos

    @property
    def colunas_das_notificacoes(self) -> tuple[str, ...]:
        return (Bruto.NOTIFICACAO_AGRAVO, Bruto.NOTIFICACAO_MUNICIPIO, Bruto.NOTIFICACAO_SEXO,
                Bruto.NOTIFICACAO_ANO_NASCIMENTO, Bruto.NOTIFICACAO_NASCIMENTO,
                Bruto.NOTIFICACAO_PRIMEIROS_SINTOMAS, Bruto.NOTIFICACAO_DATA,
                Bruto.NOTIFICACAO_CLASSIFICACAO_FINAL, Bruto.NOTIFICACAO_EVOLUCAO)

    @property
    def colunas_dos_obitos(self) -> tuple[str, ...]:
        return (Bruto.OBITO_SEXO, Bruto.OBITO_NASCIMENTO, Bruto.OBITO_MUNICIPIO, Bruto.OBITO_DATA,
                Bruto.OBITO_CAUSA, Bruto.OBITO_IDADE, Bruto.OBITO_NUMERO_DA_DECLARACAO)

    @property
    def colunas_das_internacoes(self) -> tuple[str, ...]:
        return (Bruto.INTERNACAO_SEXO, Bruto.INTERNACAO_NASCIMENTO, Bruto.INTERNACAO_MUNICIPIO,
                Bruto.INTERNACAO_DATA, Bruto.INTERNACAO_DIAGNOSTICO,
                Bruto.INTERNACAO_DIAGNOSTICO_SECUNDARIO, Bruto.INTERNACAO_NUMERO_DA_AIH)

    @property
    def pasta_dos_obitos_brutos(self) -> Path:
        return self.pasta_raiz / "sim"

    @property
    def pasta_das_internacoes_brutas(self) -> Path:
        return self.pasta_raiz / "sih"

    @property
    def pasta_do_sinan(self) -> Path:
        return self.pasta_raiz / "sinan"

    @property
    def pasta_dos_processados(self) -> Path:
        return self.pasta_raiz / "processado"

    @property
    def pasta_dos_resultados(self) -> Path:
        return self.pasta_raiz / "resultados"

    def arquivo_processado(self, nome: str) -> Path:
        return self.pasta_dos_processados / f"{nome}.parquet"

    def arquivo_de_resultado(self, nome: str) -> Path:
        return self.pasta_dos_resultados / f"{nome}.csv"


def carregar_configuracao(pasta_raiz: Optional[Path] = None) -> Configuracao:
    """A pasta vem do argumento, da variável DCJ_DADOS ou do padrão ./dados_rs_drp."""
    origem = pasta_raiz or Path(os.environ.get(VARIAVEL_DE_AMBIENTE_DOS_DADOS, "dados_rs_drp"))
    return Configuracao(pasta_raiz=origem.expanduser().resolve())
