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

st.title("Rastreamento de Embarques TCP")

# ==========================
# FUNÇÃO PARA PEGAR NAVIOS
# ==========================
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
            st.error(f"Erro na requisição da página {pagina}: {e}")
            break

        registros = []
        if isinstance(data, dict):
            registros = data.get("Objeto", [])
        elif isinstance(data, list):
            registros = data

        if not registros:
            break

        todos_dados.extend(registros)
        pagina += 1
        if pagina > MAX_PAGINAS:
            break

    return todos_dados

# ==========================
# PEGAR DADOS
# ==========================
st.info("Consultando API TCP...")
dados = pegar_programacao_navios()
if not dados:
    st.warning("Nenhum dado retornado da API.")
    st.stop()

# ==========================
# NORMALIZAR E FILTRAR COLUNAS
# ==========================
df = pd.json_normalize(dados)
colunas_desejadas = ["Navio", "ArmadorNome", "PrevisaoAtracacao"]
df = df[colunas_desejadas]
df["PrevisaoAtracacao"] = pd.to_datetime(df["PrevisaoAtracacao"], errors="coerce")

# ==========================
# FILTROS INTERATIVOS
# ==========================
pedido = st.text_input("Buscar por pedido (nome do navio):")
produto = st.text_input("Buscar por produto (armador):")

df_filtrado = df.copy()
if pedido:
    df_filtrado = df_filtrado[df_filtrado['Navio'].str.contains(pedido, case=False)]
if produto:
    df_filtrado = df_filtrado[df_filtrado['ArmadorNome'].str.contains(produto, case=False)]

st.write(f"Mostrando {len(df_filtrado)} resultados")
st.dataframe(df_filtrado)
