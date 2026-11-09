import numpy as np
import pandas as pd

from conftest import criar_internacoes_limpas, criar_obitos_limpos
from dcj.colunas import Col
from dcj.pareamento import parear
from dcj.permutacao import ETAPAS_DO_PAREAMENTO, avaliar_pareamento_contra_o_acaso, embaralhar_dentro_do_bloco


def criar_base_com_pessoas(quantidade: int):
    """Óbitos espalhados por 2017-2022 e internação 30 dias antes: o embaralhamento só tem poder quando as datas
    variam, porque a etapa 'chave igual' é invariante (a permutação preserva as datas de nascimento do bloco)."""
    nascimentos = [f"19{40 + indice % 40}-{1 + indice % 12:02d}-{1 + indice % 27:02d}" for indice in range(quantidade)]
    datas_do_obito = pd.Timestamp("2017-03-01") + pd.to_timedelta([70 * indice for indice in range(quantidade)], "D")
    obitos = criar_obitos_limpos(*[{Col.DATA_NASCIMENTO: n, Col.DATA_OBITO: d}
                                   for n, d in zip(nascimentos, datas_do_obito)])
    internacoes = criar_internacoes_limpas(*[{Col.DATA_NASCIMENTO: n, Col.DATA_INTERNACAO: d - pd.Timedelta(30, "D")}
                                             for n, d in zip(nascimentos, datas_do_obito)])
    return internacoes, obitos


def test_contagem_observada_reproduz_o_pareamento_real(configuracao):
    internacoes, obitos = criar_base_com_pessoas(30)
    tabela = avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao)
    assert tabela["etapa"].tolist() == list(ETAPAS_DO_PAREAMENTO)
    assert tabela.iloc[-1]["observado"] == parear(internacoes, obitos, configuracao).total_de_pares


def test_pares_reais_superam_o_acaso(configuracao):
    internacoes, obitos = criar_base_com_pessoas(30)
    ultima_etapa = avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao).iloc[-1]
    assert ultima_etapa["observado"] > ultima_etapa["percentil_95_ao_acaso"]
    assert ultima_etapa["p_valor_unilateral"] < 0.05


def test_resultado_e_reprodutivel_com_a_mesma_semente(configuracao):
    internacoes, obitos = criar_base_com_pessoas(30)
    primeira = avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao)
    segunda = avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao)
    assert primeira.equals(segunda)


def test_embaralhamento_nao_cruza_blocos():
    valores = np.array([1, 2, 3, 10, 20, 30])
    blocos = np.array([0, 0, 0, 1, 1, 1])
    sorteados = embaralhar_dentro_do_bloco(valores, blocos, np.random.default_rng(0))
    assert sorted(sorteados[:3]) == [1, 2, 3] and sorted(sorteados[3:]) == [10, 20, 30]


def test_sem_candidatos_devolve_tabela_vazia(configuracao):
    internacoes, obitos = criar_base_com_pessoas(3)
    obitos[Col.MUNICIPIO] = "430000"
    assert avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao).empty


def test_primeira_etapa_e_invariante_por_construcao(configuracao):
    internacoes, obitos = criar_base_com_pessoas(30)
    primeira = avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao).iloc[0]
    assert primeira["excesso"] == 0 and primeira["p_valor_unilateral"] == 1.0