"""Orquestração: cada etapa lê entradas, chama funções puras, grava saídas e registra o resultado.
Nenhuma regra de negócio mora aqui."""
from __future__ import annotations
from dcj.captura_recaptura import DuasListas, montar_tabela_de_sensibilidade

import logging
from typing import Callable, Optional

import pandas as pd

from dcj import armazenamento as disco
from dcj.arquivos import (
    carregar_internacoes_brutas, carregar_notificacoes_brutas, carregar_obitos_brutos, existem_notificacoes_brutas)
from dcj.cobertura import auditar_obitos_brutos, calcular_cobertura_por_ano, comparar_obitos_por_dcj_com_esperado
from dcj.concordancia import calcular_concordancia
from dcj.configuracao import Configuracao
from dcj.escore import (
    calcular_escore, calcular_taxa_normalizada, comparar_criterios_de_desempate,
    comparar_faixas_etarias, p_valor_de_fisher_entre_periodos, resumir_por_periodo)
from dcj.limpeza import limpar_internacoes, limpar_obitos
from dcj.colunas import Col
from dcj.pareamento import parear
from dcj.sinan import (
    cruzar_sinan_com_internacoes, cruzar_sinan_com_obitos, listar_individuos_do_cruzamento,
    manter_obitos_na_janela_de_sobrevida, preparar_notificacoes,
    resumir_cruzamentos, resumir_perfil_dos_individuos)
from dcj.permutacao import avaliar_pareamento_contra_o_acaso
from dcj.permutacao_sinan import avaliar_cruzamento_sinan_contra_o_acaso

registro = logging.getLogger(__name__)
Etapa = Callable[[Configuracao], None]


def relatar(titulo: str, conteudo: object) -> None:
    texto = conteudo.to_string() if isinstance(conteudo, pd.DataFrame) else str(conteudo)
    registro.info("\n=== %s ===\n%s", titulo, texto)


def _gravar_resultado(configuracao: Configuracao, nome: str, tabela: pd.DataFrame, manter_indice: bool = False) -> None:
    disco.salvar_csv(tabela, configuracao.arquivo_de_resultado(nome), manter_indice)


def _ler_limpos(configuracao: Configuracao) -> tuple[pd.DataFrame, pd.DataFrame]:
    obitos = disco.ler_parquet_da_etapa_anterior(configuracao.arquivo_processado("obitos_limpos"), "limpeza")
    internacoes = disco.ler_parquet_da_etapa_anterior(configuracao.arquivo_processado("internacoes_limpas"), "limpeza")
    return obitos, internacoes


def executar_limpeza(configuracao: Configuracao) -> None:
    obitos, funil_dos_obitos = limpar_obitos(carregar_obitos_brutos(configuracao), configuracao)
    internacoes, funil_das_internacoes = limpar_internacoes(carregar_internacoes_brutas(configuracao), configuracao)
    disco.salvar_parquet(obitos, configuracao.arquivo_processado("obitos_limpos"))
    disco.salvar_parquet(internacoes, configuracao.arquivo_processado("internacoes_limpas"))
    _gravar_resultado(configuracao, "funil_obitos", funil_dos_obitos)
    _gravar_resultado(configuracao, "funil_internacoes", funil_das_internacoes)
    relatar("FUNIL DOS ÓBITOS", funil_dos_obitos)
    relatar("FUNIL DAS INTERNAÇÕES", funil_das_internacoes)


def executar_pareamento(configuracao: Configuracao) -> None:
    obitos, internacoes = _ler_limpos(configuracao)
    resultado = parear(internacoes, obitos, configuracao)
    disco.salvar_parquet(resultado.pares, configuracao.arquivo_processado("pares_finais"))
    resumo = pd.DataFrame({"valor": {"pares_candidatos": resultado.candidatos,
                                     "apos_internacao_antes_do_obito": resultado.apos_internacao_antes_do_obito,
                                     "pares_finais": resultado.total_de_pares}})
    _gravar_resultado(configuracao, "pareamento_resumo", resumo, manter_indice=True)
    relatar("PAREAMENTO", resumo)


def executar_escore(configuracao: Configuracao) -> None:
    obitos, internacoes = _ler_limpos(configuracao)
    pares = disco.ler_parquet_da_etapa_anterior(configuracao.arquivo_processado("pares_finais"), "pareamento")
    pontuados = calcular_escore(pares, configuracao)
    por_periodo = resumir_por_periodo(pontuados)
    disco.salvar_parquet(pontuados, configuracao.arquivo_processado("pares_com_escore"))
    _gravar_resultado(configuracao, "escore_por_periodo", por_periodo, manter_indice=True)
    _gravar_resultado(configuracao, "escore_taxa_normalizada", calcular_taxa_normalizada(pontuados, internacoes, configuracao))
    _gravar_resultado(configuracao, "escore_sensibilidade_desempate",
                      comparar_criterios_de_desempate(internacoes, obitos, configuracao))
    _gravar_resultado(configuracao, "casos_sinalizados", pontuados[pontuados[Col.SINALIZADO]])
    _gravar_resultado(configuracao, "escore_sensibilidade_faixa_etaria", comparar_faixas_etarias(pares, configuracao))
    relatar("ESCORE POR PERÍODO", por_periodo)
    relatar("FISHER ENTRE PERÍODOS (p)", round(p_valor_de_fisher_entre_periodos(pontuados), 3))


