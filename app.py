"""
App Streamlit do projeto de clipping da Transparência Brasil.

Fase 1: recebe a exportação bruta da Palver (CSV ou XLSX) e devolve o
arquivo no MODELO IDEAL, pronto para download ou visualização em tela.

Fase 2: recebe o MODELO IDEAL e classifica cada item por Tema e Área
Temática usando o modelo local servido pela instância Docker do Ollama.
"""

import base64
import html
import io
import os

import pandas as pd
import requests
import streamlit as st

from tasks.Fase01.src.transform import transform_palver_export
from tasks.fase02.src.classifica import (
    NUM_CTX_PADRAO,
    carrega_guia,
    classifica_df,
    cria_classificadores,
    tem_conteudo,
)

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
        f'<svg style="height:60px;width:auto;vertical-align:middle;color:{COR_LARANJA};" ',
        1,
    )
    return f'<span style="display:inline-flex;align-items:center;margin-right:1.1rem;">{svg}</span>'


def _logo_em_base64():
    """Lê o arquivo de logo do disco e devolve em base64, se ele existir."""
    if not os.path.exists(CAMINHO_LOGO):
        return None
    with open(CAMINHO_LOGO, "rb") as arquivo_logo:
        return base64.b64encode(arquivo_logo.read()).decode("utf-8")


def formata_numero(numero) -> str:
    """Número inteiro com ponto de milhar, no padrão brasileiro."""
    return f"{int(numero):,}".replace(",", ".")


def le_arquivo(arquivo) -> pd.DataFrame:
    if arquivo.name.endswith(".csv"):
        return pd.read_csv(arquivo)
    return pd.read_excel(arquivo)


FORMATOS_DOWNLOAD = ["Excel (.xlsx)", "CSV"]


