"""
Classifica cada item do MODELO IDEAL (saída da fase 01) seguindo o guia de
classificação da Transparência Brasil, usando um modelo local servido pelo Ollama.

O guia está dividido em um arquivo por assunto (data/categorias/), e a
classificação roda em três etapas, cada uma com só a parte do guia que usa:

1. Área Temática 1 e Tema  — guia_areas.md
2. Projeto                 — guia_projetos.md (pulada para "Fora do escopo")
3. Relatório               — guia_relatorios.md + catalogo_relatorios.csv
                             (só para itens que mencionam a TB junto de
                             relatório, levantamento, estudo etc.)

Instruções menores ajudam o modelo local a seguir o guia: com tudo junto, ele
se guiava por palavras soltas. Cada etapa passa por todos os itens antes da
próxima, para o Ollama reaproveitar as instruções entre uma chamada e outra.

Uso:
    python src/classifica.py CAMINHO_DO_CSV_FASE01 [--saida CAMINHO]

Configuração por variáveis de ambiente:
    LLM_BASE_URL  endereço do Ollama (padrão: http://localhost:11434)
    LLM_MODEL     nome do modelo carregado no Ollama (obrigatório)
    LLM_NUM_CTX   janela de contexto em tokens (padrão: 16384)
"""

import argparse
import json
import os
import re
from pathlib import Path

import pandas as pd
import requests

RAIZ_PROJETO = Path(__file__).resolve().parents[3]
PASTA_CATEGORIAS = RAIZ_PROJETO / "data" / "categorias"
CAMINHO_SAIDA_PADRAO = Path(__file__).resolve().parents[1] / "outputs" / "classificado.csv"

FORA_DO_ESCOPO = "Fora do escopo"
RELATORIO_NAO_IDENTIFICADO = "Não foi possível identificar"
NIVEIS_CONFIANCA = ["Alta", "Média", "Baixa"]
LIMITE_CONTEUDO = 2000
SEM_CONTEUDO = "Sem título nem conteúdo: não enviado ao modelo."
COLUNAS_CLASSIFICACAO = ["Área Temática 1", "Tema", "Projeto", "Relatório", "Confiança (auto)"]
SEPARADOR_PROJETOS = "; "
ETAPAS = ["Área e tema", "Projeto", "Relatório"]

# A etapa de relatório só roda quando a notícia cita a TB e algum tipo de publicação.
MENCAO_TB = re.compile(r"transpar[êe]ncia brasil|\bTB\b", re.IGNORECASE)
MENCAO_PUBLICACAO = re.compile(r"relat[óo]rio|levantamento|estudo|an[áa]lise|pesquisa|boletim|nota t[ée]cnica", re.IGNORECASE)

# O Ollama descarta sem aviso o que passa da janela de contexto (com a janela
# padrão, lia só ~2.050 tokens das instruções). Por isso ela é definida em toda chamada.
NUM_CTX_PADRAO = 16384
CARACTERES_POR_TOKEN_MAXIMO = 5


def _secao_markdown(texto: str, secao: str, nivel_item: str) -> list[str]:
    """Títulos de nível `nivel_item` dentro da seção de nível 1 numerada `secao`."""
    itens, dentro = [], False
    for linha in texto.splitlines():
        if linha.startswith("# "):
            dentro = linha[2:].split(".")[0] == secao
        elif dentro and linha.startswith(nivel_item + " "):
            itens.append(linha[len(nivel_item) + 1:].strip())
    return itens


def carrega_areas(texto: str) -> dict[str, list[str]]:
    """
    Áreas (## 3.x) e temas de cada área (####) do guia de áreas.
    Uma área sem temas, como Institucional, usa o próprio nome como tema.
    """
    areas, area, dentro = {}, None, False
    for linha in texto.splitlines():
        if linha.startswith("# "):
            dentro = linha[2:].split(".")[0] == "3"
        elif dentro and linha.startswith("## "):
            area = re.sub(r"^\d+(\.\d+)*\.?\s*", "", linha[3:]).strip()
            areas[area] = []
        elif dentro and linha.startswith("#### "):
            areas[area].append(linha[5:].strip())
    return {area: temas or [area] for area, temas in areas.items()}


def carrega_guia(pasta: Path = PASTA_CATEGORIAS) -> dict:
    """Lê os três arquivos do guia e o catálogo, e extrai as opções válidas de resposta."""
    texto_areas = (pasta / "guia_areas.md").read_text(encoding="utf-8")
    texto_projetos = (pasta / "guia_projetos.md").read_text(encoding="utf-8")
    catalogo = pd.read_csv(pasta / "catalogo_relatorios.csv", encoding="utf-8", dtype=str).fillna("")
    return {
        "texto_areas": texto_areas,
        "texto_projetos": texto_projetos,
        "texto_relatorios": (pasta / "guia_relatorios.md").read_text(encoding="utf-8"),
        "temas": carrega_areas(texto_areas),
        "projetos": _secao_markdown(texto_projetos, "4", "###"),
        "relatorios": catalogo.sort_values("Data", ascending=False).to_dict("records"),
    }


