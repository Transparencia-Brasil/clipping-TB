"""
App Streamlit da Fase 1 do projeto de clipping da Transparência Brasil.

Recebe a exportação bruta da Palver (CSV ou XLSX) e devolve o arquivo
no MODELO IDEAL, pronto para download ou visualização em tela.
"""

import io

import pandas as pd
import streamlit as st

from tasks.task1.src.transform import transform_palver_export

st.set_page_config(page_title="Clipping TB — Modelo Ideal", layout="wide")

st.title("Transformação do Clipping Palver em Modelo Ideal")
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