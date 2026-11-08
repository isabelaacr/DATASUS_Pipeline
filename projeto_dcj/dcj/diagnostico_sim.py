import pysus
import pandas as pd

print("Versão PySUS:", pysus.__version__)

# Função legada (que alimenta o pipeline)
df = pysus.sim(state="RS", year=2019, as_dataframe=True)
print("Shape:", df.shape)
print("Duplicatas:", df.duplicated().sum())
print("NUMERODO existe:", "NUMERODO" in df.columns)
print("Top 5 prefixos:", df["CODMUNRES"].astype(str).str[:2].value_counts().head(5).to_dict())
