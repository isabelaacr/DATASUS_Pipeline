import pandas as pd
import pyreaddbc
import dbf
from pathlib import Path

PASTA_SINAN = Path("dados_rs_drp/sinan")

for sufixo in range(17, 23):
    ano = 2000 + sufixo
    arquivo_dbc = PASTA_SINAN / f"DCRJBR{sufixo}.dbc"
    arquivo_dbf = PASTA_SINAN / f"DCRJBR{sufixo}.dbf"
    arquivo_parquet = PASTA_SINAN / f"sinan_rs_{ano}.parquet"

    if arquivo_dbc.exists():
        print(f"Convertendo {arquivo_dbc.name}...")
        try:
            # Descompacta o .dbc para .dbf
            pyreaddbc.dbc2dbf(str(arquivo_dbc), str(arquivo_dbf))

            # Lê o .dbf usando a biblioteca 'dbf' (que aceita colunas duplicadas)
            tabela = dbf.Table(str(arquivo_dbf))
            tabela.open(mode=dbf.READ_ONLY)

            # Renomeia duplicatas (ID_MN_RESI_1, ID_MN_RESI_2)
            campos = tabela.field_names
            colunas_unicas = []
            contagem = {}
            for c in campos:
                if c in contagem:
                    contagem[c] += 1
                    colunas_unicas.append(f"{c}_{contagem[c]}")
                else:
                    contagem[c] = 1
                    colunas_unicas.append(c)

            # Extrai os dados
            registros = [list(linha) for linha in tabela]
            df = pd.DataFrame(registros, columns=colunas_unicas)

            # Fecha a tabela original
            tabela.close()

            # O pipeline quer a coluna de residência. 
            # No DATASUS, a segunda ocorrência geralmente é a de residência.
            if 'ID_MN_RESI_2' in df.columns:
                df = df.rename(columns={'ID_MN_RESI_2': 'ID_MN_RESI', 'ID_MN_RESI_1': 'ID_MUNICIP_NOTIFICACAO'})
            elif 'ID_MN_RESI_1' in df.columns:
                df = df.rename(columns={'ID_MN_RESI_1': 'ID_MN_RESI'})

            # Padroniza o resto para maiúsculo
            df.columns = [str(c).upper().strip() for c in df.columns]

            # Garante que as colunas de texto não tenham problemas no Parquet
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str)

            df.to_parquet(arquivo_parquet, index=False)
            print(f"✅ Salvo: {arquivo_parquet.name} ({len(df)} registros)")

            # Remove o .dbf temporário
            if arquivo_dbf.exists():
                arquivo_dbf.unlink()

        except Exception as e:
            print(f"❌ Erro em {arquivo_dbc.name}: {e}")

print("Conversão finalizada!")