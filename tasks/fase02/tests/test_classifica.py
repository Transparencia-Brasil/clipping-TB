import pandas as pd
import pytest

from src import classifica
from src.classifica import (
    FORA_DO_ESCOPO,
    LIMITE_CONTEUDO,
    RELATORIO_NAO_IDENTIFICADO,
    SEM_CONTEUDO,
    carrega_guia,
    classifica_df,
    cria_classificador,
    prompt_area,
    prompt_projeto,
    prompt_relatorio,
    schema_area,
)

GUIA = carrega_guia()
TITULO_RELATORIO = "Emendas de bancada \"paralelas\" driblaram decisões do STF"


def _linha_exemplo(**overrides):
    linha = {
        "ID": "abc123",
        "Data": "2026-09-22",
        "Título": "Dino deixa julgamento sobre emendas para depois das eleições",
        "Veículo": "ND Mais",
        "Tipo de mídia": "Notícias",
        "Tier": 2.0,
        "Área Temática 1": None,
        "Tema": None,
        "Projeto": None,
        "Relatório": None,
        "Confiança (auto)": None,
        "Visualizações": None,
        "Impressões": 8982.0,
        "Link": "https://clip.palver.com.br/shared/news/abc123",
        "Conteúdo": "Levantamento da Transparência Brasil mostra emendas de bancada paralelas.",
    }
    linha.update(overrides)
    return linha


def _classificadores(area=None, projetos=None, relatorio=""):
    """Classificadores falsos por etapa, que registram as mensagens recebidas."""
    area = area or {
        "area": "Qualidade do Gasto Público",
        "tema": "Emendas parlamentares",
        "confianca": "Alta",
        "justificativa": "Trata da execução de emendas.",
    }
    projetos = ["Emendas parlamentares"] if projetos is None else projetos
    chamadas = {"area": [], "projeto": [], "relatorio": []}

    def falso(etapa, resposta):
        def classificar(mensagem):
            chamadas[etapa].append(mensagem)
            return resposta
        return classificar

    classificadores = {
        "area": falso("area", area),
        "projeto": falso("projeto", {"projetos": projetos}),
        "relatorio": falso("relatorio", {"relatorio": relatorio}),
    }
    return classificadores, chamadas


def _classifica(linha=None, **respostas):
    classificadores, chamadas = _classificadores(**respostas)
    df = pd.DataFrame([_linha_exemplo(**(linha or {}))])
    resultado, auditoria = classifica_df(df, GUIA, classificadores)
    return resultado.loc[0], auditoria.loc[0], chamadas


def _area(**overrides):
    area = {"area": "Qualidade do Gasto Público", "tema": "Emendas parlamentares", "confianca": "Alta", "justificativa": "x"}
    area.update(overrides)
    return area


# Guia dividido


def test_guia_de_areas_traz_as_seis_areas_com_seus_temas():
    assert list(GUIA["temas"]) == [
        "Accountability do Estado",
        "Transparência Partidária",
        "Qualidade do Gasto Público",
        "Acesso a Informação",
        "Governança e Tecnologia",
        "Institucional",
    ]
    assert "Emendas parlamentares" in GUIA["temas"]["Qualidade do Gasto Público"]
    assert GUIA["temas"]["Institucional"] == ["Institucional"]


def test_guia_de_projetos_traz_projetos_e_iniciativas():
    assert len(GUIA["projetos"]) == 12
    assert "Ninguém Acima da Lei" in GUIA["projetos"]


def test_catalogo_traz_os_relatorios_do_mais_recente_ao_mais_antigo():
    assert len(GUIA["relatorios"]) == 29
    assert GUIA["relatorios"][0]["Data"] >= GUIA["relatorios"][-1]["Data"]


def test_cada_etapa_recebe_so_a_sua_parte_do_guia():
    area, projeto, relatorio = prompt_area(GUIA), prompt_projeto(GUIA), prompt_relatorio(GUIA)
    assert GUIA["texto_areas"] in area and GUIA["texto_projetos"] not in area
    assert GUIA["texto_projetos"] in projeto and GUIA["texto_areas"] not in projeto
    assert GUIA["texto_relatorios"] in relatorio and TITULO_RELATORIO in relatorio
    assert TITULO_RELATORIO not in area and TITULO_RELATORIO not in projeto


def test_instrucoes_por_etapa_ficam_bem_menores_que_o_guia_inteiro():
    for prompt in (prompt_area(GUIA), prompt_projeto(GUIA), prompt_relatorio(GUIA)):
        assert len(prompt) < 16000


# Classificação em três etapas


def test_preenche_todas_as_colunas():
    linha, auditoria, _ = _classifica(projetos=["Emendas parlamentares", "DadosJusBr"], relatorio=TITULO_RELATORIO)
    assert linha["Área Temática 1"] == "Qualidade do Gasto Público"
    assert linha["Tema"] == "Emendas parlamentares"
    assert linha["Projeto"] == "Emendas parlamentares; DadosJusBr"
    assert linha["Relatório"] == TITULO_RELATORIO
    assert linha["Confiança (auto)"] == "Alta"
    assert auditoria["Justificativa"] == "Trata da execução de emendas."


def test_relatorio_nao_identificado_e_gravado():
    linha, _, _ = _classifica(relatorio=RELATORIO_NAO_IDENTIFICADO)
    assert linha["Relatório"] == RELATORIO_NAO_IDENTIFICADO


def test_relatorio_fora_do_catalogo_e_descartado():
    linha, auditoria, _ = _classifica(relatorio="Relatório inventado sobre emendas")
    assert pd.isna(linha["Relatório"])
    assert "Relatório descartado" in auditoria["Justificativa"]


