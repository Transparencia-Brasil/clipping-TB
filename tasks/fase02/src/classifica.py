"""
Classifica cada item do MODELO IDEAL (saída da fase 01) em um Tema do
esquema de categorias da Transparência Brasil, usando um modelo local
servido por uma instância Docker com API compatível com OpenAI
(Ollama, vLLM, llama.cpp server etc).

O modelo escolhe apenas o Tema; a Área Temática é derivada do esquema,
o que garante que as duas colunas sejam sempre consistentes.

Uso:
    python src/classifica.py CAMINHO_DO_CSV_FASE01 [--saida CAMINHO]

Configuração por variáveis de ambiente:
    LLM_BASE_URL  endereço da API (padrão: http://localhost:11434/v1)
    LLM_MODEL     nome do modelo carregado na instância (obrigatório)
"""

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import requests

RAIZ_PROJETO = Path(__file__).resolve().parents[3]
CAMINHO_ESQUEMA = RAIZ_PROJETO / "data" / "categorias" / "esquema_categorias.csv"
CAMINHO_SAIDA_PADRAO = Path(__file__).resolve().parents[1] / "outputs" / "classificado.csv"

# Nomes curtos do esquema para os nomes oficiais usados no site.
NOMES_AREAS = {
    "Acc do estado": "Accountability do Estado",
    "Gov e tech": "Governança e Tecnologia",
}

FORA_DO_ESCOPO = "Fora do escopo"
NIVEIS_CONFIANCA = ["Alta", "Média", "Baixa"]
LIMITE_CONTEUDO = 2000
SEM_CONTEUDO = "Sem título nem conteúdo: não enviado ao modelo."

REGRAS_DESEMPATE = """\
- Qualquer menção a emendas parlamentares vai para "Emendas parlamentares", mesmo que envolva orçamento, STF ou Legislativo.
- "Justiça" é só conduta de ministros e conflitos de interesse; remunerações, benefícios e gastos do sistema de Justiça vão para "DadosJusbr".
- Negar acesso a informação é "LAI", não "Sigilo de informações".
- Contratações de medicamentos vão para "Medicamentos Transparentes"; demais contratações para "Contratos, licitações e compras públicas".
- "Institucional" só quando a notícia fala da Transparência Brasil como instituição; se ela apenas é citada como fonte, classifique pelo assunto.
- Se o assunto não se encaixa em nenhum tema, responda "Fora do escopo"."""


def carrega_esquema(caminho: Path = CAMINHO_ESQUEMA) -> pd.DataFrame:
    """Lê o esquema de categorias e padroniza os nomes das áreas."""
    esquema = pd.read_csv(caminho, encoding="utf-8").fillna("")
    esquema["Área Temática"] = esquema["Área Temática"].replace(NOMES_AREAS)
    return esquema


def monta_prompt_sistema(esquema: pd.DataFrame) -> str:
    """Monta as instruções do modelo com todos os temas, explicações e exemplos."""
    blocos = []
    for _, linha in esquema.iterrows():
        bloco = f"### {linha['Tema']} (área: {linha['Área Temática']})\n{linha['Explicação']}"
        if linha["Exemplos"]:
            bloco += f"\nExemplos: {linha['Exemplos']}"
        blocos.append(bloco)

    return (
        "Você classifica notícias do clipping da Transparência Brasil em exatamente um tema.\n\n"
        "## Temas\n\n" + "\n\n".join(blocos) + "\n\n"
        "## Regras de desempate\n" + REGRAS_DESEMPATE + "\n\n"
        "Responda apenas com o JSON pedido: o tema, a confiança (Alta, Média ou Baixa) "
        "e uma justificativa de uma frase."
    )


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


def schema_resposta(temas: list[str]) -> dict:
    """JSON schema que restringe a resposta do modelo aos temas válidos."""
    return {
        "type": "object",
        "properties": {
            "tema": {"type": "string", "enum": temas + [FORA_DO_ESCOPO]},
            "confianca": {"type": "string", "enum": NIVEIS_CONFIANCA},
            "justificativa": {"type": "string"},
        },
        "required": ["tema", "confianca", "justificativa"],
        "additionalProperties": False,
    }


