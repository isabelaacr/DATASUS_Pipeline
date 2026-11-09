from conftest import criar_internacoes_limpas, criar_obitos_limpos
from dcj.colunas import Col
from dcj.pareamento import parear
from dcj.permutacao import ETAPAS_DO_PAREAMENTO, avaliar_pareamento_contra_o_acaso, embaralhar_dentro_do_bloco

def criar_base_com_pessoas(quantidade: int):
    nascimentos = [f"19{40 + indice % 40}-{1 + indice % 12:02d}-{1 + indice % 27:02d}" for indice in range(quantidade)]
    obitos = criar_obitos_limpos(*[{Col.DATA_NASCIMENTO: n, Col.DATA_OBITO: "2020-06-01"} for n in nascimentos])
    internacoes = criar_internacoes_limpas(*[{Col.DATA_NASCIMENTO: n, Col.DATA_INTERNACAO: "2020-01-01"} for n in nascimentos])
    return internacoes, obitos


def test_contagem_observada_reproduz_o_pareamento_real(configuracao):
    internacoes, obitos = criar_base_com_pessoas(30)
    candidatos = montar_candidatos_do_bloco(internacoes, obitos, True)
    observado = contar_etapas(candidatos, candidatos.dia_e_mes_das_internacoes, "ultima")
    assert observado.pares_finais == parear(internacoes, obitos, configuracao).total_de_pares


def test_pares_reais_superam_o_acaso(configuracao):
    internacoes, obitos = criar_base_com_pessoas(30)
    tabela = avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao)
    ultima_etapa = tabela.iloc[-1]
    assert ultima_etapa["observado"] > ultima_etapa["percentil_95_ao_acaso"]
    assert ultima_etapa["p_valor_unilateral"] < 0.05


def test_resultado_e_reprodutivel_com_a_mesma_semente(configuracao):
    internacoes, obitos = criar_base_com_pessoas(15)
    primeira = avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao)
    segunda = avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao)
    assert primeira.equals(segunda)
