# app.py
"""
Dashboard interativo para análise das vendas dos Jogos Santa Casa.
Foi pensado para ser executado em Streamlit Cloud (https://streamlit.io/cloud)
e ir buscar os dados diretamente à sua base de dados online.

❗️ Antes de publicar tem de:
    1. Colocar esta aplicação num repositório GitHub (por ex. 'jogos-santa-casa-dashboard').
    2. Definir as credenciais no ficheiro `.streamlit/secrets.toml` no repositório ou
       no separador 'Secrets' do projecto no Streamlit Cloud:
           [connections]
           DATABASE_URL = "postgresql://utilizador:password@host:5432/nome_db"
    3. Opcionalmente ajustar as queries SQL e os nomes dos campos/tabelas de acordo
       com o seu esquema real.
"""

# ----------------------- Imports --------------------------
import pandas as pd                               # Manipulação de dados
import streamlit as st                            # Framework web
from sqlalchemy import create_engine              # Ligação à BD
import plotly.express as px                       # Gráficos interactivos
from datetime import date

# ----------------- Configuração da página -----------------
st.set_page_config(
    page_title="Dashboard Jogos Santa Casa",
    page_icon="🎲",
    layout="wide",
)

# Título principal
st.title("📊 Análise de Vendas – Jogos Santa Casa")

# ---------- Função de carregamento de dados ---------------
# ⚠️ Altere a query para corresponder à sua BD
@st.cache_data(ttl=3600)  # cache durante 1 h para acelerar a navegação
def load_data():
    """Lê dados da base de dados e devolve‑os num DataFrame."""
    # 'DATABASE_URL' deve estar definido em st.secrets ou em variável de ambiente
    database_url = st.secrets.get("DATABASE_URL") or st.experimental_get_query_params().get("db", [None])[0]
    if database_url is None:
        st.error("Defina a variável de ligação à base de dados em st.secrets['DATABASE_URL'].")
        st.stop()

    # Cria o engine SQLAlchemy
    engine = create_engine(database_url)

    # Exemplo de query – ajuste conforme necessário
    query = """
        SELECT
            data,           -- Data da venda (DATE ou TIMESTAMP)
            produto,        -- Nome do jogo / produto
            vendas,         -- Valor de vendas (€)
            objectivo,      -- Objectivo definido (€)
            lucro           -- Margem ou lucro (€)
        FROM vendas
    """

    # Lê a query para um DataFrame pandas
    df = pd.read_sql(query, engine)

    # Converte o campo de data para datetime, caso ainda não esteja
    df['data'] = pd.to_datetime(df['data'])

    return df

# ---------------------- Sidebar ---------------------------
with st.sidebar:
    st.header("⚙️ Filtros")

    # Carrega dados (mostra spinner enquanto processa)
    with st.spinner("A carregar dados da base de dados..."):
        df = load_data()

    # Determina limites para o selector de datas
    min_day, max_day = df['data'].min().date(), df['data'].max().date()

    # Selector de intervalo de datas
    inicio, fim = st.date_input(
        "Período",
        (min_day, max_day),
        min_value=min_day,
        max_value=max_day,
        format="DD/MM/YYYY"
    )

    # Lista de produtos para filtrar
    produtos_disponiveis = df['produto'].unique().tolist()
    produtos_seleccionados = st.multiselect(
        "Produto",
        options=produtos_disponiveis,
        default=produtos_disponiveis
    )

# ------------------- Filtragem -----------------------------
mascara_datas = (df['data'].dt.date.between(inicio, fim))
mascara_produtos = df['produto'].isin(produtos_seleccionados)
df_filt = df.loc[mascara_datas & mascara_produtos]

# --------------- KPIs (Indicadores chave) -----------------
total_vendas = df_filt['vendas'].sum()
total_obj = df_filt['objectivo'].sum()
total_lucro = df_filt['lucro'].sum()

desvio_pct = (total_vendas - total_obj) / total_obj * 100 if total_obj else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Vendas", f"{total_vendas:,.0f} €")
col2.metric("Objectivo", f"{total_obj:,.0f} €")
col3.metric("Lucro", f"{total_lucro:,.0f} €")
col4.metric("Desvio %", f"{desvio_pct:.1f}%", delta=None)

st.divider()

# ------------------- Gráfico de Vendas Semanais -----------
# Agrega por semana (segunda‑feira como início – W‑MON)
df_semana = (
    df_filt
    .groupby(pd.Grouper(key='data', freq='W‑MON'))
    .agg(vendas=('vendas', 'sum'))
    .reset_index()
)

fig_semana = px.line(
    df_semana,
    x='data',
    y='vendas',
    title="Vendas por Semana",
    markers=True
)
# Remove legenda (só há uma série)
fig_semana.update_layout(showlegend=False)
st.plotly_chart(fig_semana, use_container_width=True)

# ------------------- Vendas vs Objectivo por Produto ------
df_prod = (
    df_filt
    .groupby('produto')
    .agg(vendas=('vendas', 'sum'), objectivo=('objectivo', 'sum'))
    .reset_index()
)

fig_bar = px.bar(
    df_prod,
    x='produto',
    y=['vendas', 'objectivo'],
    barmode='group',
    title="Vendas vs Objectivo por Produto"
)
st.plotly_chart(fig_bar, use_container_width=True)

# ------------------- Pie Chart (Vendas por Produto) -------
fig_pie = px.pie(
    df_prod,
    names='produto',
    values='vendas',
    title="Peso das Vendas por Produto"
)
st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ------------------- Tabela de dados ----------------------
with st.expander("📄 Ver dados detalhados"):
    st.dataframe(df_filt, use_container_width=True)
