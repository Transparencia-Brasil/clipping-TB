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

from tasks.Fase01.src.transform import transform_palver_export

st.set_page_config(
    page_title="Clipping TB",
    # Logo com o "T" já em laranja: um favicon não herda cor, então currentColor sairia preto.
    page_icon=os.path.join(os.path.dirname(__file__), "assets", "favicon.svg"),
    layout="wide",
)

# Paleta extraída de transparencia.org.br (as mesmas cores de .streamlit/config.toml).
COR_VERDE_AGUA = "#39b1bb"
COR_VERDE_AGUA_CLARO = "#91d4d9"
COR_LARANJA = "#f9a124"
COR_LARANJA_ESCURO = "#e08a0c"
COR_TEXTO = "#3e3e3e"
COR_TEXTO_SECUNDARIO = "#666666"
COR_TEXTO_SOBRE_LARANJA = "#1d1d1b"
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

estilo_css = f"""
<style>
/* Cabeçalho: faixa branca com o logo, como no topo do site, e filete laranja. */
.cabecalho-tb {{
    display: flex;
    align-items: center;
    padding: 0.25rem 0 1rem;
    margin-bottom: 1.5rem;
    border-bottom: 4px solid {COR_LARANJA};
}}
.cabecalho-tb .marca {{
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {COR_TEXTO_SECUNDARIO};
    margin: 0;
}}
.cabecalho-tb h1 {{
    color: {COR_TEXTO};
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1.25;
    margin: 0;
    padding: 0;
}}

/* Subtítulos com o marcador laranja usado nas seções do site. */
[data-testid="stHeadingWithActionElements"] h3 {{
    border-left: 4px solid {COR_LARANJA};
    padding-left: 0.6rem;
}}

/* Botões principais: laranja com texto escuro (branco sobre laranja não tem contraste). */
[data-testid="stBaseButton-primary"] {{
    color: {COR_TEXTO_SOBRE_LARANJA};
    font-weight: 600;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background-color: {COR_LARANJA_ESCURO};
    border-color: {COR_LARANJA_ESCURO};
    color: {COR_TEXTO_SOBRE_LARANJA};
}}

/* Área de upload em verde-água, a cor de apoio da marca. */
[data-testid="stFileUploaderDropzone"] {{
    border: 2px dashed {COR_VERDE_AGUA_CLARO};
}}
</style>
"""
cabecalho_html = (
    f'<div class="cabecalho-tb">{logo_html}<div>'
    '<p class="marca">Transparência Brasil · Clipping</p>'
    "<h1>Transformação do Clipping Palver em Modelo Ideal</h1>"
    "</div></div>"
)
st.markdown(estilo_css + cabecalho_html, unsafe_allow_html=True)

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
    st.dataframe(df_ideal, width="stretch")

    csv_buffer = io.StringIO()
    df_ideal.to_csv(csv_buffer, index=False)

    st.download_button(
        label="Baixar CSV no MODELO IDEAL",
        data=csv_buffer.getvalue(),
        file_name="modelo_ideal.csv",
        mime="text/csv",
        type="primary",
    )
else:
    st.info("Aguardando o envio do arquivo da Palver.")