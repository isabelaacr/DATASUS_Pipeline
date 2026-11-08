import streamlit as st
import duckdb
from pathlib import Path

st.set_page_config(page_title="Painel DCJ", layout="wide")
st.title("🧬 Auditoria de Subnotificação da DCJ")
st.markdown("Este painel apresenta **dados agregados** para preservar a privacidade dos pacientes (LGPD).")

PASTA_SCRIPT = Path(__file__).resolve().parent
PASTA_GOLD = PASTA_SCRIPT.parent / "dados_rs_drp" / "gold"
DB = duckdb.connect()

aba1, aba2, aba3, aba4 = st.tabs([
    "🔗 Pareamento (SIM x SIH)", 
    "🏥 SINAN x SIM",
    "📊 Captura-Recaptura (Chapman)", 
    "📈 Escore de Suspeição"
])

with aba1:
    st.subheader("Permutação SIM x SIH")
    try:
        df = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/permutacao.parquet'").df()
        st.dataframe(df)
    except Exception:
        st.warning("Rode o pipeline para gerar os dados.")
    st.caption("O p-valor mínimo atingível é 1/(B+1). O modelo prova que os vínculos excedem o acaso.")

with aba2:
    st.subheader("Permutação SINAN x SIM (A810)")
    try:
        df = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/permutacao_sinan.parquet'").df()
        st.dataframe(df)
    except Exception:
        st.warning("Rode o pipeline para gerar os dados.")

with aba3:
    st.subheader("Estimativa de Casos Reais (Análise de Sensibilidade)")
    try:
        df = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/captura_recaptura_sensibilidade.parquet'").df()
        cenario = st.selectbox("Filtro do SINAN", df["cenario"].unique())
        df_filtrado = df[df["cenario"] == cenario]
        st.dataframe(df_filtrado)
        if not df_filtrado.empty:
            st.metric("Estimativa de Chapman (psi=1)", int(df_filtrado["chapman"].iloc[0]))
    except Exception:
        st.warning("Rode o pipeline para gerar os dados.")
    st.caption("O modelo assume independência. A dependência entre as fontes pode elevar o total real.")

with aba4:
    st.subheader("Casos Sinalizados pelo Escore")
    try:
        df = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/escore_por_periodo.parquet'").df()
        if not df.empty:
            st.bar_chart(df, x="periodo", y="sinalizados", color="periodo")
    except Exception:
        st.warning("Rode o pipeline para gerar os dados.")
    st.caption("O escore é uma ferramenta de triagem e priorização, não de diagnóstico definitivo.")