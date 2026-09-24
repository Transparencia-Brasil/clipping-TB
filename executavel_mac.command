#!/bin/bash

cd "$(dirname "$0")" || exit 1

falha() {
    echo
    echo "Ocorreu um erro. Leia a mensagem acima antes de fechar esta janela."
    read -r -p "Pressione Enter para fechar."
    exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 não encontrado. Instale em https://www.python.org/downloads/ e rode este arquivo de novo."
    falha
fi

if [ ! -f ".venv/bin/activate" ]; then
    echo "Ambiente virtual não encontrado. Criando..."
    python3 -m venv .venv || falha
fi

source .venv/bin/activate

# Roda sempre: é rápido quando tudo já está instalado e corrige
# ambientes em que uma instalação anterior falhou no meio.
echo "Verificando dependências..."
python -m pip install -q --disable-pip-version-check -r setup/requirements.txt || falha

python -m streamlit run app.py || falha
