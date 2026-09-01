Numpad Stream Deck

Estrutura do projeto:
- numpad_streamdeck.py
- requirements.txt
- build_release.bat
- installer.iss

Requisitos:
- Python 3.10+ no Windows
- pip
- PyInstaller
- Inno Setup

Gerar o executavel:
1. Abra um terminal no diretorio do projeto.
2. Execute:
   build_release.bat
3. O arquivo .exe aparecerah na pasta dist/

Gerar instalador:
1. Instale o Inno Setup no Windows.
2. Abra o terminal no diretorio do projeto.
3. Execute:
   build_release.bat
4. O processo gera o executavel e, se o Inno Setup estiver instalado, cria o arquivo de instalacao final em:
   installer\NumpadStreamDeck_Setup.exe

Importante:
- O usuario baixa apenas um arquivo .exe de instalacao.
- Nao e necessario fornecer .zip para ele.
- O instalador cria o programa, atalho e desinstalador no Windows.
- O programa salva presets em %APPDATA%\NumpadStreamDeck\numpad_presets.json
- O atalho global para ativar/desativar e CTRL + ALT + F12
- Para distribuicao real, e recomendavel assinar digitalmente o executavel.
