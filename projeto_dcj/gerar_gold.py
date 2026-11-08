import pandas as pd
from pathlib import Path

PASTA_SCRIPT = Path(__file__).resolve().parent
PASTA_DADOS = PASTA_SCRIPT.parent / "dados_rs_drp"

PASTA_RESULTADOS = PASTA_DADOS / "resultados"
PASTA_GOLD = PASTA_DADOS / "gold"
PASTA_GOLD.mkdir(parents=True, exist_ok=True)

def converter_para_gold(nome_csv: str):
    origem = PASTA_RESULTADOS / f"{nome_csv}.csv"
    destino = PASTA_GOLD / f"{nome_csv}.parquet"
    
    if origem.exists():
        df = pd.read_csv(origem)
        df.to_parquet(destino, index=False)
        print(f"✅ Convertido: {nome_csv}")
    else:
        print(f"⚠️ Não encontrado: {origem}")

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

print("\nCamada Gold pronta para o painel!")