"""
Transforma a exportação bruta da Palver no MODELO IDEAL utilizado
pela Transparência Brasil para geração de relatórios e classificação.
"""

import pandas as pd


# Mapeamento das colunas da exportação original da Palver (em
# português) para o nome final de cada coluna no MODELO IDEAL.
COLUMN_MAPPING = {
    "ID": "ID",
    "Data": "Data",
    "Título": "Título",
    "Veículo": "Veículo",
    "Fonte": "Tipo de mídia",
    "Tier do Veículo": "Tier",
    "Visualizações": "Visualizações",
    "Impressões": "Impressões",
    "Link Público": "Link",
}

# Colunas que não existem na exportação bruta da Palver: são
# preenchidas somente na Fase 2 (Classificação), então entram vazias
# no MODELO IDEAL nesta etapa.
COLUNAS_DE_CLASSIFICACAO = [
    "Área Temática",
    "Tema",
    "Projeto",
    "Relatório",
    "Confiança (auto)",
]

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
    originais, em português) e devolve o dataframe no MODELO IDEAL:
    apenas as colunas relevantes, renomeadas, reordenadas e com os
    tipos ajustados. As colunas de classificação (Área Temática, Tema,
    Projeto, Relatório, Confiança) saem vazias, para serem preenchidas
    na Fase 2.
    """
    validate_input_columns(df)

    colunas_originais = list(COLUMN_MAPPING.keys())
    df_ideal = df[colunas_originais].rename(columns=COLUMN_MAPPING)

    for coluna in COLUNAS_DE_CLASSIFICACAO:
        df_ideal[coluna] = None

    df_ideal = df_ideal[IDEAL_COLUMN_ORDER]

    for coluna in NUMERIC_COLUMNS:
        df_ideal[coluna] = pd.to_numeric(df_ideal[coluna], errors="coerce")

    df_ideal["Data"] = pd.to_datetime(df_ideal["Data"], errors="coerce").dt.date

    return df_ideal