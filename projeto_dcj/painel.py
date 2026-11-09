import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

# 1. Configuração da Página (Layout Largo)
st.set_page_config(page_title="Painel DCJ", page_icon="🧬", layout="wide")

# 2. Estilo Customizado (CSS simples para melhorar os cartões)
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] { font-size: 2rem; color: #1f77b4; }
    .stAlert { background-color: #f0f2f6; border-left: 5px solid #1f77b4; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧬 Auditoria de Subnotificação da DCJ")
st.markdown("Este painel apresenta **dados agregados** para preservar a privacidade dos pacientes (LGPD).")

PASTA_SCRIPT = Path(__file__).resolve().parent
PASTA_GOLD = PASTA_SCRIPT.parent / "dados_rs_drp" / "gold"
DB = duckdb.connect()

# --- SIDEBAR (Barra Lateral com Contexto) ---
with st.sidebar:
    st.header("Sobre o Projeto")
    st.info("""
    Este dashboard investiga a subnotificação da Doença de Creutzfeldt-Jakob no RS (2017–2022).
    
    **Fontes de dados:** SIM, SIH e SINAN (DATASUS).
    """)
    st.divider()
    st.caption("Desenvolvido para fins acadêmicos. Dados agregados para proteger a privacidade (LGPD).")

# --- ABAS ---
aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "🔗 Pareamento (SIM x SIH)", 
    "🏥 SINAN x SIM",
    "📊 Chapman (Captura-Recaptura)", 
    "📈 Escore de Suspeição",
    "✅ Validação TabNet"
])

with aba1:
    st.subheader("Validação do Pareamento por Permutação")
    st.markdown("O teste embaralha as datas de nascimento para provar que os vínculos não são meras coincidências demográficas.")
    
    try:
        df_perm = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/permutacao.parquet'").df()
        
        col1, col2, col3 = st.columns(3)
        observado = df_perm.iloc[-1]["observado"]
        acaso = df_perm.iloc[-1]["media_ao_acaso"]
        p_valor = df_perm.iloc[-1]["p_valor_unilateral"]
        
        col1.metric("Pares Observados", f"{observado}", "Reais")
        col2.metric("Esperado ao Acaso", f"{acaso:.1f}", "-")
        col3.metric("p-valor", f"{p_valor}", "Altamente Significativo")
        
        st.divider()
        
        df_plot = df_perm[df_perm["etapa"] != df_perm["etapa"].iloc[0]]
        fig = px.bar(df_plot, x="etapa", y=["observado", "media_ao_acaso"], 
                     barmode="group", title="Observado vs. Esperado ao Acaso",
                     labels={"value": "Quantidade de Pares", "variable": "Origem"})
        st.plotly_chart(fig, width='stretch')
        
        with st.expander("Ver tabela detalhada"):
            st.dataframe(df_perm, width='stretch', hide_index=True)
            
    except Exception as e:
        st.warning("Rode o pipeline (`gerar_gold.py`) para gerar os dados.")

with aba2:
    st.subheader("Cruzamento das Notificações (SINAN) com Óbitos (SIM)")
    st.markdown("Prova que as notificações de DCJ têm um vínculo real e temporal com os óbitos.")
    try:
        df_sinan = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/permutacao_sinan.parquet'").df()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Vínculos Reais (Observados)", f"{df_sinan.iloc[-1]['observado']}")
        col2.metric("Esperado ao Acaso", f"{df_sinan.iloc[-1]['media_ao_acaso']:.2f}")
        col3.metric("p-valor", f"{df_sinan.iloc[-1]['p_valor_unilateral']}")
        
        st.dataframe(df_sinan, width='stretch', hide_index=True)
    except Exception:
        st.warning("Rode o pipeline para gerar os dados.")

with aba3:
    st.subheader("Estimativa de Casos Reais (Chapman)")
    st.markdown("Análise de sensibilidade para estimar quantos casos existiram além dos notificados.")
    
    try:
        df_chap = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/captura_recaptura_sensibilidade.parquet'").df()
        
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            cenario = st.selectbox("Cenário da Lista 1 (SINAN)", df_chap["cenario"].unique())
        
        df_filtrado = df_chap[df_chap["cenario"] == cenario]
        
        col_met1, col_met2, col_met3 = st.columns(3)
        col_met1.metric("Estimativa (Chapman)", f"{int(df_filtrado['chapman'].iloc[0])}")
        col_met2.metric("IC 95% Inferior", f"{int(df_filtrado['ic95_inferior'].iloc[0])}")
        col_met3.metric("IC 95% Superior", f"{int(df_filtrado['ic95_superior'].iloc[0])}")
        
        st.info("A estimativa varia conforme a dependência entre as fontes (psi). O modelo assume independência, o que pode subestimar o total real.")
        
        st.dataframe(df_filtrado, width='stretch', hide_index=True)
        
    except Exception as e:
        st.warning(f"Erro ao carregar dados: {e}")

with aba4:
    st.subheader("Casos Sinalizados pelo Escore de Suspeição")
    st.markdown("O escore é uma heurística de triagem, não um diagnóstico definitivo.")
    
    try:
        df_esc = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/escore_por_periodo.parquet'").df()
        
        if not df_esc.empty:
            fig_esc = px.bar(df_esc, x="periodo", y="sinalizados", color="periodo",
                             title="Total de Casos Sinalizados (>= 70 pontos) por Período",
                             text="sinalizados", 
                             color_discrete_sequence=["#FF7F0E", "#1F77B4"])
            fig_esc.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig_esc, width='stretch')
            
            with st.expander("Ver tabela detalhada"):
                st.dataframe(df_esc, width='stretch', hide_index=True)
                
    except Exception:
        st.warning("Rode o pipeline para gerar os dados.")

with aba5:
    st.subheader("Validação Externa: Pipeline vs. TabNet (DATASUS)")
    st.markdown("Comparação do total de óbitos do pipeline com os dados oficiais do TabNet para a causa básica.")
    
    try:
        df_tabnet = DB.sql(f"SELECT * FROM '{PASTA_GOLD}/comparacao_tabnet.parquet'").df()
        
        col1, col2, col3 = st.columns(3)
        total_pipeline = int(df_tabnet["total_pipeline"].sum())
        total_basica = int(df_tabnet["so_causa_basica"].sum())
        total_tabnet = int(df_tabnet["tabnet"].sum())
        
        col1.metric("Pipeline (causa básica)", f"{total_basica:,}", f"vs TabNet: {total_basica - total_tabnet:,}")
        col2.metric("TabNet (oficial)", f"{total_tabnet:,}")
        col3.metric("Pipeline (geral)", f"{total_pipeline:,}", "Inclui mascaramento")
        
        st.divider()
        
        fig = px.bar(df_tabnet, x=df_tabnet.index, y=["so_causa_basica", "tabnet"], barmode="group",
                     title="Óbitos por Ano: Pipeline (causa básica) vs. TabNet",
                     labels={"value": "Óbitos", "variable": "Fonte", "index": "Ano"})
        st.plotly_chart(fig, width='stretch')
        
        with st.expander("Ver tabela detalhada"):
            st.dataframe(df_tabnet, width='stretch')
    except Exception as e:
        st.warning(f"Rode o gerar_gold.py para gerar os dados. Erro: {e}")