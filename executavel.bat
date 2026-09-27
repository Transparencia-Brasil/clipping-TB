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

rem So instala quando o requirements.txt mudou desde a ultima instalacao
rem bem-sucedida. A copia so e gravada depois que o pip termina sem erro,
rem entao uma instalacao interrompida e retomada na proxima execucao.
fc /b setup\requirements.txt .venv\requirements.instalado >nul 2>nul
if errorlevel 1 (
    echo.
    echo Instalando dependencias. Na primeira execucao isso pode levar 1 a 2 minutos...
    echo.
    python -m pip install --disable-pip-version-check -r setup\requirements.txt
    if errorlevel 1 goto erro
    copy /y setup\requirements.txt .venv\requirements.instalado >nul
)

echo.
echo Abrindo o app no navegador. Para encerrar, feche esta janela.
python -m streamlit run app.py
if errorlevel 1 goto erro
exit /b 0

:erro
echo.
echo Ocorreu um erro. Leia a mensagem acima antes de fechar esta janela.
pause
exit /b 1
