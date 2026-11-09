import pandas as pd
from typing import Sequence
from dcj.arquivos import carregar_obitos_brutos
from dcj.colunas import Bruto
from dcj.configuracao import carregar_configuracao
from pathlib import Path

def marcar_a810_na_declaracao(obitos: pd.DataFrame, linhas: Sequence[str]) -> pd.Series:
    # Verifica se A810 aparece em qualquer uma das linhas da declaração
    colunas_existentes = [c for c in linhas if c in obitos.columns]
    if not colunas_existentes:
        return pd.Series(False, index=obitos.index)
    
    texto = obitos[colunas_existentes].astype("string")
    return texto.apply(lambda coluna: coluna.str.contains("A810", na=False)).any(axis=1)

def contar_declaracoes_com_a810_discordante(obitos: pd.DataFrame, chave: list[str], linhas: Sequence[str]) -> int:
    # Filtra a chave para usar apenas colunas que existem no DataFrame
    chave_existente = [c for c in chave if c in obitos.columns]
    
    # Cria a marcação: A810 na causa básica OU nas linhas associadas
    tem_a810 = (marcar_a810_na_declaracao(obitos, linhas) | 
                obitos[Bruto.OBITO_CAUSA].astype(str).str.startswith("A810", na=False))
    
    # Agrupa pela chave existente
    por_declaracao = (obitos.assign(tem_a810=tem_a810)
                      .groupby(chave_existente, dropna=False)["tem_a810"]
                      .agg(["min", "max", "size"]))
    
    # Conta quantos grupos têm mais de 1 linha E marcações divergentes
    return int(((por_declaracao["size"] > 1) & (por_declaracao["min"] != por_declaracao["max"])).sum())

if __name__ == "__main__":
    pasta_raiz_projeto = Path(__file__).resolve().parent.parent.parent
    pasta_dados = pasta_raiz_projeto / "dados_rs_drp"
    
    config = carregar_configuracao(pasta_raiz=pasta_dados)
    brutos = carregar_obitos_brutos(config)
    
    chave = config.colunas_dos_obitos
    linhas = Bruto.OBITO_LINHAS_DA_DECLARACAO
    
    resultado = contar_declaracoes_com_a810_discordante(brutos, chave, linhas)
    print(f"Declarações com A81.0 discordante entre as cópias: {resultado}")