import pandas as pd
from pathlib import Path
from dcj.arquivos import carregar_obitos_brutos
from dcj.configuracao import carregar_configuracao
from dcj.limpeza import chave_dos_obitos, marcar_duplicatas

# Define as pastas com base na localização do script (que está em projeto_dcj/projeto_dcj)
PASTA_SCRIPT = Path(__file__).resolve().parent
PASTA_DADOS = PASTA_SCRIPT.parent / "dados_rs_drp"
PASTA_RESULTADOS = PASTA_DADOS / "resultados"
PASTA_GOLD = PASTA_DADOS / "gold"
PASTA_GOLD.mkdir(parents=True, exist_ok=True)

# Números oficiais do TabNet (causa básica)
TABNET = {2017: 7952, 2018: 8570, 2019: 8553, 2020: 8416, 2021: 9166, 2022: 10083}

def converter_para_gold(nome_csv: str):
    origem = PASTA_RESULTADOS / f"{nome_csv}.csv"
    destino = PASTA_GOLD / f"{nome_csv}.parquet"
    
    if origem.exists():
        df = pd.read_csv(origem)
        df.to_parquet(destino, index=False)
        print(f"✅ Convertido: {nome_csv}")
    else:
        print(f"⚠️ Não encontrado: {nome_csv}")

def gerar_comparacao_tabnet():
    print("⏳ Gerando comparação com o TabNet...")
    config = carregar_configuracao(pasta_raiz=PASTA_DADOS)
    
    # 1. Total geral (causa básica + associada) a partir dos dados LIMPOS (já deduplicados pelo pipeline)
    caminho_limpos = PASTA_DADOS / "processado" / "obitos_limpos.parquet"
    if not caminho_limpos.exists():
        print("❌ Erro: Rode o pipeline (`python -m dcj`) primeiro.")
        return

    obitos_limpos = pd.read_parquet(caminho_limpos)
    total_geral = obitos_limpos.groupby(obitos_limpos['data_obito'].dt.year).size()

    # 2. Total apenas causa básica (a partir dos brutos, aplicando a deduplicação)
    brutos = carregar_obitos_brutos(config)
    so_basica = brutos[brutos['CAUSABAS'].astype(str).str.startswith(tuple(config.cids_do_sim), na=False)]
    
    chave, identificador = chave_dos_obitos(so_basica)
    duplicatas = marcar_duplicatas(chave, identificador)
    so_basica_unica = so_basica[~duplicatas]
    
    anos_basica = pd.to_datetime(so_basica_unica['DTOBITO'], format='%d%m%Y', errors='coerce').dt.year
    total_basica = so_basica_unica.groupby(anos_basica).size()

    # 3. Junta tudo em um DataFrame
    df = pd.DataFrame({
        'total_pipeline': total_geral,
        'so_causa_basica': total_basica,
        'tabnet': [TABNET.get(int(ano), 0) for ano in total_geral.index]
    }).fillna(0)
    
    df.index.name = 'ano'
    df.to_parquet(PASTA_GOLD / "comparacao_tabnet.parquet")
    print("✅ Convertido: comparacao_tabnet")

if __name__ == "__main__":
    tabelas = [
        "permutacao",
        "permutacao_sinan",
        "captura_recaptura_sensibilidade",
        "escore_por_periodo",
        "escore_taxa_normalizada",
        "cobertura_por_ano",
        "obitos_a810_vs_esperado"
    ]

    for tabela in tabelas:
        converter_para_gold(tabela)
        
    gerar_comparacao_tabnet()
    print("\nCamada Gold pronta para o painel!")