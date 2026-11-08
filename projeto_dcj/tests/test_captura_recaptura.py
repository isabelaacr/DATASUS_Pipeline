import pytest

from dcj.captura_recaptura import (DuasListas, ajustar_pares_pelo_acaso, calcular_intervalo_de_confianca,
                                   estimar_com_dependencia, estimar_por_chapman,
                                   extrapolar_pares_pela_cobertura_da_data, montar_tabela_de_sensibilidade)

LISTAS = DuasListas(total_da_primeira=45, total_da_segunda=44, em_ambas=10)


def test_chapman_reproduz_valor_conhecido():
    assert estimar_por_chapman(LISTAS) == pytest.approx(46 * 45 / 11 - 1)


def test_listas_exclusivas_e_observados():
    assert (LISTAS.so_na_primeira, LISTAS.so_na_segunda, LISTAS.observados) == (35, 34, 79)


@pytest.mark.parametrize("em_ambas", [-1, 46])
def test_listas_rejeitam_intersecao_impossivel(em_ambas):
    with pytest.raises(ValueError):
        DuasListas(45, 44, em_ambas)


def test_intervalo_contem_estimativa_e_respeita_o_observado():
    inferior, superior = calcular_intervalo_de_confianca(LISTAS)
    assert LISTAS.observados <= inferior < estimar_por_chapman(LISTAS) < superior


def test_independencia_equivale_ao_chapman():
    assert estimar_com_dependencia(LISTAS, 1.0) == pytest.approx(estimar_por_chapman(LISTAS))


def test_dependencia_positiva_aumenta_a_estimativa():
    assert estimar_com_dependencia(LISTAS, 2.0) > estimar_com_dependencia(LISTAS, 1.0) > estimar_com_dependencia(LISTAS, 0.5)


def test_dependencia_rejeita_razao_nao_positiva():
    with pytest.raises(ValueError):
        estimar_com_dependencia(LISTAS, 0)


def test_ajuste_pelo_acaso_nao_fica_negativo():
    assert ajustar_pares_pelo_acaso(18, 4.3) == 14
    assert ajustar_pares_pelo_acaso(3, 5.0) == 0


def test_extrapolacao_pela_cobertura_da_data():
    assert extrapolar_pares_pela_cobertura_da_data(10, 18, 45) == 25
    with pytest.raises(ValueError):
        extrapolar_pares_pela_cobertura_da_data(10, 0, 45)


def test_tabela_tem_uma_linha_por_cenario_e_colunas_de_razao():
    tabela = montar_tabela_de_sensibilidade({"a": LISTAS, "b": DuasListas(28, 44, 8)})
    assert list(tabela["cenario"]) == ["a", "b"]
    assert {"chapman", "ic95_inferior", "ic95_superior", "razao_0.5", "razao_3"} <= set(tabela.columns)
