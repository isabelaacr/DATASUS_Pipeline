import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

# 1. ConfiguraÃ§Ã£o da PÃ¡gina (Layout Largo)
st.set_page_config(page_title="Painel DCJ", page_icon="ðŸ§¬", layout="wide")

# 2. Estilo Customizado (CSS simples para melhorar os cartÃµes)
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] { font-size: 2rem; color: #1f77b4; }
    .stAlert { background-color: #f0f2f6; border-left: 5px solid #1f77b4; }
    </style>
    """, unsafe_allow_html=True)

st.title("ðŸ§¬ Auditoria de SubnotificaÃ§Ã£o da DCJ")
st.markdown("Este painel apresenta **dados agregados** para preservar a privacidade dos pacientes (LGPD).")

PASTA_SCRIPT = Path(__file__).resolve().parent
PASTA_GOLD = PASTA_SCRIPT.parent / "dados_rs_drp" / "gold"
DB = duckdb.connect()

# --- SIDEBAR (Barra Lateral com Contexto) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=80)
    st.header("Sobre o Projeto")
    st.info("""
    Este dashboard investiga a subnotificaÃ§Ã£o da DoenÃ§a de Creutzfeldt-Jakob no RS (2017â€“2022).
    
    **Fontes de dados:** SIM, SIH e SINAN (DATASUS).
    """)
    st.divider()
    st.caption("Desenvolvido para fins acadÃªmicos. Dados agregados para proteger a privacidade (LGPD).")

# --- ABAS ---
aba1, aba2, aba3, aba4 = st.tabs([
    "ðŸ”— Pareamento (SIM x SIH)", 
    "ðŸ¥ SINAN x SIM",
    "ðŸ“Š Chapman (Captura-Recaptura)", 
    "ðŸ“ˆ Escore de SuspeiÃ§Ã£o"
])

with aba1:
    st.subheader("ValidaÃ§Ã£o do Pareamento por PermutaÃ§Ã£o")
    st.markdown("O teste embaralha as datas de nascimento para provar que os vÃ­nculos nÃ£o sÃ£o meras coincidÃªncias demogrÃ¡ficas.")
    
    try:
        df_perm = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/permutacao.parquet'").df()
        
        # CartÃµes de MÃ©tricas (Extraindo os valores da Ãºltima linha do dataframe)
        col1, col2, col3 = st.columns(3)
        observado = df_perm.iloc[-1]["observado"]
        acaso = df_perm.iloc[-1]["media_ao_acaso"]
        p_valor = df_perm.iloc[-1]["p_valor_unilateral"]
        
        col1.metric("Pares Observados", f"{observado}", "Reais")
        col2.metric("Esperado ao Acaso", f"{acaso:.1f}", "-")
        col3.metric("p-valor", f"{p_valor}", "Altamente Significativo")
        
        st.divider()
        
        # GrÃ¡fico de Barras Comparativo
        df_plot = df_perm[df_perm["etapa"] != df_perm["etapa"].iloc[0]] # Remove a primeira etapa (invariante)
        fig = px.bar(df_plot, x="etapa", y=["observado", "media_ao_acaso"], 
                     barmode="group", title="Observado vs. Esperado ao Acaso",
                     labels={"value": "Quantidade de Pares", "variable": "Origem"})
        st.plotly_chart(fig, width='stretch') # CORRIGIDO AQUI
        
        # Tabela detalhada escondida em um expander
        with st.expander("Ver tabela detalhada"):
            st.dataframe(df_perm, width='stretch', hide_index=True) # CORRIGIDO AQUI
            
    except Exception as e:
        st.warning("Rode o pipeline (`gerar_gold.py`) para gerar os dados.")

with aba2:
    st.subheader("Cruzamento das NotificaÃ§Ãµes (SINAN) com Ã“bitos (SIM)")
    st.markdown("Prova que as notificaÃ§Ãµes de DCJ tÃªm um vÃ­nculo real e temporal com os Ã³bitos.")
    try:
        df_sinan = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/permutacao_sinan.parquet'").df()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("VÃ­nculos Reais (Observados)", f"{df_sinan.iloc[-1]['observado']}")
        col2.metric("Esperado ao Acaso", f"{df_sinan.iloc[-1]['media_ao_acaso']:.2f}")
        col3.metric("p-valor", f"{df_sinan.iloc[-1]['p_valor_unilateral']}")
        
        st.dataframe(df_sinan, width='stretch', hide_index=True) # CORRIGIDO AQUI
    except Exception:
        st.warning("Rode o pipeline para gerar os dados.")

with aba3:
    st.subheader("Estimativa de Casos Reais (Chapman)")
    st.markdown("AnÃ¡lise de sensibilidade para estimar quantos casos existiram alÃ©m dos notificados.")
    
    try:
        df_chap = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/captura_recaptura_sensibilidade.parquet'").df()
        
        # Filtros
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            cenario = st.selectbox("CenÃ¡rio da Lista 1 (SINAN)", df_chap["cenario"].unique())
        
        df_filtrado = df_chap[df_chap["cenario"] == cenario]
        
        # CartÃµes com os valores do Chapman
        col_met1, col_met2, col_met3 = st.columns(3)
        col_met1.metric("Estimativa (Chapman)", f"{int(df_filtrado['chapman'].iloc[0])}")
        col_met2.metric("IC 95% Inferior", f"{int(df_filtrado['ic95_inferior'].iloc[0])}")
        col_met3.metric("IC 95% Superior", f"{int(df_filtrado['ic95_superior'].iloc[0])}")
        
        st.info("A estimativa varia conforme a dependÃªncia entre as fontes (psi). O modelo assume independÃªncia, o que pode subestimar o total real.")
        
        st.dataframe(df_filtrado, width='stretch', hide_index=True) # CORRIGIDO AQUI
        
    except Exception as e:
        st.warning(f"Erro ao carregar dados: {e}")

with aba4:
    st.subheader("Casos Sinalizados pelo Escore de SuspeiÃ§Ã£o")
    st.markdown("O escore Ã© uma heurÃ­stica de triagem, nÃ£o um diagnÃ³stico definitivo.")
    
    try:
        df_esc = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/escore_por_periodo.parquet'").df()
        
        if not df_esc.empty:
            # GrÃ¡fico de barras do Plotly
            fig_esc = px.bar(df_esc, x="periodo", y="sinalizados", color="periodo",
                             title="Total de Casos Sinalizados (>= 70 pontos) por PerÃ­odo",
                             text="sinalizados", 
                             color_discrete_sequence=["#FF7F0E", "#1F77B4"])
            fig_esc.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig_esc, width='stretch') # CORRIGIDO AQUI
            
            with st.expander("Ver tabela detalhada"):
                st.dataframe(df_esc, width='stretch', hide_index=True) # CORRIGIDO AQUI
                
    except Exception:
        st.warning("Rode o pipeline para gerar os dados.")
