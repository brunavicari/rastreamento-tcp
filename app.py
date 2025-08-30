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
@st.cache_data(ttl=600, show_spinner=False)
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
colunas_desejadas = ["Navio", "ViagemTcp", "ArmadorNome", "PrevisaoAtracacao"]
df_navios = df_navios[colunas_desejadas].copy()
df_navios["PrevisaoAtracacao"] = pd.to_datetime(df_navios["PrevisaoAtracacao"], errors="coerce")

# Mantém só a última previsão de cada navio+viagem
df_navios = df_navios.sort_values("PrevisaoAtracacao").drop_duplicates(subset=["Navio", "ViagemTcp"], keep="last")

# ==========================
# EXEMPLO INTERNO DE PEDIDOS
# ==========================
df_pedidos = pd.DataFrame({
    "Pedido": ["CROP193/25_PR", "CROP140/25A_PR", "CROP098/25_RS"],
    "Produto": ["KRATON 100 EC", "KRATON 100 EC", "CHARRUA 430 SC"],
    "Quantidade": [115.500, 46.200, 86.400],
    "Navio": ["SEASPAN ZAMBEZI", "SEASPAN ZAMBEZI", "CMA CGM MERCANTOUR"],
    "ViagemTcp": ["2528W", "2528W", "1GB0AN1MA"]
})

# ==========================
# PADRONIZAÇÃO DE STRINGS
# ==========================
for df in [df_navios, df_pedidos]:
    df["Navio"] = df["Navio"].astype(str).str.strip().str.upper()
    df["ViagemTcp"] = df["ViagemTcp"].astype(str).str.strip().str.upper()

# ==========================
# RELACIONAR PEDIDOS COM NAVIOS
# ==========================
df_result = df_pedidos.merge(df_navios, on=["Navio", "ViagemTcp"], how="left")

# ==========================
# FORMATAÇÃO DE DADOS
# ==========================
# Formatar data para PT-BR
df_result["PrevisaoAtracacao"] = df_result["PrevisaoAtracacao"].dt.strftime("%d/%m/%Y %H:%M")
df_navios["PrevisaoAtracacao"] = df_navios["PrevisaoAtracacao"].dt.strftime("%d/%m/%Y %H:%M")

# Formatar quantidade com 3 casas decimais
df_result["Quantidade"] = df_result["Quantidade"].map(
    lambda x: f"{x:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
)

# ==========================
# ESTILIZAR TABELAS CENTRALIZADAS
# ==========================
def style_centralizado(df):
    return df.style.set_properties(**{
        'text-align': 'center',
        'vertical-align': 'middle'
    })

# ==========================
# RESULTADO FINAL
# ==========================
st.subheader(f"🚢 Rastreamento de Embarques TCP ({len(df_result)})")
st.dataframe(style_centralizado(df_result), use_container_width=True)

st.subheader("📊 Programação de Navios (API TCP)")
st.dataframe(style_centralizado(df_navios), use_container_width=True)
