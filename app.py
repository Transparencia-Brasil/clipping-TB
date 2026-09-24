"""
App Streamlit do projeto de clipping da Transparência Brasil.

Fase 1: recebe a exportação bruta da Palver (CSV ou XLSX) e devolve o
arquivo no MODELO IDEAL, pronto para download ou visualização em tela.

Fase 2: recebe o MODELO IDEAL e classifica cada item por Tema e Área
Temática usando o modelo local servido pela instância Docker do Ollama.
"""

import io
import os

import pandas as pd
import requests
import streamlit as st

from tasks.fase02.src.classifica import (
    carrega_esquema,
    classifica_df,
    cria_classificador,
    monta_prompt_sistema,
)
from tasks.task1.src.transform import transform_palver_export

st.set_page_config(page_title="Clipping TB", layout="wide")


def le_arquivo(arquivo) -> pd.DataFrame:
    if arquivo.name.endswith(".csv"):
        return pd.read_csv(arquivo)
    return pd.read_excel(arquivo)


def para_csv(df: pd.DataFrame) -> str:
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()


def lista_modelos(base_url: str) -> list[str]:
    """Modelos disponíveis na instância; lista vazia se ela não responder."""
    try:
        resposta = requests.get(base_url.rstrip("/") + "/models", timeout=5)
        resposta.raise_for_status()
        return [modelo["id"] for modelo in resposta.json()["data"]]
    except (requests.RequestException, KeyError, ValueError):
        return []


def mostra_fase01():
    st.title("Transformação do Clipping Palver em Modelo Ideal")
    st.write(
        "Envie o arquivo exportado pela Palver (CSV ou XLSX) para gerar a "
        "versão no MODELO IDEAL, com colunas selecionadas, renomeadas e "
        "formatadas."
    )

    arquivo = st.file_uploader(
        "Exportação bruta da Palver",
        type=["csv", "xlsx"],
        key="arquivo_fase01",
    )

    if arquivo is not None:
        try:
            df_bruto = le_arquivo(arquivo)
        except Exception as erro:
            st.error(f"Não foi possível ler o arquivo enviado: {erro}")
            return

        try:
            df_ideal = transform_palver_export(df_bruto)
        except ValueError as erro:
            st.error(str(erro))
            return

        st.success(f"Arquivo transformado com sucesso: {len(df_ideal)} linhas.")

        st.subheader("Prévia do MODELO IDEAL")
        st.dataframe(df_ideal, use_container_width=True)

        st.download_button(
            label="Baixar CSV no MODELO IDEAL",
            data=para_csv(df_ideal),
            file_name="modelo_ideal.csv",
            mime="text/csv",
        )
    else:
        st.info("Aguardando o envio do arquivo da Palver.")


def mostra_fase02():
    st.title("Classificação por Área Temática")
    st.write(
        "Envie o CSV no MODELO IDEAL (saída da Fase 1). Cada item com título "
        "é classificado em um Tema do esquema da Transparência Brasil pelo "
        "modelo local; a Área Temática é derivada do Tema. Itens sem título "
        "(em geral rádio e TV) não são enviados ao modelo."
    )

    with st.expander("Configuração do modelo local"):
        base_url = st.text_input(
            "Endereço da API",
            value=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
        )
        modelos = lista_modelos(base_url)
        if modelos:
            modelo = st.selectbox("Modelo", modelos)
        else:
            st.warning("A instância não respondeu. Confira se o container do Ollama está rodando.")
            modelo = st.text_input("Modelo", value=os.environ.get("LLM_MODEL", ""))

    arquivo_ideal = st.file_uploader(
        "CSV no MODELO IDEAL",
        type=["csv", "xlsx"],
        key="arquivo_fase02",
    )

    if arquivo_ideal is None:
        st.info("Aguardando o envio do arquivo no MODELO IDEAL.")
    else:
        try:
            df_ideal = le_arquivo(arquivo_ideal)
        except Exception as erro:
            st.error(f"Não foi possível ler o arquivo enviado: {erro}")
            return

        com_titulo = df_ideal["Título"].fillna("").astype(str).str.strip().ne("").sum()
        st.write(f"{len(df_ideal)} itens no arquivo, {com_titulo} com título para classificar.")

        if st.button("Classificar", type="primary", disabled=not modelo):
            esquema = carrega_esquema()
            classificar = cria_classificador(
                monta_prompt_sistema(esquema), esquema["Tema"].tolist(), base_url, modelo
            )
            barra = st.progress(0.0)

            def ao_progredir(feitos, total):
                barra.progress(feitos / total, text=f"Classificando item {feitos} de {total}")

            classificado, auditoria = classifica_df(df_ideal, esquema, classificar, ao_progredir)
            barra.empty()
            # Guarda o resultado para que os downloads não disparem nova classificação.
            st.session_state["resultado_fase02"] = (arquivo_ideal.name, classificado, auditoria)

        resultado = st.session_state.get("resultado_fase02")
        if resultado is not None and resultado[0] == arquivo_ideal.name:
            _, classificado, auditoria = resultado
            st.success(f"{classificado['Tema'].notna().sum()} itens classificados.")

            st.subheader("Itens por Área Temática")
            st.dataframe(
                classificado["Área Temática"].value_counts(dropna=False).rename_axis("Área Temática"),
                use_container_width=True,
            )

            st.subheader("Prévia da classificação")
            previa = classificado.merge(auditoria[["ID", "Justificativa"]], on="ID", how="left")
            st.dataframe(
                previa[["Título", "Veículo", "Área Temática", "Tema", "Confiança (auto)", "Justificativa"]],
                use_container_width=True,
            )

            coluna_1, coluna_2 = st.columns(2)
            coluna_1.download_button(
                label="Baixar CSV classificado",
                data=para_csv(classificado),
                file_name="classificado.csv",
                mime="text/csv",
            )
            coluna_2.download_button(
                label="Baixar auditoria (justificativas)",
                data=para_csv(auditoria),
                file_name="classificado_auditoria.csv",
                mime="text/csv",
            )


aba_fase01, aba_fase02 = st.tabs(["Fase 1 — Modelo Ideal", "Fase 2 — Classificação"])

with aba_fase01:
    mostra_fase01()

with aba_fase02:
    mostra_fase02()