def opcoes_relatorio(guia: dict) -> list[str]:
    """Respostas válidas para o campo Relatório: vazio, não identificado ou um título do catálogo."""
    return ["", RELATORIO_NAO_IDENTIFICADO] + [relatorio["Título"] for relatorio in guia["relatorios"]]


def prompt_area(guia: dict) -> str:
    temas_por_area = "\n".join(f"- {area}: {', '.join(temas)}" for area, temas in guia["temas"].items())
    return (
        "Você classifica notícias do clipping da Transparência Brasil seguindo o guia abaixo.\n\n"
        + guia["texto_areas"]
        + "\n\n# Instruções desta etapa\n\n"
        "Preencha apenas a Área temática 1 e o tema; não preencha as áreas temáticas 2 e 3.\n\n"
        "- area: a Área temática 1 (principal), ou \"Fora do escopo\" quando a notícia não tiver relação "
        "com nenhuma área da TB.\n"
        "- tema: um dos temas da área escolhida, conforme a lista abaixo. Com \"Fora do escopo\", deixe vazio.\n"
        "- confianca: Alta, Média ou Baixa.\n"
        "- justificativa: uma frase explicando a área principal.\n\n"
        "Temas de cada área:\n" + temas_por_area
    )


def prompt_projeto(guia: dict) -> str:
    return (
        "Você identifica projetos e iniciativas da Transparência Brasil relacionados a notícias do "
        "clipping, seguindo o guia abaixo.\n\n"
        + guia["texto_projetos"]
        + "\n\n# Instruções desta etapa\n\n"
        "- projetos: os projetos ou iniciativas da seção 4 relacionados ao assunto central da notícia. "
        "Lista vazia quando a relação for apenas genérica ou tangencial, ou quando não houver.\n\n"
        "Opções: " + ", ".join(guia["projetos"])
    )


def prompt_relatorio(guia: dict) -> str:
    catalogo = "\n".join(
        f"- {relatorio['Data']} | {relatorio['Área temática']} | {relatorio['Título']}"
        for relatorio in guia["relatorios"]
    )
    return (
        "Você identifica relatórios da Transparência Brasil citados em notícias do clipping, "
        "seguindo o guia abaixo.\n\n"
        + guia["texto_relatorios"]
        + "\n\n# Instruções desta etapa\n\n"
        "- relatorio: o título exato de um relatório do catálogo abaixo quando a notícia o citar ou quando "
        "data, assunto e números permitirem identificá-lo com segurança; \""
        + RELATORIO_NAO_IDENTIFICADO
        + "\" quando a notícia indicar um relatório, estudo ou levantamento da TB que não dá para identificar "
        "(inclusive publicações fora do catálogo); vazio quando não houver indicação de relatório da TB.\n\n"
        "# Catálogo de relatórios da TB (data | área | título exato)\n\n" + catalogo
    )


def schema_area(guia: dict) -> dict:
    todos_temas = sorted({tema for temas in guia["temas"].values() for tema in temas})
    return {
        "type": "object",
        "properties": {
            "area": {"type": "string", "enum": list(guia["temas"]) + [FORA_DO_ESCOPO]},
            "tema": {"type": "string", "enum": todos_temas + [""]},
            "confianca": {"type": "string", "enum": NIVEIS_CONFIANCA},
            "justificativa": {"type": "string"},
        },
        "required": ["area", "tema", "confianca", "justificativa"],
        "additionalProperties": False,
    }


def schema_projeto(guia: dict) -> dict:
    return {
        "type": "object",
        "properties": {
            "projetos": {"type": "array", "items": {"type": "string", "enum": guia["projetos"]}, "uniqueItems": True},
        },
        "required": ["projetos"],
        "additionalProperties": False,
    }


def schema_relatorio(guia: dict) -> dict:
    return {
        "type": "object",
        "properties": {"relatorio": {"type": "string", "enum": opcoes_relatorio(guia)}},
        "required": ["relatorio"],
        "additionalProperties": False,
    }


def _texto(linha: pd.Series, coluna: str) -> str:
    """Valor textual da coluna, ou string vazia se ausente ou nulo."""
    valor = linha.get(coluna)
    return valor.strip() if isinstance(valor, str) else ""


