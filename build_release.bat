@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [2/4] Compilando helper nativo...
if not exist cpp\raw_input_filter.exe (
    if "%VSCMD_VER%"=="" (
        echo ERRO: Visual Studio Developer Command Prompt nao detectado.
        echo Instale o Visual Studio 2022 com "Desktop development with C++" e rode este script em um terminal de desenvolvimento.
        exit /b 1
    )
    cl /EHsc /std:c++17 cpp\raw_input_filter.cpp /link user32.lib /OUT:cpp\raw_input_filter.exe
    if errorlevel 1 exit /b 1
)

echo [3/4] Gerando executavel PyInstaller...
pyinstaller --noconfirm --onefile --windowed --name NumpadStreamDeck numpad_streamdeck.py

if exist cpp\raw_input_filter.exe copy /Y cpp\raw_input_filter.exe dist\raw_input_filter.exe >nul

if not exist dist\NumpadStreamDeck.exe (
    echo ERRO: Executavel nao foi gerado em dist\NumpadStreamDeck.exe
    exit /b 1
)

if not exist VC_redist.x64.exe (
    echo [3/4] Baixando o Visual C++ Redistributable x64...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "(New-Object Net.WebClient).DownloadFile('https://aka.ms/vs/17/release/vc_redist.x64.exe','VC_redist.x64.exe')"
    if not exist VC_redist.x64.exe (
        echo ERRO: Nao foi possivel baixar o VC++ Redistributable.
        exit /b 1
    )
)

where iscc >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [4/4] Inno Setup nao encontrado. O instalador .exe nao foi gerado.
    echo Instale o Inno Setup e rode este script novamente.
    echo Download: https://jrsoftware.org/isinfo.php
    exit /b 0
)

echo [4/4] Compilando instalador com Inno Setup...
iscc installer.iss

if not exist installer\NumpadStreamDeck_Setup.exe (
    echo ERRO: Instalador nao foi gerado em installer\NumpadStreamDeck_Setup.exe
    exit /b 1
)

echo [5/5] Build e instalador concluido.
echo Arquivo final: installer\NumpadStreamDeck_Setup.exe
endlocal
