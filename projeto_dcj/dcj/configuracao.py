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
    
    # Sobrevida média da DCJ ~5 meses (Boletim DCJ, SVS/MS, 2022): até 180 dias pontua cheio.
    pontos_do_declinio_por_limite_em_dias: tuple[tuple[int, int], ...] = ((180, 40), (365, 20))
    
    pontos_faixa_etaria: int = 30
    pontos_cid_generico: int = 30
    
    # Pico de notificações de DCJ (Boletim DCJ, p. 12 e 18); a faixa 30-64 anterior excluía os idosos.
    faixa_etaria_em_anos: tuple[int, int] = (55, 74)
    
    limiar_de_sinalizacao: int = 70

    def __post_init__(self) -> None:
        # Valida que os limites estão em ordem crescente (evita bugs silenciosos no np.select)
        limites = [limite for limite, _ in self.pontos_do_declinio_por_limite_em_dias]
        if limites != sorted(set(limites)):
            raise ValueError("Os limites do declínio devem ser crescentes e sem repetição.")
        
        # Valida que a faixa etária é coerente
        minimo, maximo = self.faixa_etaria_em_anos
        if minimo > maximo:
            raise ValueError("A faixa etária deve ter mínimo menor ou igual ao máximo.")


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
                Bruto.NOTIFICACAO_OBITO,
                Bruto.NOTIFICACAO_CLASSIFICACAO_FINAL, Bruto.NOTIFICACAO_EVOLUCAO)

    @property
    def colunas_dos_obitos(self) -> tuple[str, ...]:
        return (Bruto.OBITO_SEXO, Bruto.OBITO_NASCIMENTO, Bruto.OBITO_MUNICIPIO, Bruto.OBITO_DATA,
                Bruto.OBITO_CAUSA, Bruto.OBITO_IDADE, Bruto.OBITO_NUMERO_DA_DECLARACAO)

    @property
    def colunas_do_download_dos_obitos(self) -> tuple[str, ...]:
        """As linhas da declaração entram no download, mas não são obrigatórias na limpeza (parquets antigos)."""
        return self.colunas_dos_obitos + Bruto.OBITO_LINHAS_DA_DECLARACAO

    @property
    def cids_do_sim(self) -> tuple[str, ...]:
        """CIDs de interesse + todos os CIDs genéricos do escore; sem isso G30.9, R54, I64 e R99 nunca pontuam.
        O SIH continua com cids_de_interesse para não inflar o volume de internações por AVC e senilidade."""
        extras = tuple(cid for cid in self.regras_do_escore.cids_genericos
                       if not cid.startswith(self.cids_de_interesse))
        return self.cids_de_interesse + extras

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