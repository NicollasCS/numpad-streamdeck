# Git Workflow - Numpad Stream Deck

Este documento explica como trabalhar com branches e releases neste projeto.

## 📊 Estratégia de Branches (Git Flow)

```
┌─────────────────────────────────────────────────────────────┐
│ main (Production)                                           │
│ Apenas código estável, releases apenas                     │
└─────────────────────────────────────────────────────────────┘
                          ↑
                     (merge com tag)
                          ↑
┌─────────────────────────────────────────────────────────────┐
│ release/v1.0.0 (Pre-release)                               │
│ Preparação para release, bug fixes apenas                  │
└─────────────────────────────────────────────────────────────┘
                          ↑
                   (branch de develop)
                          ↑
┌─────────────────────────────────────────────────────────────┐
│ develop (Integration)                                       │
│ Código em desenvolvimento, base para features              │
└─────────────────────────────────────────────────────────────┘
                    ↑                ↑
            (merge de features)  (merge de release)
                    ↑                ↑
    ┌───────────────┴────────────────┐
    ↓                                 ↑
┌──────────────────────┐      ┌──────────────────┐
│ feature/nova-coisa   │      │ feature/bugfix   │
│ Novas funcionalidades│      │ Correção de bugs │
└──────────────────────┘      └──────────────────┘
```

---

## 🚀 Workflow Prático

### 1️⃣ **Iniciar uma Nova Feature**

```bash
# Atualize develop
git checkout develop
git pull origin develop

# Crie uma nova branch para sua feature
git checkout -b feature/nome-da-feature

# Faça suas mudanças...
# Commit
git commit -m "feat: descrição da mudança"

# Push para GitHub
git push origin feature/nome-da-feature
```

### 2️⃣ **Criar um Pull Request (PR)**

No GitHub:
1. Vá em [Pull Requests](https://github.com/NicollasCS/numpad-streamdeck/pulls)
2. Clique "New Pull Request"
3. Base: `develop`, Compare: `feature/sua-feature`
4. Descreva a mudança
5. Clique "Create Pull Request"

### 3️⃣ **Preparar para Release**

Quando tiver features prontas para lançar:

```bash
# Vá para develop
git checkout develop
git pull origin develop

# Crie branch de release
git checkout -b release/v1.1.0

# (Opcional) Faça ajustes finais, bug fixes, versão
# Edit version in code if needed
git commit -m "chore: bump version to 1.1.0"

# Push
git push origin release/v1.1.0
```

### 4️⃣ **Fazer Merge em Main (Release)**

```bash
# Vá para main
git checkout main
git pull origin main

# Merge da release
git merge release/v1.1.0

# Crie tag (importante para releases)
git tag -a v1.1.0 -m "Release version 1.1.0"

# Push
git push origin main
git push origin v1.1.0
```

### 5️⃣ **Criar Release no GitHub**

No GitHub:
1. Vá em [Releases](https://github.com/NicollasCS/numpad-streamdeck/releases)
2. Clique "Draft a new release"
3. Tag: `v1.1.0`
4. Title: `Numpad Stream Deck v1.1.0`
5. Description: Escreva as mudanças
6. **Attach binaries:**
   - `installer/NumpadStreamDeck_Setup.exe` (instalador)
   - `dist/NumpadStreamDeck.exe` (executável)
7. Clique "Publish release"

---

## 📝 Convenção de Commits

Use o padrão [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: nova funcionalidade
fix: correção de bug
docs: mudanças na documentação
style: formatação, semicolons, etc
refactor: refatoração de código
test: adição de testes
chore: build, dependências, etc
```

Exemplos:
```bash
git commit -m "feat: adiciona suporte a presets customizados"
git commit -m "fix: corrige bug na detecção de teclas"
git commit -m "docs: atualiza README com instruções"
```

---

## 🔄 Merge Back

Após lançar uma release, faça merge de volta para develop:

```bash
git checkout develop
git pull origin develop
git merge release/v1.1.0
git push origin develop
```

---

## 🗑️ Limpar Branches Antigas

Após merge, delete a branch:

```bash
# Local
git branch -d feature/nome-da-feature

# Remoto (GitHub)
git push origin --delete feature/nome-da-feature
```

---

## 📋 Checklist para Release

Antes de criar uma release:

- [ ] Todas as features testadas
- [ ] Código compilado sem erros
- [ ] README atualizado
- [ ] Versão atualizada (se necessário)
- [ ] Executáveis gerados (`dist/` e `installer/`)
- [ ] Testou o instalador
- [ ] Criou tag com `v1.x.x`

---

## 🔗 Links Úteis

- [GitHub Releases](https://github.com/NicollasCS/numpad-streamdeck/releases)
- [GitHub Issues](https://github.com/NicollasCS/numpad-streamdeck/issues)
- [GitHub Discussions](https://github.com/NicollasCS/numpad-streamdeck/discussions)

---

**Questions? Open an issue!**