def monta_mensagem_item(linha: pd.Series) -> str:
    """Texto enviado ao modelo para um item do clipping."""
    mensagem = (
        f"Título: {_texto(linha, 'Título') or '(sem título)'}\n"
        f"Veículo: {linha['Veículo']}\n"
        f"Tipo de mídia: {linha['Tipo de mídia']}"
    )
    conteudo = _texto(linha, "Conteúdo")
    if conteudo:
        # Corta textos longos para manter o modelo local rápido.
        mensagem += f"\nConteúdo: {conteudo[:LIMITE_CONTEUDO]}"
    return mensagem


def tem_conteudo(linha: pd.Series) -> bool:
    """Só vai ao modelo o item com título ou conteúdo (transcrição, no caso de rádio e TV)."""
    return bool(_texto(linha, "Título") or _texto(linha, "Conteúdo"))


def tem_indicio_de_relatorio(linha: pd.Series) -> bool:
    """A notícia cita a TB e algum tipo de publicação (relatório, levantamento, estudo...)."""
    texto = _texto(linha, "Título") + "\n" + _texto(linha, "Conteúdo")
    return bool(MENCAO_TB.search(texto) and MENCAO_PUBLICACAO.search(texto))


def cria_classificador(prompt_sistema: str, schema: dict, base_url: str, modelo: str, num_ctx: int = NUM_CTX_PADRAO):
    """
    Devolve uma função que recebe o texto de um item e retorna a resposta do
    modelo local no formato de `schema`.

    Usa a API nativa do Ollama (/api/chat), a única que aceita a janela de
    contexto por chamada. Se parte das instruções for cortada, a chamada
    falha em vez de gravar uma classificação feita sem o guia.
    """
    url = base_url.rstrip("/") + "/api/chat"

    def classificar(mensagem: str) -> dict:
        resposta = requests.post(
            url,
            json={
                "model": modelo,
                "stream": False,
                "format": schema,
                "options": {"temperature": 0, "num_ctx": num_ctx},
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": mensagem},
                ],
            },
            timeout=300,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        # Ao cortar, o Ollama descarta cerca de metade da janela, então o corte não aparece
        # como "tokens lidos = janela". Em português, cada token tem ~3,7 caracteres: ler
        # menos de 1 token a cada 5 caracteres enviados indica que parte do texto sumiu.
        tokens_minimos = (len(prompt_sistema) + len(mensagem)) / CARACTERES_POR_TOKEN_MAXIMO
        if dados.get("prompt_eval_count", tokens_minimos) < tokens_minimos:
            raise ValueError(
                f"As instruções não couberam na janela de contexto ({num_ctx} tokens) e foram cortadas "
                f"(o modelo leu {dados['prompt_eval_count']} tokens); aumente LLM_NUM_CTX."
            )
        return json.loads(dados["message"]["content"])

    return classificar


def cria_classificadores(guia: dict, base_url: str, modelo: str, num_ctx: int = NUM_CTX_PADRAO) -> dict:
    """Um classificador por etapa, cada um com a sua parte do guia."""
    return {
        "area": cria_classificador(prompt_area(guia), schema_area(guia), base_url, modelo, num_ctx),
        "projeto": cria_classificador(prompt_projeto(guia), schema_projeto(guia), base_url, modelo, num_ctx),
        "relatorio": cria_classificador(prompt_relatorio(guia), schema_relatorio(guia), base_url, modelo, num_ctx),
    }


def valida_area(resposta: dict, guia: dict) -> dict:
    """Área ou confiança inválida descarta a resposta; tema fora da área escolhida fica em branco."""
    area = resposta.get("area")
    confianca = resposta.get("confianca")
    justificativa = resposta.get("justificativa", "")
    if area not in list(guia["temas"]) + [FORA_DO_ESCOPO] or confianca not in NIVEIS_CONFIANCA:
        return {"area": None, "justificativa": f"Resposta inválida do modelo: {resposta}"}
    if area == FORA_DO_ESCOPO:
        return {"area": area, "tema": "", "confianca": confianca, "justificativa": justificativa}
    tema = resposta.get("tema")
    if tema not in guia["temas"][area]:
        justificativa += f" [Tema descartado: \"{tema}\" não pertence a {area}.]"
        tema = None
    return {"area": area, "tema": tema, "confianca": confianca, "justificativa": justificativa}


def valida_projetos(resposta: dict, guia: dict) -> list[str]:
    """Projetos do guia, sem repetição; os inexistentes são removidos."""
    projetos = []
    for projeto in resposta.get("projetos") or []:
        if projeto in guia["projetos"] and projeto not in projetos:
            projetos.append(projeto)
    return projetos


def valida_relatorio(resposta: dict, guia: dict) -> tuple[str, str]:
    """Devolve (relatório, observação); título fora do catálogo vira vazio com observação."""
    relatorio = resposta.get("relatorio")
    if relatorio in opcoes_relatorio(guia):
        return relatorio, ""
    return "", f" [Relatório descartado: \"{relatorio}\" não está no catálogo.]"


