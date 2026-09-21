"""
Transforma a exportação bruta da Palver no MODELO IDEAL utilizado
pela Transparência Brasil para geração de relatórios.
"""

import pandas as pd


# Mapeamento das colunas da exportação original da Palver para o
# nome final de cada coluna no MODELO IDEAL.
COLUMN_MAPPING = {
    "ID": "ID",
    "Date": "Data",
    "Title": "Título",
    "Source Name": "Veículo",
    "Source": "Tipo de mídia",
    "Source Tier": "Tier",
    "Área Temática": "Área Temática",
    "Tema": "Tema",
    "Projeto": "Projeto",
    "Relatório": "Relatório",
    "Confiança (auto)": "Confiança (auto)",
    "Views": "Visualizações",
    "Impressions": "Impressões",
    "Public Link": "Link",
}

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
]

# Colunas numéricas no MODELO IDEAL, usadas para garantir o tipo correto.
NUMERIC_COLUMNS = ["Tier", "Visualizações", "Impressões"]


def validate_input_columns(df: pd.DataFrame) -> None:
    """Garante que todas as colunas esperadas existem na exportação bruta."""
    colunas_esperadas = set(COLUMN_MAPPING.keys())
    colunas_recebidas = set(df.columns)
    faltando = colunas_esperadas - colunas_recebidas
    if faltando:
        raise ValueError(
            "A exportação recebida não contém as colunas esperadas da Palver: "
            f"{sorted(faltando)}"
        )


def transform_palver_export(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe o dataframe bruto exportado pela Palver (todas as colunas
    originais) e devolve o dataframe no MODELO IDEAL: apenas as colunas
    relevantes, renomeadas, reordenadas e com os tipos ajustados.
    """
    validate_input_columns(df)

    colunas_originais = list(COLUMN_MAPPING.keys())
    df_ideal = df[colunas_originais].rename(columns=COLUMN_MAPPING)
    df_ideal = df_ideal[IDEAL_COLUMN_ORDER]

    for coluna in NUMERIC_COLUMNS:
        df_ideal[coluna] = pd.to_numeric(df_ideal[coluna], errors="coerce")

    df_ideal["Data"] = pd.to_datetime(df_ideal["Data"], errors="coerce").dt.date

    return df_ideal