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
df_navios = pd.json_normalize(dados)
colunas_desejadas = ["Navio", "ArmadorNome", "PrevisaoAtracacao"]
df_navios = df_navios[colunas_desejadas]
df_navios["PrevisaoAtracacao"] = pd.to_datetime(df_navios["PrevisaoAtracacao"], errors="coerce")

# ==========================
# MANTER APENAS ÚLTIMA PREVISÃO POR NAVIO
# ==========================
df_navios = df_navios.sort_values("PrevisaoAtracacao").drop_duplicates(subset=["Navio"], keep="last")

# ==========================
# CRIAR DATAFRAME DE PEDIDOS SIMULADO
# ==========================
# Usamos alguns navios da API para simular pedidos
num_simulados = min(5, len(df_navios))  # pega até 5 navios
df_pedidos = pd.DataFrame({
    "PedidoID": range(1, num_simulados + 1),
    "Navio": df_navios["Navio"].iloc[:num_simulados].tolist(),
    "Produto": [f"Produto {i}" for i in range(1, num_simulados + 1)],
    "Quantidade": [10, 20, 15, 5, 12][:num_simulados]
})

# ==========================
# MERGE DOS PEDIDOS COM NAVIOS
# ==========================
df_result = df_pedidos.merge(df_navios, on="Navio", how="left")

st.write(f"Mostrando {len(df_result)} pedidos com previsão de chegada")
st.dataframe(df_result)
