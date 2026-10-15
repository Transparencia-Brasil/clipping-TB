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

rem Na primeira execucao, cria um atalho na area de trabalho com a logo da TB.
rem Se a pessoa apagar o atalho, ele e recriado na proxima execucao.
set "PASTA_APP=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$atalho = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Clipping TB.lnk';" ^
  "if (-not (Test-Path -LiteralPath $atalho)) {" ^
  "  $s = (New-Object -ComObject WScript.Shell).CreateShortcut($atalho);" ^
  "  $s.TargetPath = Join-Path $env:PASTA_APP 'executavel.bat';" ^
  "  $s.WorkingDirectory = $env:PASTA_APP;" ^
  "  $s.IconLocation = (Join-Path $env:PASTA_APP 'assets\logo_tb.ico') + ',0';" ^
  "  $s.Description = 'Abre o app de clipping da Transparencia Brasil';" ^
  "  $s.Save();" ^
  "  Write-Host 'Atalho \"Clipping TB\" criado na area de trabalho.'" ^
  "}" 2>nul

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
