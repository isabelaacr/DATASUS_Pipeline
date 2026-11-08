"""Quantos cruzamentos SINAN x SIM o ACASO produziria? A chave (município, sexo, ano de nascimento) é
fraca: embaralha-se o ano de nascimento dos óbitos DENTRO de cada bloco (município, sexo) e aplicam-se as
mesmas travas, para comparar igual com igual.

A primeira etapa é invariante ao embaralhamento (o bloco preserva quantos óbitos têm cada ano), então seu p é 1
por construção. O que discrimina é a coerência temporal: um vínculo real tem óbito logo após os sintomas, e
uma colisão tem data de óbito arbitrária."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from dcj.colunas import Col
from dcj.configuracao import Configuracao
from dcj.permutacao import resumir_permutacao
from dcj.sinan import (
    COLUNAS_DO_OBITO_NO_CRUZAMENTO, cruzar_sinan_com_obitos, listar_individuos_do_cruzamento,
    manter_obitos_na_janela_de_sobrevida)

ETAPAS_DO_SINAN = ("bloco + ano de nascimento iguais", "+ óbito >= primeiros sintomas",
                    "+ óbito em até 1 ano dos sintomas", "+ indivíduos únicos")
BLOCO_DO_EMBARALHAMENTO = [Col.MUNICIPIO, Col.SEXO]


def contar_etapas_do_cruzamento(notificacoes: pd.DataFrame, obitos: pd.DataFrame) -> tuple[int, int, int, int]:
    por_chave, validos = cruzar_sinan_com_obitos(notificacoes, obitos)
    na_janela = manter_obitos_na_janela_de_sobrevida(validos)
    return len(por_chave), len(validos), len(na_janela), len(listar_individuos_do_cruzamento(na_janela))


def embaralhar_dentro_do_bloco(valores: np.ndarray, identificador_do_bloco: np.ndarray,
                               gerador: np.random.Generator) -> np.ndarray:
    """Permuta `valores` só entre linhas do mesmo bloco: ordena por bloco com e sem sorteio e alinha as duas ordens."""
    ordem_original = np.argsort(identificador_do_bloco, kind="stable")
    ordem_sorteada = np.lexsort((gerador.random(len(valores)), identificador_do_bloco))
    embaralhados = np.empty_like(valores)
    embaralhados[ordem_original] = valores[ordem_sorteada]
    return embaralhados


def preparar_obitos_para_o_sorteio(obitos: pd.DataFrame) -> pd.DataFrame:
    colunas = BLOCO_DO_EMBARALHAMENTO + [Col.ANO_NASCIMENTO] + COLUNAS_DO_OBITO_NO_CRUZAMENTO
    return obitos[colunas].dropna(subset=BLOCO_DO_EMBARALHAMENTO + [Col.ANO_NASCIMENTO]).reset_index(drop=True)


def simular_cruzamentos_ao_acaso(notificacoes: pd.DataFrame, obitos: pd.DataFrame, configuracao: Configuracao,
                                 contador: Callable[[pd.DataFrame, pd.DataFrame], tuple[int, ...]]
                                 = contar_etapas_do_cruzamento) -> np.ndarray:
    gerador = np.random.default_rng(configuracao.semente_aleatoria)
    identificador = obitos.groupby(BLOCO_DO_EMBARALHAMENTO, sort=False).ngroup().to_numpy()
    anos = obitos[Col.ANO_NASCIMENTO].to_numpy()
    contagens = [contador(
        notificacoes, obitos.assign(**{Col.ANO_NASCIMENTO: embaralhar_dentro_do_bloco(anos, identificador, gerador)}))
        for _ in range(configuracao.numero_de_permutacoes)]
    return np.array(contagens)


def avaliar_cruzamento_sinan_contra_o_acaso(notificacoes: pd.DataFrame, obitos: pd.DataFrame,
                                            configuracao: Configuracao) -> pd.DataFrame:
    sorteaveis = preparar_obitos_para_o_sorteio(obitos)
    observado = contar_etapas_do_cruzamento(notificacoes, sorteaveis)
    simuladas = simular_cruzamentos_ao_acaso(notificacoes, sorteaveis, configuracao)
    return resumir_permutacao(observado, simuladas, ETAPAS_DO_SINAN)
