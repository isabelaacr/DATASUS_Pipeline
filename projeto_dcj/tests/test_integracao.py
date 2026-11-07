import pandas as pd

from dcj.cli import executar_linha_de_comando
from dcj.colunas import Col
from dados_sinteticos import gerar_dados_brutos

QUANTIDADE_DE_PARES = 40


def test_pipeline_completo_recupera_os_pares_conhecidos(configuracao):
    gerar_dados_brutos(configuracao.pasta_raiz, quantidade_de_pares=QUANTIDADE_DE_PARES)
    assert executar_linha_de_comando(["--dados", str(configuracao.pasta_raiz)]) == 0
    pares = pd.read_parquet(configuracao.arquivo_processado("pares_com_escore"))
    assert len(pares) >= QUANTIDADE_DE_PARES * 0.95
    assert (pares[Col.DATA_INTERNACAO] <= pares[Col.DATA_OBITO]).all()
    for nome in ("funil_obitos", "pareamento_resumo", "escore_por_periodo", "permutacao", "concordancia"):
        assert configuracao.arquivo_de_resultado(nome).exists()


def test_etapa_sem_a_anterior_falha_com_mensagem_e_codigo_1(configuracao, caplog):
    assert executar_linha_de_comando(["--dados", str(configuracao.pasta_raiz), "--etapa", "pareamento"]) == 1
    assert "limpeza" in caplog.text


def test_populacao_gera_comparacao_com_o_esperado_do_boletim(configuracao):
    gerar_dados_brutos(configuracao.pasta_raiz, quantidade_de_pares=QUANTIDADE_DE_PARES)
    argumentos = ["--dados", str(configuracao.pasta_raiz), "--populacao", "11000000"]
    assert executar_linha_de_comando(argumentos) == 0
    assert configuracao.arquivo_de_resultado("escore_sensibilidade_faixa_etaria").exists()
    assert configuracao.arquivo_de_resultado("obitos_a810_vs_esperado").exists()
