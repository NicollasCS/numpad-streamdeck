# Contributing to Numpad Stream Deck

First off, thanks for considering contributing to Numpad Stream Deck! It's people like you that make this project such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- Use a clear and descriptive title
- Describe the exact steps which reproduce the problem
- Provide specific examples to demonstrate the steps
- Describe the behavior you observed after following the steps
- Explain which behavior you expected to see instead and why
- Include your Windows version and Python version

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- Use a clear and descriptive title
- Provide a step-by-step description of the suggested enhancement
- Provide specific examples to demonstrate the steps
- Describe the current behavior and expected behavior
- Explain why this enhancement would be useful

### Pull Requests

- Fill in the required template
- Follow the Python styleguide
- Include appropriate test cases
- Document new code based on the Documentation Styleguide
- End all files with a newline

## Development Setup

### Prerequisites

- Python 3.14.5 or higher
- Windows 10 or later
- Git

### Setup Steps

1. Fork the repository
```bash
git clone https://github.com/YOUR-USERNAME/numpad-streamdeck.git
cd numpad-streamdeck
```

2. Create a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Run the application
```bash
python numpad_streamdeck.py
```

5. Create a feature branch
```bash
git checkout -b feature/your-feature-name
```

## Styleguides

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- Follow [Conventional Commits](https://www.conventionalcommits.org/) format

Examples:
```
feat: add support for custom action types
fix: resolve numpad key detection lag
docs: update installation instructions
refactor: simplify preset loading logic
test: add unit tests for key validation
```

### Python Styleguide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use 4 spaces for indentation
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and small

Example:
```python
def execute_action(self, action_type: str, action_value: str) -> None:
    """
    Execute a configured action.
    
    Args:
        action_type: Type of action to execute
        action_value: Value/parameter for the action
    """
    # Implementation here
    pass
```

### Documentation Styleguide

- Use Markdown
- Reference functions and classes using backticks: `function_name()`
- Use clear, simple language
- Include code examples where appropriate

## Building and Testing

### Run Syntax Check

```bash
python -m py_compile numpad_streamdeck.py
```

### Build Executable with PyInstaller

```bash
pyinstaller --onefile --windowed numpad_streamdeck.py
```

### Build Installer with Inno Setup

```bash
iscc installer.iss
```

## Release Process

1. Update version number if needed
2. Update CHANGELOG.md with new changes
3. Create a pull request to main
4. After merge, create a GitHub Release with binaries
5. Tag the release with semantic versioning (v1.0.0)

## Questions?

Feel free to open an issue for any questions or clarifications needed.

---

Thank you for contributing!
