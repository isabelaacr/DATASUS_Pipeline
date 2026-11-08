"""Monta, a partir dos dados, os cenários de captura-recaptura SINAN x SIM (A81.0). Nenhuma contagem é fixa.

O número de pares (`m`) é a parte frágil do Chapman, por isso há três formas de obtê-lo:
- chave forte: município, sexo, ano de nascimento E data de óbito do SINAN a até 30 dias da do SIM. Só é testável
  nas notificações que têm a data; as demais ficam de fora, o que SUBESTIMA `m` e infla o total;
- chave forte extrapolada: escala `m` pela fração de notificações com data (supõe que a data falta ao acaso);
- chave fraca descontando o acaso: a chave sem data gera coincidências demográficas, estimadas por permutação."""
from __future__ import annotations

import pandas as pd

from dcj.captura_recaptura import (
    DuasListas, ajustar_pares_pelo_acaso, extrapolar_pares_pela_cobertura_da_data)
from dcj.colunas import Col
from dcj.configuracao import Configuracao
from dcj.permutacao_sinan import manter_obitos_por_dcj, preparar_obitos_para_o_sorteio, simular_cruzamentos_ao_acaso
from dcj.sinan import (
    cruzar_por_chave, manter_obitos_a_partir_dos_sintomas, manter_obitos_na_janela_de_sobrevida)

TOLERANCIA_DA_DATA_DO_OBITO_EM_DIAS = 30
ID_DA_NOTIFICACAO = "id_da_notificacao"
CLASSIFICACAO_FINAL_DO_RECORTE = "1"


selecionar_obitos_por_dcj = manter_obitos_por_dcj


def listar_cruzamentos_na_janela(notificacoes: pd.DataFrame, obitos_por_dcj: pd.DataFrame) -> pd.DataFrame:
    identificadas = notificacoes.rename_axis(ID_DA_NOTIFICACAO).reset_index()
    cruzados = cruzar_por_chave(identificadas, obitos_por_dcj, [Col.DATA_OBITO])
    return manter_obitos_na_janela_de_sobrevida(manter_obitos_a_partir_dos_sintomas(cruzados))


def manter_datas_de_obito_coerentes(cruzados: pd.DataFrame,
                                    tolerancia_em_dias: int = TOLERANCIA_DA_DATA_DO_OBITO_EM_DIAS) -> pd.DataFrame:
    diferenca = (cruzados[Col.DATA_OBITO] - cruzados[Col.DATA_OBITO_NOTIFICADA]).dt.days.abs()
    return cruzados[diferenca <= tolerancia_em_dias]


def contar_notificacoes_distintas(cruzados: pd.DataFrame) -> int:
    return int(cruzados[ID_DA_NOTIFICACAO].nunique())


def contar_notificacoes_com_obito_dcj_na_janela(notificacoes: pd.DataFrame, obitos: pd.DataFrame) -> tuple[int]:
    """Contador no formato esperado pela simulação ao acaso (que embaralha TODOS os óbitos, não só A81.0)."""
    return (contar_notificacoes_distintas(listar_cruzamentos_na_janela(notificacoes, selecionar_obitos_por_dcj(obitos))),)


def estimar_pares_esperados_ao_acaso(notificacoes: pd.DataFrame, obitos: pd.DataFrame,
                                     configuracao: Configuracao) -> float:
    sorteaveis = preparar_obitos_para_o_sorteio(obitos)
    simuladas = simular_cruzamentos_ao_acaso(notificacoes, sorteaveis, configuracao,
                                             contar_notificacoes_com_obito_dcj_na_janela)
    return float(simuladas[:, 0].mean())


def montar_cenarios_do_recorte(rotulo: str, notificacoes: pd.DataFrame, obitos: pd.DataFrame,
                               configuracao: Configuracao) -> dict[str, DuasListas]:
    obitos_por_dcj = selecionar_obitos_por_dcj(obitos)
    n_sinan, n_sim = len(notificacoes), len(obitos_por_dcj)
    cruzados = listar_cruzamentos_na_janela(notificacoes, obitos_por_dcj)
    com_data = int(notificacoes[Col.DATA_OBITO_NOTIFICADA].notna().sum())
    pares_fortes = contar_notificacoes_distintas(manter_datas_de_obito_coerentes(cruzados))
    pares_fracos = contar_notificacoes_distintas(cruzados)
    esperados = estimar_pares_esperados_ao_acaso(notificacoes, obitos, configuracao)
    cenarios = {f"{rotulo} | chave forte observada": DuasListas(n_sinan, n_sim, min(pares_fortes, n_sim)),
                f"{rotulo} | chave fraca descontando o acaso":
                    DuasListas(n_sinan, n_sim, min(ajustar_pares_pelo_acaso(pares_fracos, esperados), n_sim))}
    if com_data:
        extrapolados = extrapolar_pares_pela_cobertura_da_data(pares_fortes, com_data, n_sinan)
        cenarios[f"{rotulo} | chave forte extrapolada p/ data ausente"] = DuasListas(
            n_sinan, n_sim, min(extrapolados, n_sinan, n_sim))
    return cenarios


def montar_cenarios_de_captura(notificacoes: pd.DataFrame, obitos: pd.DataFrame,
                               configuracao: Configuracao) -> dict[str, DuasListas]:
    """Dois recortes do SINAN: todas as notificações e só as com CLASSI_FIN = 1 (significado do código a confirmar)."""
    recorte = notificacoes[notificacoes[Col.CLASSIFICACAO_FINAL] == CLASSIFICACAO_FINAL_DO_RECORTE]
    cenarios = montar_cenarios_do_recorte(f"todas ({len(notificacoes)})", notificacoes, obitos, configuracao)
    cenarios.update(montar_cenarios_do_recorte(f"CLASSI_FIN=1 ({len(recorte)})", recorte, obitos, configuracao))
    return cenarios
