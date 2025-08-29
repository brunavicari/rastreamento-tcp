import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import os

# ==========================
# CONFIGURAÇÕES
# ==========================
API_URL = "https://api.tcp.com.br/tos-bridge/v1/programacao-navios/pesquisar"
PAGE_SIZE = 100
MAX_PAGINAS = 20
PLANILHA_PEDIDOS = "pedidos.xlsx"  # deve estar na mesma pasta do app.py

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

        registros = data.get("Objeto", []) if isinstance(data, dict) else data
        if not registros:
            break

        todos_dados.extend(registros)
        pagina += 1
        if pagina > MAX_PAGINAS:
            break

    return todos_dados

# ==========================
# PEGAR DADOS DA API
# ==========================
st.info("Consultando API TCP...")
dados = pegar_programacao_navios()
if not dados:
    st.warning("Nenhum dado retornado da API.")
    st.stop()

df_navios = pd.json_normalize(dados)
colunas_desejadas = ["Navio", "ArmadorNome", "PrevisaoAtracacao"]
df_navios = df_navios[colunas_desejadas]
df_navios["PrevisaoAtracacao"] = pd.to_datetime(df_navios["PrevisaoAtracacao"], errors="coerce")

# ==========================
# MANTER APENAS ÚLTIMA PREVISÃO POR NAVIO
# ==========================
df_navios = df_navios.sort_values("PrevisaoAtracacao").drop_duplicates(subset=["Navio"], keep="last")

# ==========================
# CARREGAR PLANILHA DE PEDIDOS AUTOMATICAMENTE
# ==========================
if os.path.exists(PLANILHA_PEDIDOS):
    df_pedidos = pd.read_excel(PLANILHA_PEDIDOS)
else:
    st.error(f"Não foi possível encontrar '{PLANILHA_PEDIDOS}' na pasta do app.")
    st.stop()

# ==========================
# MERGE DOS PEDIDOS COM NAVIOS
# ==========================
# Supondo que sua planilha tenha uma coluna "Navio"
df_result = df_pedidos.merge(df_navios, on="Navio", how="left")

# ==========================
# FILTROS INTERATIVOS OPCIONAIS
# ==========================
pedido_filtro = st.text_input("Filtrar por pedido (opcional):")
produto_filtro = st.text_input("Filtrar por produto/armador (opcional):")

df_filtrado = df_result.copy()
if pedido_filtro:
    df_filtrado = df_filtrado[df_filtrado['Pedido'].str.contains(pedido_filtro, case=False, na=False)]
if produto_filtro:
    df_filtrado = df_filtrado[df_filtrado['Produto'].str.contains(produto_filtro, case=False, na=False)]

st.write(f"Mostrando {len(df_filtrado)} pedidos")
st.dataframe(df_filtrado)
