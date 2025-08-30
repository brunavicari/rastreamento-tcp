import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

# ==========================
# CONFIGURAÇÕES
# ==========================
API_URL = "https://api.tcp.com.br/tos-bridge/v1/programacao-navios/pesquisar"
PAGE_SIZE = 100
MAX_PAGINAS = 20

st.set_page_config(page_title="Rastreamento TCP", layout="wide")
st.title("🚢 Rastreamento de Embarques TCP")

# ==========================
# FUNÇÃO PARA PEGAR NAVIOS
# ==========================
@st.cache_data(ttl=600, show_spinner=False)  # cache por 10 minutos
def pegar_programacao_navios(data_inicio=None):
    pagina = 1
    todos_dados = []

    if data_inicio is None:
        data_inicio = datetime.now(timezone.utc) - timedelta(days=7)

    while True:
        params = {
            "IncluirObsoletos": "false",
            "TamanhoPagina": PAGE_SIZE,
            "SentidoOrdenacao": 1,
            "PaginaAtual": pagina,
            "Ordenacao": "PrevisaoAtracacao",
            "Situacao": ["ATRACADO", "PREVISTO", "DESATRACADO", "CANCELADO"],
            "Excel": "false",
            "DataInicial": data_inicio.isoformat()
        }

        try:
            response = requests.get(API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            st.error(f"❌ Erro na requisição da página {pagina}: {e}")
            break

        registros = data.get("Objeto", []) if isinstance(data, dict) else data
        if not registros:
            break

        todos_dados.extend(registros)
        pagina += 1
        if pagina > MAX_PAGINAS:
            break

    return todos_dados


# ==========================
# COLETA E PREPARAÇÃO
# ==========================
with st.spinner("🔄 Consultando API TCP..."):
    dados = pegar_programacao_navios()

if not dados:
    st.warning("Nenhum dado retornado da API.")
    st.stop()

df_navios = pd.json_normalize(dados)

colunas_desejadas = ["Navio", "ArmadorNome", "PrevisaoAtracacao"]
df_navios = df_navios[colunas_desejadas].copy()
df_navios["PrevisaoAtracacao"] = pd.to_datetime(df_navios["PrevisaoAtracacao"], errors="coerce")

# Manter só a última previsão de cada navio
df_navios = df_navios.sort_values("PrevisaoAtracacao").drop_duplicates(subset=["Navio"], keep="last")

# ==========================
# FILTROS STREAMLIT
# ==========================
st.sidebar.header("⚙️ Filtros")

armadores = st.sidebar.multiselect("Selecione Armador:", sorted(df_navios["ArmadorNome"].dropna().unique()))
navios = st.sidebar.multiselect("Selecione Navio:", sorted(df_navios["Navio"].dropna().unique()))
data_min, data_max = df_navios["PrevisaoAtracacao"].min(), df_navios["PrevisaoAtracacao"].max()
intervalo_datas = st.sidebar.date_input("Período:", (data_min, data_max))

df_filtrado = df_navios.copy()
if armadores:
    df_filtrado = df_filtrado[df_filtrado["ArmadorNome"].isin(armadores)]
if navios:
    df_filtrado = df_filtrado[df_filtrado["Navio"].isin(navios)]
if len(intervalo_datas) == 2:
    inicio, fim = pd.to_datetime(intervalo_datas)
    df_filtrado = df_filtrado[(df_filtrado["PrevisaoAtracacao"] >= inicio) & (df_filtrado["PrevisaoAtracacao"] <= fim)]

# ==========================
# SIMULAÇÃO DE PEDIDOS
# ==========================
num_simulados = min(5, len(df_filtrado))
df_pedidos = pd.DataFrame({
    "PedidoID": range(1, num_simulados + 1),
    "Navio": df_filtrado["Navio"].iloc[:num_simulados].tolist(),
    "Produto": [f"Produto {i}" for i in range(1, num_simulados + 1)],
    "Quantidade": [10, 20, 15, 5, 12][:num_simulados]
})

df_result = df_pedidos.merge(df_filtrado, on="Navio", how="left")

# ==========================
# RESULTADOS
# ==========================
st.subheader(f"📦 Pedidos com previsão de chegada ({len(df_result)})")
st.dataframe(df_result, use_container_width=True)

st.subheader("📊 Programação de Navios")
st.dataframe(df_filtrado, use_container_width=True)