def executar_validacao(configuracao: Configuracao) -> None:
    obitos, internacoes = _ler_limpos(configuracao)
    pares = disco.ler_parquet_da_etapa_anterior(configuracao.arquivo_processado("pares_finais"), "pareamento")
    permutacao = avaliar_pareamento_contra_o_acaso(internacoes, obitos, configuracao)
    cobertura = calcular_cobertura_por_ano(obitos, internacoes)
    concordancia = pd.DataFrame({"valor": calcular_concordancia(pares)})
    _gravar_resultado(configuracao, "permutacao", permutacao)
    _gravar_resultado(configuracao, "cobertura_por_ano", cobertura, manter_indice=True)
    _gravar_resultado(configuracao, "concordancia", concordancia, manter_indice=True)
    relatar("AUDITORIA DA INGESTÃO (óbitos brutos)", auditar_obitos_brutos(carregar_obitos_brutos(configuracao), configuracao))
    relatar("COBERTURA POR ANO", cobertura)
    relatar("PERMUTAÇÃO", permutacao)
    relatar("CONCORDÂNCIA SIH x SIM", concordancia)
    _validar_contra_o_esperado_do_boletim(configuracao, obitos)


def _validar_contra_o_esperado_do_boletim(configuracao: Configuracao, obitos: pd.DataFrame) -> None:
    if configuracao.populacao_da_uf is None:
        registro.info("Informe --populacao para comparar os óbitos A810 com o esperado do boletim.")
        return
    esperado = comparar_obitos_por_dcj_com_esperado(obitos, configuracao.populacao_da_uf)
    _gravar_resultado(configuracao, "obitos_a810_vs_esperado", esperado, manter_indice=True)
    relatar("ÓBITOS A810 x ESPERADO (Boletim DCJ, p. 12)", esperado)


def _ler_notificacoes_preparadas(configuracao: Configuracao) -> Optional[tuple[int, pd.DataFrame]]:
    if not existem_notificacoes_brutas(configuracao):
        registro.warning("Etapa do SINAN ignorada: sem arquivos sinan_AAAA em %s (rode com --baixar)",
                         configuracao.pasta_do_sinan)
        return None
    brutas = carregar_notificacoes_brutas(configuracao)
    return len(brutas), preparar_notificacoes(brutas, configuracao)


def executar_sinan(configuracao: Configuracao) -> None:
    leitura = _ler_notificacoes_preparadas(configuracao)
    if leitura is None:
        return
    total_bruto, notificacoes = leitura
    obitos, internacoes = _ler_limpos(configuracao)
    com_obito = cruzar_sinan_com_obitos(notificacoes, obitos)
    com_internacao = cruzar_sinan_com_internacoes(notificacoes, internacoes)
    individuos = listar_individuos_do_cruzamento(manter_obitos_na_janela_de_sobrevida(com_obito[1]))
    resumo = resumir_cruzamentos(total_bruto, notificacoes, com_obito, com_internacao)
    _gravar_resultado(configuracao, "sinan_resumo", resumo, manter_indice=True)
    _gravar_resultado(configuracao, "sinan_x_sim_validos", com_obito[1])
    _gravar_resultado(configuracao, "sinan_x_sih_validos", com_internacao[1])
    _gravar_resultado(configuracao, "sinan_individuos", individuos)
    relatar("CRUZAMENTO EXPLORATÓRIO COM O SINAN", resumo)
    if len(individuos):
        _gravar_resultado(configuracao, "sinan_perfil_individuos", resumir_perfil_dos_individuos(individuos),
                          manter_indice=True)


def executar_validacao_sinan(configuracao: Configuracao) -> None:
    leitura = _ler_notificacoes_preparadas(configuracao)
    if leitura is None:
        return
    obitos, _ = _ler_limpos(configuracao)
    notificacoes = leitura[1]
    permutacao = avaliar_cruzamento_sinan_contra_o_acaso(notificacoes, obitos, configuracao)
    _gravar_resultado(configuracao, "permutacao_sinan", permutacao)
    relatar("PERMUTAÇÃO SINAN x SIM (cruzamento vs acaso)", permutacao)


    listas_todas = DuasListas(total_da_primeira=45, total_da_segunda=44, em_ambas=10)
    listas_confirmadas = DuasListas(total_da_primeira=28, total_da_segunda=44, em_ambas=8)

    cenarios = {
        "SINAN todas (45)": listas_todas,
        "SINAN confirmadas (28)": listas_confirmadas,
    }

    tabela_chapman = montar_tabela_de_sensibilidade(cenarios)
    _gravar_resultado(configuracao, "captura_recaptura_sensibilidade", tabela_chapman)
    relatar("CAPTURA-RECAPTURA (CHAPMAN)", tabela_chapman)

ETAPAS: dict[str, Etapa] = {
    "limpeza": executar_limpeza,
    "pareamento": executar_pareamento,
    "escore": executar_escore,
    "validacao": executar_validacao,
    "sinan": executar_sinan,
    "validacao_sinan": executar_validacao_sinan,
}
