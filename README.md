# Numpad Stream Deck

Um aplicativo Windows para transformar seu teclado numérico em um stream deck customizável com atalhos personalizados, presets e suporte a tray icon.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.14+-blue)

## 🚀 Download Rápido

### ⬇️ Opção 1: Installer (Recomendado)
Clique em [**Releases**](https://github.com/NicollasCS/numpad-streamdeck/releases) e baixe `NumpadStreamDeck_Setup.exe`

Após baixar:
1. Execute o instalador
2. Selecione as opções desejadas
3. Pronto! Abre automaticamente

### ⬇️ Opção 2: Executável Direto
Se preferir sem instalação:
- Baixe `NumpadStreamDeck.exe` em [Releases](https://github.com/NicollasCS/numpad-streamdeck/releases)
- Execute e pronto!

---

## ✨ Recursos

- ✅ **Layout Numpad Customizável** - Configure cada tecla com ações personalizadas
- ✅ **Presets** - Salve múltiplas configurações e alterne entre elas
- ✅ **Atalhos Globais** - Use o numpad mesmo com outras janelas ativas
- ✅ **Tray Icon** - Minimize para a bandeja do sistema
- ✅ **Inicialização Automática** - Opção de iniciar com Windows
- ✅ **Interface Intuitiva** - Abas para Presets e Configurações

## 🎮 Ações Suportadas

- Fechar janela
- Abrir sites / programas / pastas
- Atalhos de teclado customizados
- Controle de mídia (play/pause, próxima, anterior, volume)
- Área de trabalho / Windows+Tab / Alt+Tab
- Bloquear PC
- Captura de tela
- Digitar texto com Enter automático

## ⌨️ Atalhos Globais

| Atalho | Ação |
|--------|------|
| `CTRL + ALT + F12` | Ativar/Desativar numpad |
| `CTRL + ALT + 1` | Trocar para preset "Default" |

## 📁 Estrutura do Projeto

```
numpad-streamdeck/
├── numpad_streamdeck.py      # App principal
├── installer.iss             # Script do instalador Windows
├── requirements.txt          # Dependências Python
├── icon.ico                  # Ícone do app
├── .gitignore               # Arquivos ignorados no Git
├── LICENSE                  # Licença MIT
└── README.md                # Este arquivo
```

## 🛠️ Desenvolvimento

### Branch Strategy (Git Flow)

```
main (production)
 ↓
release/* (prepare releases)
 ↓
develop (integration)
 ↓
feature/* (new features)
```

**Branches:**
- `main` - Código estável, releases apenas
- `develop` - Código em desenvolvimento, base para features
- `feature/*` - Novas funcionalidades (ex: `feature/custom-colors`)
- `release/*` - Preparação para release (ex: `release/1.1.0`)

### Configuração Local

1. Clone o repositório:
```bash
git clone https://github.com/NicollasCS/numpad-streamdeck.git
cd numpad-streamdeck
```

2. Crie um ambiente virtual:
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute o app:
```bash
python numpad_streamdeck.py
```

### Build do Executável

Para gerar o `.exe` pronto para distribuir:

```bash
pyinstaller --onefile --windowed --name NumpadStreamDeck numpad_streamdeck.py
```

O executável será gerado em `dist/NumpadStreamDeck.exe`

### Build do Instalador

Requer [Inno Setup 6](https://jrsoftware.org/isdl.php) instalado:

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

O instalador será gerado em `installer/NumpadStreamDeck_Setup.exe`

## 📦 Dependências

- `keyboard` - Detecção global de teclas do numpad
- `pystray` - Ícone na bandeja do sistema
- `pillow` - Criação de imagens para tray
- `tkinter` - Interface gráfica (incluído com Python)

## 📝 Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🤝 Contribuições

Contribuições são bem-vindas! 

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 💬 Dúvidas?

Abra uma [Issue](https://github.com/NicollasCS/numpad-streamdeck/issues) com sua pergunta!

---

**Made with ❤️**
