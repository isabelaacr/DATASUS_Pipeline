import hashlib
import json
from pathlib import Path
import pandas as pd

def gerar_manifesto(pasta_bronze: Path, saida: Path):
    """Gera um hash SHA-256 de cada arquivo bruto para garantir a reprodutibilidade."""
    manifesto = {}
    for arquivo in sorted(pasta_bronze.glob("*.parquet")):
        df = pd.read_parquet(arquivo)
        
        # Validações de sanidade
        if df.empty:
            raise ValueError(f"Arquivo vazio: {arquivo.name}")
            
        manifesto[arquivo.name] = {
            "sha256": hashlib.sha256(arquivo.read_bytes()).hexdigest(),
            "linhas": len(df),
            "colunas": len(df.columns),
            "duplicatas_exatas": int(df.duplicated().sum())
        }
    
    with open(saida / "manifest.json", "w") as f:
        json.dump(manifesto, f, indent=4)
    print(f"Manifesto gerado com {len(manifesto)} arquivos.")