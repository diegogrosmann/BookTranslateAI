# Contributing to BookTranslateAI

Thank you for your interest in contributing to BookTranslateAI! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Commit Message Convention](#commit-message-convention)

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. We expect all contributors to be respectful, inclusive, and professional in all interactions.

## How to Contribute

### Types of Contributions

We welcome several types of contributions:

- 🐛 **Bug fixes**: Help us identify and fix issues
- 🚀 **Feature development**: Add new functionality
- 📚 **Documentation**: Improve guides, docstrings, and examples
- 🧪 **Testing**: Add or improve test coverage
- 🎨 **UI/UX improvements**: Enhance user experience
- 🌐 **Translations**: Help translate the interface or documentation

### Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your contribution
4. Make your changes
5. Test your changes thoroughly
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A virtual environment tool (venv, conda, etc.)

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/diegogrosmann/BookTranslateAI.git
   cd BookTranslateAI
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev,test]"
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

5. **Run tests to verify setup:**
   ```bash
   pytest
   ```

## Coding Standards

### Code Style

We use the following tools for code quality:

- **Ruff**: For linting and formatting
- **MyPy**: For static type checking
- **Pre-commit**: To run checks automatically

### Code Formatting

- Line length: 88 characters (Black/Ruff default)
- Use type hints for all function parameters and return values
- Follow PEP 8 naming conventions
- Write docstrings for all public functions and classes

### Example Code Style

```python
from typing import Optional, List

def process_text(
    text: str,
    max_length: Optional[int] = None
) -> List[str]:
    """Process text into chunks.

    Args:
        text: The input text to process
        max_length: Maximum length of each chunk

    Returns:
        List of text chunks

    Raises:
        ValueError: If text is empty
    """
    if not text:
        raise ValueError("Text cannot be empty")

    # Implementation here
    return []
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_translator.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Write tests for all new functionality
- Aim for >80% code coverage for new code
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern

```python
def test_translate_text_success():
    """Test successful text translation."""
    # Arrange
    config = TranslationConfig(model="gpt-4", target_language="pt-BR")
    client = TranslationClient(config)

    # Act
    result = await client.translate_text("Hello, world!")

    # Assert
    assert isinstance(result, str)
    assert len(result) > 0
```

## Pull Request Process

### Before Submitting

1. **Run all checks locally:**
   ```bash
   ruff check . --fix
   ruff format .
   mypy src
   pytest --cov=src
   ```

2. **Update documentation** if needed
3. **Add tests** for new functionality
4. **Update CHANGELOG.md** with your changes

### PR Requirements

- [ ] All CI checks pass
- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] Commit messages follow convention
- [ ] PR description explains the change clearly

### PR Template

Use our PR template to ensure all requirements are met:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Tests pass locally
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

- Operating system and version
- Python version
- BookTranslateAI version
- Detailed steps to reproduce
- Expected vs actual behavior
- Error messages and stack traces
- Minimal code example if possible

### Feature Requests

For feature requests, please provide:

- Clear description of the feature
- Use cases and motivation
- Proposed API or interface
- Any relevant examples or mockups

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

### Examples

```
feat: add support for PDF password protection
fix: resolve memory leak in text chunking
docs: update installation instructions
test: add unit tests for translator module
```

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Release Process

1. Features are developed in feature branches
2. PRs are merged into `dev` branch
3. Releases are created from `main` branch
4. `dev` is merged into `main` for releases

## Questions and Support

- 📧 Create an issue for questions
- 💬 Join discussions in GitHub Discussions
- 📖 Check the documentation first

## Recognition

Contributors will be:
- Listed in the CONTRIBUTORS.md file
- Mentioned in release notes
- Invited to be maintainers for significant contributions

Thank you for contributing to BookTranslateAI! 🚀
