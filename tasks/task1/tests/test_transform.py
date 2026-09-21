import pandas as pd
import pytest

from src.transform import transform_palver_export, IDEAL_COLUMN_ORDER, validate_input_columns


def _linha_exemplo(**overrides):
    linha = {
        "ID": "abc123",
        "Date": "2026-07-01",
        "Title": "Título de exemplo",
        "Source Name": "Veículo Exemplo",
        "Source": "News",
        "Source Tier": 3.0,
        "Área Temática": "Institucional",
        "Tema": None,
        "Projeto": None,
        "Relatório": None,
        "Confiança (auto)": "Alta",
        "Views": 120.5,
        "Impressions": 3000.0,
        "Public Link": "https://clip.palver.com.br/shared/news/abc123",
    }
    linha.update(overrides)
    return linha


def test_transform_gera_colunas_no_modelo_ideal():
    df = pd.DataFrame([_linha_exemplo()])
    resultado = transform_palver_export(df)
    assert list(resultado.columns) == IDEAL_COLUMN_ORDER


def test_transform_preserva_quantidade_de_linhas():
    df = pd.DataFrame([_linha_exemplo(), _linha_exemplo(ID="def456")])
    resultado = transform_palver_export(df)
    assert len(resultado) == 2


def test_transform_converte_colunas_numericas():
    df = pd.DataFrame([_linha_exemplo(**{"Source Tier": "3"})])
    resultado = transform_palver_export(df)
    assert resultado["Tier"].dtype.kind in ("f", "i")
    assert resultado["Tier"].iloc[0] == 3.0


def test_transform_falha_quando_falta_coluna_obrigatoria():
    df = pd.DataFrame([_linha_exemplo()]).drop(columns=["Source Tier"])
    with pytest.raises(ValueError):
        transform_palver_export(df)


def test_validate_input_columns_aceita_colunas_extras():
    df = pd.DataFrame([_linha_exemplo(**{"Coluna Extra Da Palver": "qualquer valor"})])
    validate_input_columns(df)