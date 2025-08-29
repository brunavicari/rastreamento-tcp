import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import streamlit_authenticator as stauth

st.set_page_config(page_title="Rastreamento de Embarques TCP", layout="wide")

# ==========================
# LOGIN INTERNO
# ==========================
# Defina seus usuários e senhas
users = {
    "brunavicari": "Crop123!4",   # você pode adicionar mais usuários
}

authenticator = stauth.Authenticate(users, "cookie_name", "signature_key", cookie_expiry_days=1)

name, authentication_status = authenticator.login("Login", "main")

if authentication_status:
    st.success(f"Bem-vinda, {name}!")

    # ==========================
    # CARREGAR PEDIDOS INTERNOS
    # ==========================
    st.sidebar.header("Filtros")
    pedidos_file = st.sidebar.file_uploader("Upload planilha de pedidos (Excel)", type=["xlsx"])
    if not pedidos_file:
        st.warning("Por favor, faça upload da planilha de pedidos internos (.xlsx)")
        st.stop()
    pedidos_df = pd.read_excel(pedidos_file)

    # ==========================
    # PEGAR PROGRAMACAO TCP
    # ==========================
    API_URL = "https://api.tcp.com.br/tos-bridge/v1/programacao-navios/pesquisar"
    PAGE_SIZE = 100
    MAX_PAGINAS = 20

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
            except:
                st.error(f"Erro ao consultar API na página {pagina}")
                break
            registros = data.get("Objeto", []) if isinstance(data, dict) else data
            if not registros:
                break
            todos_dados.extend(registros)
            pagina += 1
            if pagina > MAX_PAGINAS:
                break
        return todos_dados

    st.info("Consultando API TCP...")
    dados = pegar_programacao_navios()
    if not dados:
        st.warning("Nenhum dado retornado da API.")
        st.stop()

    tcp_df = pd.json_normalize(dados)[["Navio", "ArmadorNome", "PrevisaoAtracacao"]]
    tcp_df["PrevisaoAtracacao"] = pd.to_datetime(tcp_df["PrevisaoAtracacao"], errors="coerce")

    # ==========================
    # ASSOCIAÇÃO COM PEDIDOS INTERNOS
    # ==========================
    df = pd.merge(pedidos_df, tcp_df, on="Navio", how="left")

    # ==========================
    # FILTROS INTERATIVOS
    # ==========================
    pedido_input = st.sidebar.text_input("Buscar por pedido interno")
    produto_input = st.sidebar.text_input("Buscar por produto")

    df_filtrado = df.copy()
    if pedido_input:
        df_filtrado = df_filtrado[df_filtrado["PedidoInterno"].str.contains(pedido_input, case=False)]
    if produto_input:
        df_filtrado = df_filtrado[df_filtrado["Produto"].str.contains(produto_input, case=False)]

    st.write(f"Mostrando {len(df_filtrado)} resultados")
    st.dataframe(df_filtrado)

elif authentication_status == False:
    st.error("Usuário ou senha incorretos")
else:
    st.warning("Por favor, faça login")


