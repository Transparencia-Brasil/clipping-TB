@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado. Instale o Python 3 em https://www.python.org/downloads/
    echo marcando a opcao "Add python.exe to PATH" e rode este arquivo de novo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo Ambiente virtual nao encontrado. Criando...
    python -m venv .venv
    if errorlevel 1 goto erro
)

call .venv\Scripts\activate.bat

rem Roda sempre: e rapido quando tudo ja esta instalado e corrige
rem ambientes em que uma instalacao anterior falhou no meio.
echo Verificando dependencias...
python -m pip install -q --disable-pip-version-check -r setup\requirements.txt
if errorlevel 1 goto erro

python -m streamlit run app.py
if errorlevel 1 goto erro
exit /b 0

:erro
echo.
echo Ocorreu um erro. Leia a mensagem acima antes de fechar esta janela.
pause
exit /b 1
