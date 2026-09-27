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

# Só instala quando o requirements.txt mudou desde a última instalação
# bem-sucedida. A cópia só é gravada depois que o pip termina sem erro,
# então uma instalação interrompida é retomada na próxima execução.
if ! cmp -s setup/requirements.txt .venv/requirements.instalado; then
    echo
    echo "Instalando dependências. Na primeira execução isso pode levar 1 a 2 minutos..."
    echo
    python -m pip install --disable-pip-version-check -r setup/requirements.txt || falha
    cp setup/requirements.txt .venv/requirements.instalado
fi

echo
echo "Abrindo o app no navegador. Para encerrar, feche esta janela."
python -m streamlit run app.py || falha
