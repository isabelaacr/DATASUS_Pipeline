from fastapi import FastAPI, HTTPException
import duckdb
from pathlib import Path

app = FastAPI(title="API DCJ - Auditoria Epidemiológica")
PASTA_SCRIPT = Path(__file__).resolve().parent
PASTA_GOLD = PASTA_SCRIPT.parent / "dados_rs_drp" / "gold"
DB = duckdb.connect()

@app.get("/permutacao")
def get_permutacao():
    try:
        return DB.sql(f"SELECT * FROM '{PASTA_GOLD}/permutacao.parquet'").df().to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chapman")
def get_chapman():
    try:
        return DB.sql(f"SELECT * FROM '{PASTA_GOLD}/captura_recaptura_sensibilidade.parquet'").df().to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/escore")
def get_escore():
    try:
        return DB.sql(f"SELECT * FROM '{PASTA_GOLD}/escore_por_periodo.parquet'").df().to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))