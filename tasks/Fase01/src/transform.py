"""
Transforma a exportação bruta da Palver no MODELO IDEAL utilizado
pela Transparência Brasil para geração de relatórios.
"""

import pandas as pd


# Mapeamento das colunas da exportação original da Palver para o
# nome final de cada coluna no MODELO IDEAL. A Palver exporta no idioma
# da conta, então há um mapeamento para inglês e outro para português.
COLUMN_MAPPING = {
    "ID": "ID",
    "Date": "Data",
    "Title": "Título",
    "Source Name": "Veículo",
    "Source": "Tipo de mídia",
    "Source Tier": "Tier",
    "Views": "Visualizações",
    "Impressions": "Impressões",
    "Public Link": "Link",
    "Content": "Conteúdo",
}

COLUMN_MAPPING_PT = {
    "ID": "ID",
    "Data": "Data",
    "Título": "Título",
    "Veículo": "Veículo",
    "Fonte": "Tipo de mídia",
    "Tier do Veículo": "Tier",
    "Visualizações": "Visualizações",
    "Impressões": "Impressões",
    "Link Público": "Link",
    "Conteúdo": "Conteúdo",
}

# Tipos de mídia da exportação em inglês traduzidos para os nomes usados
# pela Palver em português, para que o MODELO IDEAL não misture idiomas.
# "Press" não apareceu em exportações em português; "Impresso" é suposição.
MEDIA_TYPE_PT = {
    "News": "Notícias",
    "Radio": "Rádio",
    "Television": "Televisão",
    "YouTube": "YouTube",
    "Press": "Impresso",
}

# Colunas de classificação preenchidas pela TB (a fase 02 preenche
# Área Temática, Tema e Confiança). A exportação da Palver não as traz;
# quando ausentes, são criadas vazias.
CLASSIFICATION_COLUMNS = ["Área Temática", "Tema", "Projeto", "Relatório", "Confiança (auto)"]

# Ordem final das colunas no MODELO IDEAL.
IDEAL_COLUMN_ORDER = [
    "ID",
    "Data",
    "Título",
    "Veículo",
    "Tipo de mídia",
    "Tier",
    "Área Temática",
    "Tema",
    "Projeto",
    "Relatório",
    "Confiança (auto)",
    "Visualizações",
    "Impressões",
    "Link",
    # Texto integral ou transcrição (rádio e TV); usado na classificação da fase 02.
    "Conteúdo",
]

# Colunas numéricas no MODELO IDEAL, usadas para garantir o tipo correto.
NUMERIC_COLUMNS = ["Tier", "Visualizações", "Impressões"]


def validate_input_columns(df: pd.DataFrame) -> dict:
    """
    Garante que todas as colunas esperadas existem na exportação bruta, em
    inglês ou em português, e devolve o mapeamento do idioma encontrado.
    """
    colunas_recebidas = set(df.columns)
    faltando_por_mapeamento = [
        (sorted(set(mapeamento) - colunas_recebidas), mapeamento)
        for mapeamento in (COLUMN_MAPPING, COLUMN_MAPPING_PT)
    ]
    # Reporta as faltantes do idioma mais próximo do arquivo recebido.
    faltando, mapeamento = min(faltando_por_mapeamento, key=lambda par: len(par[0]))
    if faltando:
        raise ValueError(
            "A exportação recebida não contém as colunas esperadas da Palver: "
            f"{faltando}"
        )
    return mapeamento


def transform_palver_export(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe o dataframe bruto exportado pela Palver (todas as colunas
    originais) e devolve o dataframe no MODELO IDEAL: apenas as colunas
    relevantes, renomeadas, reordenadas e com os tipos ajustados.
    """
    mapeamento = validate_input_columns(df)

    colunas_originais = list(mapeamento.keys())
    df_ideal = df[colunas_originais].rename(columns=mapeamento)
    df_ideal["Tipo de mídia"] = df_ideal["Tipo de mídia"].replace(MEDIA_TYPE_PT)
    for coluna in CLASSIFICATION_COLUMNS:
        df_ideal[coluna] = df[coluna] if coluna in df.columns else pd.NA
    df_ideal = df_ideal[IDEAL_COLUMN_ORDER]

    for coluna in NUMERIC_COLUMNS:
        df_ideal[coluna] = pd.to_numeric(df_ideal[coluna], errors="coerce")

    df_ideal["Data"] = pd.to_datetime(df_ideal["Data"], errors="coerce").dt.date

    return df_ideal