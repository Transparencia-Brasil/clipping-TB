import pandas as pd

from src.classifica import (
    FORA_DO_ESCOPO,
    LIMITE_CONTEUDO,
    SEM_CONTEUDO,
    carrega_esquema,
    classifica_df,
    monta_prompt_sistema,
)


def _linha_exemplo(**overrides):
    linha = {
        "ID": "abc123",
        "Data": "2026-09-22",
        "Título": "Dino deixa julgamento sobre emendas para depois das eleições",
        "Veículo": "ND Mais",
        "Tipo de mídia": "Notícias",
        "Tier": 2.0,
        "Área Temática": None,
        "Tema": None,
        "Projeto": None,
        "Relatório": None,
        "Confiança (auto)": None,
        "Visualizações": None,
        "Impressões": 8982.0,
        "Link": "https://clip.palver.com.br/shared/news/abc123",
        "Conteúdo": "O ministro Flávio Dino adiou o julgamento sobre as emendas parlamentares.",
    }
    linha.update(overrides)
    return linha


def _classificador_fixo(resposta):
    chamadas = []

    def classificar(mensagem):
        chamadas.append(mensagem)
        return resposta

    return classificar, chamadas


def test_esquema_usa_nomes_oficiais_das_areas():
    areas = set(carrega_esquema()["Área Temática"])
    assert "Accountability do Estado" in areas
    assert "Governança e Tecnologia" in areas
    assert "Acc do estado" not in areas


def test_prompt_contem_todos_os_temas():
    esquema = carrega_esquema()
    prompt = monta_prompt_sistema(esquema)
    for tema in esquema["Tema"]:
        assert tema in prompt


def test_area_e_derivada_do_tema():
    classificar, _ = _classificador_fixo(
        {"tema": "Emendas parlamentares", "confianca": "Alta", "justificativa": "Fala de emendas."}
    )
    resultado, _ = classifica_df(pd.DataFrame([_linha_exemplo()]), carrega_esquema(), classificar)
    assert resultado.loc[0, "Tema"] == "Emendas parlamentares"
    assert resultado.loc[0, "Área Temática"] == "Qualidade do gasto público"
    assert resultado.loc[0, "Confiança (auto)"] == "Alta"


def test_item_sem_titulo_nem_conteudo_nao_vai_ao_modelo():
    classificar, chamadas = _classificador_fixo(
        {"tema": "LAI", "confianca": "Alta", "justificativa": "x"}
    )
    df = pd.DataFrame([_linha_exemplo(**{"Título": None, "Conteúdo": None, "Tipo de mídia": "Rádio"})])
    resultado, auditoria = classifica_df(df, carrega_esquema(), classificar)
    assert chamadas == []
    assert pd.isna(resultado.loc[0, "Tema"])
    assert auditoria.loc[0, "Justificativa"] == SEM_CONTEUDO


def test_item_sem_titulo_com_conteudo_vai_ao_modelo_com_texto_cortado():
    classificar, chamadas = _classificador_fixo(
        {"tema": "LAI", "confianca": "Média", "justificativa": "Fala de pedidos de acesso."}
    )
    transcricao = "pedido de acesso negado " * 500
    df = pd.DataFrame([_linha_exemplo(**{"Título": None, "Conteúdo": transcricao, "Tipo de mídia": "Rádio"})])
    resultado, _ = classifica_df(df, carrega_esquema(), classificar)
    assert len(chamadas) == 1
    assert "(sem título)" in chamadas[0]
    assert "Conteúdo: pedido de acesso negado" in chamadas[0]
    assert len(chamadas[0]) < LIMITE_CONTEUDO + 200
    assert resultado.loc[0, "Tema"] == "LAI"


def test_arquivo_antigo_sem_coluna_conteudo_ainda_funciona():
    classificar, chamadas = _classificador_fixo(
        {"tema": "Emendas parlamentares", "confianca": "Alta", "justificativa": "x"}
    )
    df = pd.DataFrame([_linha_exemplo()]).drop(columns=["Conteúdo"])
    resultado, _ = classifica_df(df, carrega_esquema(), classificar)
    assert "Conteúdo:" not in chamadas[0]
    assert resultado.loc[0, "Tema"] == "Emendas parlamentares"


def test_tema_inventado_pelo_modelo_e_descartado():
    classificar, _ = _classificador_fixo(
        {"tema": "Tema que não existe", "confianca": "Alta", "justificativa": "x"}
    )
    resultado, auditoria = classifica_df(pd.DataFrame([_linha_exemplo()]), carrega_esquema(), classificar)
    assert pd.isna(resultado.loc[0, "Tema"])
    assert "inválida" in auditoria.loc[0, "Justificativa"]


def test_fora_do_escopo_e_aceito():
    classificar, _ = _classificador_fixo(
        {"tema": FORA_DO_ESCOPO, "confianca": "Média", "justificativa": "Política externa."}
    )
    resultado, _ = classifica_df(pd.DataFrame([_linha_exemplo()]), carrega_esquema(), classificar)
    assert resultado.loc[0, "Tema"] == FORA_DO_ESCOPO
    assert resultado.loc[0, "Área Temática"] == FORA_DO_ESCOPO