def gera_arquivo(df: pd.DataFrame, formato: str, nome_planilha: str) -> tuple[bytes, str, str]:
    """Devolve (conteúdo, extensão, mime) do dataframe no formato escolhido para download."""
    if formato == "CSV":
        # utf-8-sig para o Excel abrir o CSV com os acentos corretos.
        return df.to_csv(index=False).encode("utf-8-sig"), "csv", "text/csv"
    xlsx_buffer = io.BytesIO()
    df.to_excel(xlsx_buffer, index=False, sheet_name=nome_planilha)
    return (
        xlsx_buffer.getvalue(),
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def lista_modelos(base_url: str) -> list[str] | None:
    """Modelos carregados no Ollama; None se ele não responder."""
    try:
        resposta = requests.get(base_url.rstrip("/") + "/api/tags", timeout=5)
        resposta.raise_for_status()
        return [modelo["name"] for modelo in resposta.json().get("models") or []]
    except (requests.RequestException, KeyError, ValueError):
        return None


logo_svg_html = _logo_svg_inline()
if logo_svg_html:
    logo_html = logo_svg_html
else:
    logo_base64 = _logo_em_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_base64}" style="height:60px;margin-right:1rem;">'
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
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {COR_TEXTO_SECUNDARIO};
    margin: 0;
}}
.cabecalho-tb h1 {{
    color: {COR_TEXTO};
    font-size: 2.1rem;
    font-weight: 700;
    line-height: 1.2;
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

/* Resumo: cartões em uma linha; os tipos de mídia viram etiquetas no último cartão. */
.resumo-tb {{
    display: grid;
    grid-template-columns: 1fr 1.4fr 1fr 2.2fr;
    gap: 0.75rem;
    margin-bottom: 1rem;
}}
.resumo-tb .cartao {{
    border: 1px solid #e3e3e3;
    border-top: 3px solid {COR_LARANJA};
    border-radius: 6px;
    padding: 0.75rem 1rem;
    background: #ffffff;
}}
.resumo-tb .rotulo {{
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: {COR_TEXTO_SECUNDARIO};
    margin: 0 0 0.35rem;
}}
.resumo-tb .valor {{
    font-size: 1.5rem;
    font-weight: 700;
    color: {COR_TEXTO};
    line-height: 1.2;
    margin: 0;
}}
.resumo-tb .etiquetas {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
}}
.resumo-tb .etiqueta {{
    background: #eaf6f7;
    color: #1f6f76;
    border-radius: 999px;
    padding: 0.15rem 0.6rem;
    font-size: 0.85rem;
    white-space: nowrap;
}}
@media (max-width: 900px) {{
    .resumo-tb {{ grid-template-columns: 1fr 1fr; }}
}}

/* Área de upload em verde-água, a cor de apoio da marca. */
[data-testid="stFileUploaderDropzone"] {{
    border: 2px dashed {COR_VERDE_AGUA_CLARO};
}}
</style>
"""
cabecalho_html = (
    f'<div class="cabecalho-tb">{logo_html}<div>'
    '<p class="marca">Transparência Brasil</p>'
    "<h1>Conversor Clipping</h1>"
    "</div></div>"
)
st.markdown(estilo_css + cabecalho_html, unsafe_allow_html=True)


def mostra_fase01():
    st.write(
        "Envie o arquivo exportado pelo Palver (CSV ou XLSX) para gerar a "
        "versão no modelo ideal desejado, com colunas selecionadas, renomeadas e "
        "formatadas."
    )

    arquivo = st.file_uploader(
        "Exportação bruta do Palver",
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
            return

        try:
            df_ideal = transform_palver_export(df_bruto)
        except ValueError as erro:
            st.error(str(erro))
            return

        st.success("Arquivo transformado com sucesso.")

        # Resumo para conferir a exportação antes de baixar.
        datas = pd.to_datetime(df_ideal["Data"], errors="coerce")
        data_inicio, data_fim = datas.min(), datas.max()
        sem_titulo = df_ideal["Título"].fillna("").astype(str).str.strip().eq("").sum()

        if pd.isna(data_inicio):
            periodo = "Sem datas"
        elif data_inicio.year == data_fim.year:
            periodo = f"{data_inicio:%d/%m} a {data_fim:%d/%m/%Y}"
        else:
            periodo = f"{data_inicio:%d/%m/%Y} a {data_fim:%d/%m/%Y}"

        contagem_midia = df_ideal["Tipo de mídia"].fillna("Não informado").value_counts()
        etiquetas_midia = "".join(
            f'<span class="etiqueta">{html.escape(str(tipo))} <b>{formata_numero(quantidade)}</b></span>'
            for tipo, quantidade in contagem_midia.items()
        )

        st.subheader("Resumo")
        st.markdown(
            '<div class="resumo-tb">'
            f'<div class="cartao"><p class="rotulo">Itens</p><p class="valor">{formata_numero(len(df_ideal))}</p></div>'
            f'<div class="cartao"><p class="rotulo">Período</p><p class="valor">{periodo}</p></div>'
            f'<div class="cartao"><p class="rotulo">Sem título</p><p class="valor">{formata_numero(sem_titulo)}</p></div>'
            f'<div class="cartao"><p class="rotulo">Tipos de mídia</p><div class="etiquetas">{etiquetas_midia}</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )

        st.subheader("Prévia do arquivo no modelo ideal")
        coluna_filtro_midia, coluna_busca = st.columns([1, 2])
        tipos_selecionados = coluna_filtro_midia.multiselect(
            "Tipo de mídia",
            options=contagem_midia.index.tolist(),
            placeholder="Todos",
        )
        busca = coluna_busca.text_input("Buscar no título", placeholder="Ex.: emendas")

        previa = df_ideal
        if tipos_selecionados:
            previa = previa[previa["Tipo de mídia"].isin(tipos_selecionados)]
        if busca:
            previa = previa[previa["Título"].fillna("").str.contains(busca, case=False, regex=False)]

        st.caption(
            f"Mostrando {formata_numero(len(previa))} de {formata_numero(len(df_ideal))} itens. "
            "Os filtros valem só para a prévia; o download traz o arquivo completo."
        )
        st.dataframe(
            previa,
            width="stretch",
            hide_index=True,
            column_config={
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Tier": st.column_config.NumberColumn("Tier", format="%d"),
                "Visualizações": st.column_config.NumberColumn("Visualizações", format="localized"),
                "Impressões": st.column_config.NumberColumn("Impressões", format="localized"),
                "Link": st.column_config.LinkColumn("Link", display_text="Abrir"),
            },
        )

        formato = st.radio("Formato do arquivo", FORMATOS_DOWNLOAD, horizontal=True, key="formato_fase01")
        dados, extensao, mime = gera_arquivo(df_ideal, formato, "Modelo Ideal")

        # O período no nome evita confundir arquivos de meses diferentes.
        if pd.isna(data_inicio):
            sufixo_periodo = ""
        elif data_inicio.date() == data_fim.date():
            sufixo_periodo = f"_{data_inicio:%Y-%m-%d}"
        else:
            sufixo_periodo = f"_{data_inicio:%Y-%m-%d}_a_{data_fim:%Y-%m-%d}"

        st.download_button(
            label=f"Baixar {extensao.upper()}",
            data=dados,
            file_name=f"modelo_ideal_arquivo_convertido{sufixo_periodo}.{extensao}",
            mime=mime,
            type="primary",
        )
    else:
        st.info("Aguardando o envio do arquivo do Palver.")


def mostra_fase02():
    st.subheader("Classificação por Área Temática")
    st.write(
        "Envie o arquivo no MODELO IDEAL (saída da Fase 1). O modelo local classifica "
        "cada item seguindo o guia de classificação da Transparência Brasil, a partir "
        "do título e do conteúdo (texto ou transcrição), e preenche Área Temática 1, "
        "Tema, Projeto e Relatório. Itens sem título nem conteúdo não são enviados ao modelo."
    )

    with st.expander("Configuração do modelo local"):
        base_url = st.text_input(
            "Endereço do Ollama",
            value=os.environ.get("LLM_BASE_URL", "http://localhost:11434"),
        )
        num_ctx = st.number_input(
            "Janela de contexto (tokens)",
            min_value=2048,
            step=2048,
            value=int(os.environ.get("LLM_NUM_CTX", NUM_CTX_PADRAO)),
            help="Precisa caber o guia inteiro, cerca de 8 mil tokens, mais a notícia.",
        )
        modelos = lista_modelos(base_url)
        if modelos:
            modelo = st.selectbox("Modelo", modelos)
        else:
            if modelos is None:
                st.warning("O Ollama não respondeu. Confira se o container está rodando.")
            else:
                st.warning("O Ollama está no ar, mas sem nenhum modelo carregado.")
            modelo = st.text_input("Modelo", value=os.environ.get("LLM_MODEL", ""))

    arquivo_ideal = st.file_uploader(
        "CSV no MODELO IDEAL",
        type=["csv", "xlsx"],
        key="arquivo_fase02",
    )

    if arquivo_ideal is None:
        st.info("Aguardando o envio do arquivo no MODELO IDEAL.")
        return

    try:
        df_ideal = le_arquivo(arquivo_ideal)
    except Exception as erro:
        st.error(f"Não foi possível ler o arquivo enviado: {erro}")
        return

    classificaveis = df_ideal.apply(tem_conteudo, axis=1).sum()
    st.write(f"{len(df_ideal)} itens no arquivo, {classificaveis} com título ou conteúdo para classificar.")
    if "Conteúdo" not in df_ideal.columns:
        st.warning(
            "O arquivo não tem a coluna Conteúdo; itens sem título (rádio e TV) "
            "ficarão sem classificação. Gere o MODELO IDEAL novamente na Fase 1."
        )

    if st.button("Classificar", type="primary", disabled=not modelo):
        guia = carrega_guia()
        classificadores = cria_classificadores(guia, base_url, modelo, int(num_ctx))
        barra = st.progress(0.0)

        def ao_progredir(etapa, feitos, total):
            barra.progress(feitos / total, text=f"{etapa}: item {feitos} de {total}")

        classificado, auditoria = classifica_df(df_ideal, guia, classificadores, ao_progredir)
        barra.empty()
        # Guarda o resultado para que os downloads não disparem nova classificação.
        st.session_state["resultado_fase02"] = (arquivo_ideal.name, classificado, auditoria)

    resultado = st.session_state.get("resultado_fase02")
    if resultado is None or resultado[0] != arquivo_ideal.name:
        return

    nome_enviado, classificado, auditoria = resultado
    # O arquivo baixado mantém o nome do enviado, com a tag "_classificado" no fim.
    nome_base = os.path.splitext(nome_enviado)[0] + "_classificado"
    st.success(f"{classificado['Área Temática 1'].notna().sum()} itens classificados.")

    st.subheader("Itens por Área Temática 1")
    st.dataframe(
        classificado["Área Temática 1"].value_counts(dropna=False).rename_axis("Área Temática 1"),
        width="stretch",
    )

    st.subheader("Prévia da classificação")
    previa = classificado.merge(auditoria[["ID", "Justificativa"]], on="ID", how="left")
    st.dataframe(
        previa[["Título", "Veículo", "Área Temática 1", "Tema", "Projeto", "Relatório", "Confiança (auto)", "Justificativa"]],
        width="stretch",
    )

    formato = st.radio("Formato do arquivo", FORMATOS_DOWNLOAD, horizontal=True, key="formato_fase02")
    dados_classificado, extensao, mime = gera_arquivo(classificado, formato, "Classificação")
    dados_auditoria, _, _ = gera_arquivo(auditoria, formato, "Auditoria")

    coluna_1, coluna_2 = st.columns(2)
    coluna_1.download_button(
        label=f"Baixar classificação ({extensao.upper()})",
        data=dados_classificado,
        file_name=f"{nome_base}.{extensao}",
        mime=mime,
        type="primary",
    )
    coluna_2.download_button(
        label=f"Baixar auditoria ({extensao.upper()})",
        data=dados_auditoria,
        file_name=f"{nome_base}_auditoria.{extensao}",
        mime=mime,
    )


aba_fase01, aba_fase02 = st.tabs(["Fase 1 — Modelo Ideal", "Fase 2 — Classificação"])

with aba_fase01:
    mostra_fase01()

with aba_fase02:
    mostra_fase02()