def cria_classificador(prompt_sistema: str, temas: list[str], base_url: str, modelo: str):
    """
    Devolve uma função que recebe o texto de um item e retorna o dicionário
    {tema, confianca, justificativa} vindo do modelo local.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    formato = {
        "type": "json_schema",
        "json_schema": {"name": "classificacao", "strict": True, "schema": schema_resposta(temas)},
    }

    def classificar(mensagem: str) -> dict:
        resposta = requests.post(
            url,
            json={
                "model": modelo,
                "temperature": 0,
                "response_format": formato,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": mensagem},
                ],
            },
            timeout=300,
        )
        resposta.raise_for_status()
        conteudo = resposta.json()["choices"][0]["message"]["content"]
        return json.loads(conteudo)

    return classificar


def valida_resposta(resposta: dict, temas: list[str]) -> dict:
    """Descarta respostas fora do esquema em vez de gravar um tema inventado."""
    tema = resposta.get("tema")
    confianca = resposta.get("confianca")
    if tema not in temas + [FORA_DO_ESCOPO] or confianca not in NIVEIS_CONFIANCA:
        return {"tema": None, "confianca": None, "justificativa": f"Resposta inválida do modelo: {resposta}"}
    return resposta


def classifica_df(
    df: pd.DataFrame, esquema: pd.DataFrame, classificar, ao_progredir=None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Preenche Área Temática, Tema e Confiança (auto) no MODELO IDEAL.
    Devolve o dataframe classificado e um dataframe de auditoria com a
    justificativa de cada item. `ao_progredir(feitos, total)` é chamado
    após cada item, para barras de progresso.
    """
    temas = esquema["Tema"].tolist()
    area_por_tema = dict(zip(esquema["Tema"], esquema["Área Temática"]))

    df = df.copy()
    for coluna in ["Área Temática", "Tema", "Confiança (auto)"]:
        df[coluna] = df[coluna].astype("object")

    auditoria = []
    for posicao, (indice, linha) in enumerate(df.iterrows(), start=1):
        if ao_progredir is not None:
            ao_progredir(posicao, len(df))

        if not tem_conteudo(linha):
            auditoria.append({"ID": linha["ID"], "Tema": None, "Justificativa": SEM_CONTEUDO})
            continue

        try:
            resposta = valida_resposta(classificar(monta_mensagem_item(linha)), temas)
        except (requests.RequestException, json.JSONDecodeError, KeyError) as erro:
            resposta = {"tema": None, "confianca": None, "justificativa": f"Erro na chamada ao modelo: {erro}"}

        tema = resposta["tema"]
        if tema is not None:
            df.at[indice, "Tema"] = tema
            df.at[indice, "Área Temática"] = area_por_tema.get(tema, FORA_DO_ESCOPO)
            df.at[indice, "Confiança (auto)"] = resposta["confianca"]
        auditoria.append({"ID": linha["ID"], "Tema": tema, "Justificativa": resposta["justificativa"]})

    return df, pd.DataFrame(auditoria)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classifica o CSV da fase 01 por Tema e Área Temática.")
    parser.add_argument("entrada", type=Path, help="CSV no MODELO IDEAL gerado pela fase 01")
    parser.add_argument("--saida", type=Path, default=CAMINHO_SAIDA_PADRAO)
    args = parser.parse_args()

    modelo = os.environ.get("LLM_MODEL")
    if not modelo:
        raise SystemExit("Defina LLM_MODEL com o nome do modelo carregado na instância Docker.")
    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")

    esquema = carrega_esquema()
    classificar = cria_classificador(monta_prompt_sistema(esquema), esquema["Tema"].tolist(), base_url, modelo)

    df = pd.read_csv(args.entrada, encoding="utf-8")
    classificado, auditoria = classifica_df(df, esquema, classificar)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    classificado.to_csv(args.saida, index=False, encoding="utf-8")
    auditoria.to_csv(args.saida.with_name(args.saida.stem + "_auditoria.csv"), index=False, encoding="utf-8")

    sem_conteudo = (auditoria["Justificativa"] == SEM_CONTEUDO).sum()
    print(f"{len(df)} itens | {classificado['Tema'].notna().sum()} classificados | {sem_conteudo} sem título nem conteúdo")
    print(classificado["Área Temática"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