def classifica_df(
    df: pd.DataFrame, guia: dict, classificadores: dict, ao_progredir=None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Preenche Área Temática 1, Tema, Projeto, Relatório e Confiança (auto) no
    MODELO IDEAL, em três etapas. Devolve o dataframe classificado e um
    dataframe de auditoria com a justificativa de cada item.
    `ao_progredir(etapa, feitos, total)` é chamado antes de cada chamada ao modelo.
    """
    df = df.copy()
    for coluna in COLUNAS_CLASSIFICACAO:
        df[coluna] = df[coluna].astype("object") if coluna in df.columns else None
    justificativas = {indice: SEM_CONTEUDO for indice in df.index}

    def chama(etapa: str, indice, linha) -> dict | None:
        try:
            return classificadores[etapa](monta_mensagem_item(linha))
        except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError) as erro:
            justificativas[indice] = (justificativas.get(indice) or "") + f" [Erro na etapa {etapa}: {erro}]"
            return None

    def avisa(etapa: str, feitos: int, total: int) -> None:
        if ao_progredir is not None:
            ao_progredir(etapa, feitos, total)

    # Etapa 1: área e tema de todos os itens com título ou conteúdo.
    fila = [(i, linha) for i, linha in df.iterrows() if tem_conteudo(linha)]
    for feitos, (indice, linha) in enumerate(fila, start=1):
        avisa(ETAPAS[0], feitos, len(fila))
        justificativas[indice] = ""
        resposta = chama("area", indice, linha)
        if resposta is None:
            continue
        resposta = valida_area(resposta, guia)
        justificativas[indice] += resposta["justificativa"]
        if resposta["area"] is not None:
            df.at[indice, "Área Temática 1"] = resposta["area"]
            df.at[indice, "Tema"] = resposta["tema"]
            df.at[indice, "Confiança (auto)"] = resposta["confianca"]

    no_escopo = [
        (i, linha) for i, linha in fila
        if df.at[i, "Área Temática 1"] not in (None, FORA_DO_ESCOPO) and pd.notna(df.at[i, "Área Temática 1"])
    ]

    # Etapa 2: projetos, só para itens classificados dentro do escopo.
    for feitos, (indice, linha) in enumerate(no_escopo, start=1):
        avisa(ETAPAS[1], feitos, len(no_escopo))
        resposta = chama("projeto", indice, linha)
        if resposta is not None:
            df.at[indice, "Projeto"] = SEPARADOR_PROJETOS.join(valida_projetos(resposta, guia)) or None

    # Etapa 3: relatório, só quando a notícia cita a TB junto de alguma publicação.
    com_indicio = [(i, linha) for i, linha in no_escopo if tem_indicio_de_relatorio(linha)]
    for feitos, (indice, linha) in enumerate(com_indicio, start=1):
        avisa(ETAPAS[2], feitos, len(com_indicio))
        resposta = chama("relatorio", indice, linha)
        if resposta is not None:
            relatorio, observacao = valida_relatorio(resposta, guia)
            df.at[indice, "Relatório"] = relatorio or None
            justificativas[indice] += observacao

    auditoria = pd.DataFrame({
        "ID": df["ID"],
        "Área Temática 1": df["Área Temática 1"],
        "Justificativa": [justificativas[i].strip() for i in df.index],
    })
    return df, auditoria


def main() -> None:
    parser = argparse.ArgumentParser(description="Classifica o CSV da fase 01 seguindo o guia de classificação.")
    parser.add_argument("entrada", type=Path, help="CSV no MODELO IDEAL gerado pela fase 01")
    parser.add_argument("--saida", type=Path, default=CAMINHO_SAIDA_PADRAO)
    args = parser.parse_args()

    modelo = os.environ.get("LLM_MODEL")
    if not modelo:
        raise SystemExit("Defina LLM_MODEL com o nome do modelo carregado no Ollama.")
    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434")
    num_ctx = int(os.environ.get("LLM_NUM_CTX", NUM_CTX_PADRAO))

    guia = carrega_guia()
    classificadores = cria_classificadores(guia, base_url, modelo, num_ctx)

    df = pd.read_csv(args.entrada, encoding="utf-8")
    classificado, auditoria = classifica_df(df, guia, classificadores)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    classificado.to_csv(args.saida, index=False, encoding="utf-8")
    auditoria.to_csv(args.saida.with_name(args.saida.stem + "_auditoria.csv"), index=False, encoding="utf-8")

    sem_conteudo = (auditoria["Justificativa"] == SEM_CONTEUDO).sum()
    print(
        f"{len(df)} itens | {classificado['Área Temática 1'].notna().sum()} classificados | "
        f"{sem_conteudo} sem título nem conteúdo"
    )
    print(classificado["Área Temática 1"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
