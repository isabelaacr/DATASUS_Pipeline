import pandas as pd
import glob

print("=== DIAGNÓSTICO DE DUPLICATAS (SIM RS) ===")
for arquivo in sorted(glob.glob(r'..\dados_rs_drp\sim\*.parquet')):
    df = pd.read_parquet(arquivo)
    
    # Adiciona a coluna de contagem de campos preenchidos
    df['_preenchidos'] = df.notna().sum(axis=1)
    
    # Agrupa pela chave demográfica
    chave = ['CODMUNRES', 'SEXO', 'DTNASC', 'DTOBITO', 'CAUSABAS', 'IDADE']
    chave = [c for c in chave if c in df.columns]
    
    grupos = df.groupby(chave)
    duplicados = grupos.filter(lambda x: len(x) > 1)
    
    if not duplicados.empty:
        # Verifica se as cópias têm a mesma quantidade de campos preenchidos
        variacao_preenchimento = duplicados.groupby(chave)['_preenchidos'].nunique().gt(1).sum()
        nome_arquivo = arquivo.split('\\')[-1]
        print(f"{nome_arquivo}: {len(df)} linhas | {duplicados.shape[0]} duplicadas | Variação de preenchimento: {variacao_preenchimento}")
    else:
        nome_arquivo = arquivo.split('\\')[-1]
        print(f"{nome_arquivo}: {len(df)} linhas | Sem duplicatas")