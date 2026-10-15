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
        "Área Temática 1": "Institucional",
        "Tema": None,
        "Projeto": None,
        "Relatório": None,
        "Confiança (auto)": "Alta",
        "Views": 120.5,
        "Impressions": 3000.0,
        "Public Link": "https://clip.palver.com.br/shared/news/abc123",
        "Content": "Texto integral de exemplo",
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


def test_transform_cria_colunas_de_classificacao_quando_ausentes():
    colunas_tb = ["Área Temática 1", "Tema", "Projeto", "Relatório", "Confiança (auto)"]
    df = pd.DataFrame([_linha_exemplo()]).drop(columns=colunas_tb)
    resultado = transform_palver_export(df)
    assert list(resultado.columns) == IDEAL_COLUMN_ORDER
    assert resultado[colunas_tb].isna().all().all()


def test_transform_preserva_colunas_de_classificacao_existentes():
    df = pd.DataFrame([_linha_exemplo()])
    resultado = transform_palver_export(df)
    assert resultado.loc[0, "Área Temática 1"] == "Institucional"


def _linha_exemplo_pt(**overrides):
    linha = {
        "ID": "abc123",
        "Data": "2026-09-22",
        "Título": "Título de exemplo",
        "Veículo": "Veículo Exemplo",
        "Fonte": "Notícias",
        "Tier do Veículo": 4.0,
        "Visualizações": None,
        "Impressões": 0.0,
        "Link Público": "https://clip.palver.com.br/shared/news/abc123",
        "Conteúdo": "Texto integral de exemplo",
    }
    linha.update(overrides)
    return linha


def test_transform_aceita_exportacao_em_portugues():
    df = pd.DataFrame([_linha_exemplo_pt()])
    resultado = transform_palver_export(df)
    assert list(resultado.columns) == IDEAL_COLUMN_ORDER
    assert resultado.loc[0, "Tier"] == 4.0
    assert resultado.loc[0, "Link"].startswith("https://clip.palver.com.br")


def test_transform_preserva_conteudo_nos_dois_idiomas():
    for linha in (_linha_exemplo(), _linha_exemplo_pt()):
        resultado = transform_palver_export(pd.DataFrame([linha]))
        assert resultado.loc[0, "Conteúdo"] == "Texto integral de exemplo"


def test_transform_traduz_tipo_de_midia_da_exportacao_em_ingles():
    df = pd.DataFrame([_linha_exemplo(Source="Radio"), _linha_exemplo(Source="News")])
    resultado = transform_palver_export(df)
    assert resultado["Tipo de mídia"].tolist() == ["Rádio", "Notícias"]


def test_erro_lista_colunas_do_idioma_mais_proximo():
    df = pd.DataFrame([_linha_exemplo_pt()]).drop(columns=["Tier do Veículo"])
    with pytest.raises(ValueError, match=r"\['Tier do Veículo'\]"):
        transform_palver_export(df)


def test_validate_input_columns_aceita_colunas_extras():
    df = pd.DataFrame([_linha_exemplo(**{"Coluna Extra Da Palver": "qualquer valor"})])
    validate_input_columns(df)