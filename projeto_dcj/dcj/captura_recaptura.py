"""Captura-recaptura (Chapman) entre duas fontes, como análise de SENSIBILIDADE e não como estimativa populacional.

Hipóteses do modelo: população fechada, pareamento sem erro e fontes independentes. Aqui nenhuma é garantida: o
pareamento perde pares (parte das notificações não tem data de óbito) e as fontes são positivamente dependentes
(quem é notificado tende a ter a causa A81.0 no SIM). Dependência positiva faz o modelo de independência
SUBESTIMAR o total; por isso a tabela varia a razão de chances entre as fontes."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

NIVEL_Z_DE_95_POR_CENTO = 1.96
RAZOES_DE_CHANCES_PADRAO = (0.5, 1.0, 2.0, 3.0)


@dataclass(frozen=True)
class DuasListas:
    total_da_primeira: int
    total_da_segunda: int
    em_ambas: int

    def __post_init__(self) -> None:
        if self.em_ambas < 0 or self.em_ambas > min(self.total_da_primeira, self.total_da_segunda):
            raise ValueError("em_ambas deve estar entre 0 e o menor total das duas listas")

    @property
    def so_na_primeira(self) -> int:
        return self.total_da_primeira - self.em_ambas

    @property
    def so_na_segunda(self) -> int:
        return self.total_da_segunda - self.em_ambas

    @property
    def observados(self) -> int:
        return self.total_da_primeira + self.total_da_segunda - self.em_ambas


def estimar_por_chapman(listas: DuasListas) -> float:
    return (listas.total_da_primeira + 1) * (listas.total_da_segunda + 1) / (listas.em_ambas + 1) - 1


def calcular_variancia_de_chapman(listas: DuasListas) -> float:
    numerador = ((listas.total_da_primeira + 1) * (listas.total_da_segunda + 1)
                 * listas.so_na_primeira * listas.so_na_segunda)
    return numerador / ((listas.em_ambas + 1) ** 2 * (listas.em_ambas + 2))


def calcular_intervalo_de_confianca(listas: DuasListas, nivel_z: float = NIVEL_Z_DE_95_POR_CENTO) -> tuple[float, float]:
    """Aproximação normal de Seber; o limite inferior nunca fica abaixo do total já observado."""
    estimativa = estimar_por_chapman(listas)
    margem = nivel_z * calcular_variancia_de_chapman(listas) ** 0.5
    return max(estimativa - margem, float(listas.observados)), estimativa + margem


def estimar_com_dependencia(listas: DuasListas, razao_de_chances: float) -> float:
    """Multiplica a parcela não observada do Chapman pela razão de chances entre as fontes (1 = independência)."""
    if razao_de_chances <= 0:
        raise ValueError("razao_de_chances deve ser positiva")
    nao_observados = estimar_por_chapman(listas) - listas.observados
    return listas.observados + razao_de_chances * nao_observados


def ajustar_pares_pelo_acaso(pares_observados: int, pares_esperados_ao_acaso: float) -> int:
    """Pares da chave fraca incluem coincidências demográficas; a permutação estima quantas."""
    return max(round(pares_observados - pares_esperados_ao_acaso), 0)


def extrapolar_pares_pela_cobertura_da_data(pares_com_data: int, notificacoes_com_data: int, notificacoes: int) -> int:
    """Supõe que a data de óbito do SINAN falta ao acaso; se faltar mais entre os não-óbitos, superestima os pares."""
    if notificacoes_com_data <= 0:
        raise ValueError("notificacoes_com_data deve ser positivo")
    return round(pares_com_data * notificacoes / notificacoes_com_data)


def _linha_do_cenario(nome: str, listas: DuasListas, razoes_de_chances: tuple[float, ...]) -> dict[str, object]:
    inferior, superior = calcular_intervalo_de_confianca(listas)
    linha: dict[str, object] = {
        "cenario": nome, "total_sinan": listas.total_da_primeira, "total_sim": listas.total_da_segunda,
        "em_ambas": listas.em_ambas, "observados": listas.observados,
        "chapman": round(estimar_por_chapman(listas)), "ic95_inferior": round(inferior), "ic95_superior": round(superior)}
    for razao in razoes_de_chances:
        linha[f"razao_{razao:g}"] = round(estimar_com_dependencia(listas, razao))
    return linha


def montar_tabela_de_sensibilidade(cenarios: dict[str, DuasListas],
                                   razoes_de_chances: tuple[float, ...] = RAZOES_DE_CHANCES_PADRAO) -> pd.DataFrame:
    return pd.DataFrame([_linha_do_cenario(nome, listas, razoes_de_chances) for nome, listas in cenarios.items()])