def test_sem_indicio_de_relatorio_a_etapa_de_relatorio_nao_roda():
    linha, _, chamadas = _classifica(linha={"Conteúdo": "O STF adiou o julgamento sobre emendas."}, relatorio=TITULO_RELATORIO)
    assert chamadas["relatorio"] == []
    assert pd.isna(linha["Relatório"])


def test_fora_do_escopo_pula_projeto_e_relatorio():
    linha, _, chamadas = _classifica(area=_area(area=FORA_DO_ESCOPO, tema="LAI"))
    assert linha["Área Temática 1"] == FORA_DO_ESCOPO
    assert linha["Tema"] == ""
    assert chamadas["projeto"] == [] and chamadas["relatorio"] == []
    assert pd.isna(linha["Projeto"])


def test_tema_de_outra_area_fica_em_branco_e_area_e_mantida():
    linha, auditoria, _ = _classifica(area=_area(tema="LAI"))
    assert linha["Área Temática 1"] == "Qualidade do Gasto Público"
    assert pd.isna(linha["Tema"])
    assert "Tema descartado" in auditoria["Justificativa"]


def test_area_inventada_descarta_a_resposta_e_pula_as_outras_etapas():
    linha, auditoria, chamadas = _classifica(area=_area(area="Área que não existe"))
    assert pd.isna(linha["Área Temática 1"])
    assert "inválida" in auditoria["Justificativa"]
    assert chamadas["projeto"] == []


def test_projeto_inexistente_e_descartado():
    linha, _, _ = _classifica(projetos=["Projeto Inventado", "Emendas parlamentares"])
    assert linha["Projeto"] == "Emendas parlamentares"


def test_erro_numa_etapa_fica_na_auditoria_sem_perder_as_outras():
    classificadores, _ = _classificadores()

    def falha(mensagem):
        raise ValueError("Ollama fora do ar")

    classificadores["projeto"] = falha
    resultado, auditoria = classifica_df(pd.DataFrame([_linha_exemplo()]), GUIA, classificadores)
    assert resultado.loc[0, "Área Temática 1"] == "Qualidade do Gasto Público"
    assert "Erro na etapa projeto" in auditoria.loc[0, "Justificativa"]


def test_cada_etapa_passa_por_todos_os_itens_antes_da_proxima():
    ordem = []
    classificadores, _ = _classificadores()
    for etapa in ("area", "projeto"):
        original = classificadores[etapa]
        classificadores[etapa] = lambda mensagem, etapa=etapa, original=original: ordem.append(etapa) or original(mensagem)
    df = pd.DataFrame([_linha_exemplo(ID="a"), _linha_exemplo(ID="b")])
    classifica_df(df, GUIA, classificadores)
    assert ordem[:4] == ["area", "area", "projeto", "projeto"]


def test_item_sem_titulo_nem_conteudo_nao_vai_ao_modelo():
    linha, auditoria, chamadas = _classifica(linha={"Título": None, "Conteúdo": None, "Tipo de mídia": "Rádio"})
    assert chamadas["area"] == []
    assert pd.isna(linha["Área Temática 1"])
    assert auditoria["Justificativa"] == SEM_CONTEUDO


def test_item_sem_titulo_com_conteudo_vai_ao_modelo_com_texto_cortado():
    _, _, chamadas = _classifica(linha={"Título": None, "Conteúdo": "pedido negado " * 500, "Tipo de mídia": "Rádio"})
    assert "(sem título)" in chamadas["area"][0]
    assert len(chamadas["area"][0]) < LIMITE_CONTEUDO + 200


def test_arquivo_sem_colunas_de_classificacao_ainda_funciona():
    df = pd.DataFrame([_linha_exemplo()]).drop(columns=["Área Temática 1", "Projeto", "Conteúdo"])
    classificadores, _ = _classificadores()
    resultado, _ = classifica_df(df, GUIA, classificadores)
    assert resultado.loc[0, "Área Temática 1"] == "Qualidade do Gasto Público"


# Chamada ao Ollama


class _RespostaFalsa:
    def __init__(self, dados):
        self._dados = dados

    def raise_for_status(self):
        pass

    def json(self):
        return self._dados


def test_classificador_define_janela_de_contexto_e_formato(monkeypatch):
    enviado = {}

    def post_falso(url, json, timeout):
        enviado.update(url=url, corpo=json)
        return _RespostaFalsa({"message": {"content": '{"area": "Institucional"}'}, "prompt_eval_count": 9000})

    monkeypatch.setattr(classifica.requests, "post", post_falso)
    classificar = cria_classificador("instruções", schema_area(GUIA), "http://localhost:11434/", "llama3.1:8b", 16384)
    assert classificar("item") == {"area": "Institucional"}
    assert enviado["url"] == "http://localhost:11434/api/chat"
    assert enviado["corpo"]["options"] == {"temperature": 0, "num_ctx": 16384}
    assert "area" in enviado["corpo"]["format"]["properties"]


def test_classificador_falha_quando_as_instrucoes_sao_cortadas(monkeypatch):
    # Com janela de 4.096, o Ollama leu só ~2.050 tokens de instruções bem maiores.
    def post_falso(url, json, timeout):
        return _RespostaFalsa({"message": {"content": "{}"}, "prompt_eval_count": 2050})

    monkeypatch.setattr(classifica.requests, "post", post_falso)
    classificar = cria_classificador(prompt_area(GUIA), schema_area(GUIA), "http://localhost:11434", "llama3.1:8b", 4096)
    with pytest.raises(ValueError, match="janela de contexto"):
        classificar("item")
