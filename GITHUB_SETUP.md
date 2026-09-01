# 🚀 Primeiros Passos no GitHub

## 1️⃣ Inicialize o Git no projeto

```bash
cd c:\Users\nicol\Documents\fodase
git init
git add .
git commit -m "Initial commit: Numpad Stream Deck v1.0.0"
```

## 2️⃣ Adicione o repositório remoto

```bash
git remote add origin https://github.com/NicollasCS/numpad-streamdeck.git
git branch -M main
```

## 3️⃣ Faça o push inicial

```bash
git push -u origin main
```

## 4️⃣ Crie a branch develop

```bash
git checkout -b develop
git push -u origin develop
```

## ✅ Pronto!

Agora seu projeto está no GitHub com:
- `main` - Código estável
- `develop` - Código em desenvolvimento

## 📥 Como Usar Depois

### Para novos features:
```bash
git checkout develop
git checkout -b feature/nome-da-feature
# Faça mudanças...
git commit -m "feat: descrição"
git push origin feature/nome-da-feature
# Abra PR no GitHub
```

### Para releases:
```bash
git checkout -b release/v1.1.0
# Finalize tudo...
git commit -m "Release v1.1.0"
git push origin release/v1.1.0
# Merge em main + tag + release no GitHub
```

Veja [WORKFLOW.md](WORKFLOW.md) para detalhes completos!
