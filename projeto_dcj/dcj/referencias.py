"""Referência epidemiológica usada para justificar regras do escore e validar contagens.

Fonte: Ministério da Saúde, Secretaria de Vigilância em Saúde. Boletim Epidemiológico, v. 53,
n. 39, out. 2022. "Perfil epidemiológico de casos da doença de Creutzfeldt-Jakob (DCJ) no Brasil,
2005 a 2021", p. 12-22. Páginas citadas abaixo são as impressas no boletim.

Atenção: os percentuais por faixa etária, classificação e evolução vêm de 1.576 NOTIFICAÇÕES
SUSPEITAS do Sinan, não de casos confirmados. A Tabela 1 do boletim (confirmados por UF) tem
rótulos de UF que não batem com o texto e por isso não é usada aqui.
"""
from __future__ import annotations

from dataclasses import dataclass

CITACAO_DO_BOLETIM = (
    "Brasil. Ministério da Saúde. Secretaria de Vigilância em Saúde. Boletim Epidemiológico, "
    "v. 53, n. 39, out. 2022. Perfil epidemiológico de casos da doença de Creutzfeldt-Jakob "
    "(DCJ) no Brasil, 2005 a 2021."
)
CID_DA_DCJ = "A810"
IDADE_MAXIMA_PLAUSIVEL = 120


@dataclass(frozen=True)
class ReferenciaDoBoletimDcj:
    mortes_por_milhao_por_ano: tuple[float, float] = (1.0, 2.0)  # p. 12
    sobrevida_media_em_meses: int = 5  # p. 12
    faixa_de_maior_incidencia_na_literatura: tuple[int, int] = (55, 70)  # p. 12, média de 65 anos
    faixa_etaria_de_maior_notificacao: tuple[int, int] = (55, 74)  # p. 18, 60,2% das notificações
    percentual_de_notificacoes_com_65_anos_ou_mais: float = 44.2  # soma 65-74, 75-85 e >85 da Tabela 2, p. 21
    queda_das_notificacoes_em_2020_percentual: float = 21.3  # p. 20
    notificacoes_sem_classificacao_final_percentual: float = 36.3  # p. 15
    notificacoes_sem_evolucao_percentual: float = 55.8  # p. 17


REFERENCIA_DO_BOLETIM = ReferenciaDoBoletimDcj()


def calcular_obitos_esperados_por_ano(populacao: int,
                                      referencia: ReferenciaDoBoletimDcj = REFERENCIA_DO_BOLETIM
                                      ) -> tuple[float, float]:
    """Faixa de óbitos anuais por DCJ esperada para uma população (1 a 2 por milhão)."""
    if populacao <= 0:
        raise ValueError("A população deve ser positiva.")
    minimo, maximo = referencia.mortes_por_milhao_por_ano
    return populacao / 1_000_000 * minimo, populacao / 1_000_000 * maximo
