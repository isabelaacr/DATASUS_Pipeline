from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path
from typing import Optional, Sequence

from dcj.configuracao import Configuracao, carregar_configuracao
from dcj.erros import ErroDoPipeline
from dcj.etapas import ETAPAS
from dcj.fonte_pysus import descrever_pysus_instalado
from dcj.ingestao import baixar_internacoes, baixar_notificacoes, baixar_obitos

registro = logging.getLogger(__name__)


def criar_leitor_de_argumentos() -> argparse.ArgumentParser:
    leitor = argparse.ArgumentParser(prog="python -m dcj", description="Pipeline SIM x SIH e escore de DCJ")
    leitor.add_argument("--baixar", action="store_true", help="baixa SIM, SIH e SINAN via PySUS antes de tudo")
    leitor.add_argument("--etapa", choices=list(ETAPAS), help="roda só esta etapa")
    leitor.add_argument("--dados", type=Path, help="pasta dos dados (padrão: variável DCJ_DADOS)")
    leitor.add_argument("--verificar-pysus", action="store_true", help="mostra a API do PySUS instalado e sai")
    leitor.add_argument("--populacao", type=int, help="população da UF, para comparar óbitos A810 com o esperado")
    return leitor


def baixar_bases(configuracao: Configuracao) -> None:
    falhas = (baixar_obitos(configuracao) + baixar_internacoes(configuracao)
              + baixar_notificacoes(configuracao))
    for falha in falhas:
        registro.error("Download falhou: %s (%s)", falha.periodo, falha.motivo)


def executar_linha_de_comando(argumentos: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    leitura = criar_leitor_de_argumentos().parse_args(argumentos)
    if leitura.verificar_pysus:
        print(descrever_pysus_instalado())
        return 0
    configuracao = replace(carregar_configuracao(leitura.dados), populacao_da_uf=leitura.populacao)
    registro.info("Dados em: %s", configuracao.pasta_raiz)
    try:
        if leitura.baixar:
            baixar_bases(configuracao)
        for nome in ([leitura.etapa] if leitura.etapa else ETAPAS):
            registro.info("\n%s\nETAPA: %s\n%s", "=" * 60, nome, "=" * 60)
            ETAPAS[nome](configuracao)
    except ErroDoPipeline as erro:
        registro.error("Erro: %s", erro)
        return 1
    return 0
