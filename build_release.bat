@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [2/4] Gerando executavel PyInstaller...
pyinstaller --noconfirm --onefile --windowed --name NumpadStreamDeck numpad_streamdeck.py

if not exist dist\NumpadStreamDeck.exe (
    echo ERRO: Executavel nao foi gerado em dist\NumpadStreamDeck.exe
    exit /b 1
)

where iscc >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [3/4] Inno Setup nao encontrado. O instalador .exe nao foi gerado.
    echo Instale o Inno Setup e rode este script novamente.
    echo Download: https://jrsoftware.org/isinfo.php
    exit /b 0
)

echo [3/4] Compilando instalador com Inno Setup...
iscc installer.iss

if not exist installer\NumpadStreamDeck_Setup.exe (
    echo ERRO: Instalador nao foi gerado em installer\NumpadStreamDeck_Setup.exe
    exit /b 1
)

echo [4/4] Build e instalador concluido.
echo Arquivo final: installer\NumpadStreamDeck_Setup.exe
endlocal
