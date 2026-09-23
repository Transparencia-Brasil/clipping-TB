"""
App Streamlit da Fase 1 do projeto de clipping da Transparência Brasil.

Recebe a exportação bruta da Palver (CSV ou XLSX) e devolve o arquivo
no MODELO IDEAL, pronto para download ou visualização em tela.
"""

import base64
import io
import os

import pandas as pd
import streamlit as st

from tasks.task1.src.transform import transform_palver_export

st.set_page_config(page_title="Clipping TB — Modelo Ideal", layout="wide")

COR_VERDE_AGUA = "#39b1bb"
COR_LARANJA = "#f9a124"
CAMINHO_LOGO_SVG = os.path.join(os.path.dirname(__file__), "assets", "logo.svg")
CAMINHO_LOGO = os.path.join(os.path.dirname(__file__), "assets", "logo.png")


def _logo_svg_inline():
    """Lê o SVG da marca e devolve como HTML embutido, já com a cor
    laranja da marca aplicada ao traço que usa currentColor."""
    if not os.path.exists(CAMINHO_LOGO_SVG):
        return None
    with open(CAMINHO_LOGO_SVG, "r", encoding="utf-8") as arquivo_svg:
        svg = arquivo_svg.read().strip()
    svg = svg.replace(
        "<svg ",
        f'<svg style="height:44px;width:auto;vertical-align:middle;color:{COR_LARANJA};" ',
        1,
    )
    return f'<span style="display:inline-flex;align-items:center;margin-right:1rem;">{svg}</span>'


def _logo_em_base64():
    """Lê o arquivo de logo do disco e devolve em base64, se ele existir."""
    if not os.path.exists(CAMINHO_LOGO):
        return None
    with open(CAMINHO_LOGO, "rb") as arquivo_logo:
        return base64.b64encode(arquivo_logo.read()).decode("utf-8")


logo_svg_html = _logo_svg_inline()
if logo_svg_html:
    logo_html = logo_svg_html
else:
    logo_base64 = _logo_em_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_base64}" style="height:44px;margin-right:1rem;">'
        if logo_base64
        else ""
    )

cabecalho_css = (
    "<style>"
    f".cabecalho-tb{{background-color:{COR_VERDE_AGUA};padding:1rem 1.5rem;"
    "border-radius:8px;margin-bottom:1.5rem;display:flex;align-items:center;}"
    ".cabecalho-tb h1{color:#ffffff;font-size:1.4rem;margin:0;}"
    "</style>"
)
cabecalho_html = (
    f'<div class="cabecalho-tb">{logo_html}'
    "<h1>Transformação do Clipping Palver em Modelo Ideal</h1></div>"
)
st.markdown(cabecalho_css + cabecalho_html, unsafe_allow_html=True)

st.write(
    "Envie o arquivo exportado pela Palver (CSV ou XLSX) para gerar a "
    "versão no MODELO IDEAL, com colunas selecionadas, renomeadas e "
    "formatadas."
)

arquivo = st.file_uploader(
    "Exportação bruta da Palver",
    type=["csv", "xlsx"],
)

if arquivo is not None:
    try:
        if arquivo.name.endswith(".csv"):
            df_bruto = pd.read_csv(arquivo)
        else:
            df_bruto = pd.read_excel(arquivo)
    except Exception as erro:
        st.error(f"Não foi possível ler o arquivo enviado: {erro}")
        st.stop()

    try:
        df_ideal = transform_palver_export(df_bruto)
    except ValueError as erro:
        st.error(str(erro))
        st.stop()

    st.success(f"Arquivo transformado com sucesso: {len(df_ideal)} linhas.")

    st.subheader("Prévia do MODELO IDEAL")
    st.dataframe(df_ideal, use_container_width=True)

    csv_buffer = io.StringIO()
    df_ideal.to_csv(csv_buffer, index=False)

    st.download_button(
        label="Baixar CSV no MODELO IDEAL",
        data=csv_buffer.getvalue(),
        file_name="modelo_ideal.csv",
        mime="text/csv",
    )
else:
    st.info("Aguardando o envio do arquivo da Palver.")