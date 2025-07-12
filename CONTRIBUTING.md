# Contributing to WinGet Manifest Automation Tool

Thank you for your interest in contributing to the WinGet Manifest Automation Tool! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- GitHub account

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/WinGetManifestGeneratorTool.git
   cd WinGetManifestGeneratorTool
   ```

2. **Set up development environment**
   ```bash
   make dev-setup
   ```
   
   Or manually:
   ```bash
   pip install -e ".[dev]"
   pip install -r requirements-dev.txt
   pre-commit install
   ```

3. **Verify installation**
   ```bash
   make health-check
   wmat --help
   ```

### Project Structure

```
WinGetManifestGeneratorTool/
├── src/winget_automation/     # Main package
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface
│   ├── config/                # Configuration management
│   ├── monitoring/            # Monitoring and observability
│   ├── github/                # GitHub integration
│   └── utils/                 # Utility functions
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── e2e/                   # End-to-end tests
├── docs/                      # Documentation
├── scripts/                   # Development scripts
├── examples/                  # Usage examples
└── config/                    # Configuration files
```

## Making Changes

### Branch Naming

Use descriptive branch names with prefixes:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test improvements

Example: `feature/add-package-filtering`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): description

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build process or auxiliary tool changes

Examples:
```
feat(cli): add package filtering options
fix(monitoring): resolve health check timeout issue
docs(api): update configuration examples
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-e2e

# Run with coverage
make test-all
```

### Writing Tests

1. **Unit Tests** (`tests/unit/`)
   - Test individual functions and classes
   - Mock external dependencies
   - Fast execution

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - Use real external services when possible
   - May require API tokens

3. **End-to-End Tests** (`tests/e2e/`)
   - Test complete workflows
   - Use production-like environments
   - Longer execution time

### Test Guidelines

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Include both positive and negative test cases
- Mock external dependencies appropriately

## Code Style

### Formatting

We use automated code formatting:

```bash
# Format code
make format

# Check formatting
make lint
```

### Style Guide

- Follow [PEP 8](https://pep8.org/) for Python code
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pyre-check.org/docs/isort/) for import sorting
- Use [flake8](https://flake8.pycqa.org/) for linting

### Type Hints

- Use type hints for all public functions
- Use [mypy](http://mypy-lang.org/) for type checking
- Import types from `typing` module when needed

### Documentation

- Write docstrings for all public functions and classes
- Use [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) docstrings
- Include examples in docstrings when helpful

Example:
```python
def process_package(package_name: str, options: Dict[str, Any]) -> ProcessResult:
    """Process a WinGet package for updates.
    
    Args:
        package_name: Name of the package to process
        options: Processing options and configuration
        
    Returns:
        ProcessResult containing status and details
        
    Raises:
        PackageNotFoundError: If the package doesn't exist
        ProcessingError: If processing fails
        
    Example:
        >>> result = process_package("Microsoft.VSCode", {"check_updates": True})
        >>> print(result.status)
        "success"
    """
```

## Submitting Changes

### Pull Request Process

1. **Create a pull request**
   - Use a descriptive title
   - Reference related issues
   - Include a detailed description

2. **PR Template**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] Tests added/updated
   ```

3. **Review process**
   - All checks must pass
   - Code review required
   - Address feedback promptly
   - Maintain clean commit history

### Quality Gates

Before merging, ensure:
- [ ] All tests pass
- [ ] Code coverage maintained
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Documentation updated
- [ ] No security vulnerabilities

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes (backward compatible)

### Release Steps

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release PR
4. Tag release after merge
5. GitHub Actions handles PyPI deployment

## Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Email**: For security issues

### Documentation

- [User Guide](docs/user-guide/)
- [API Documentation](docs/api/)
- [Development Guide](docs/development/)

### Common Issues

1. **Import errors**: Ensure package is installed in development mode
2. **Test failures**: Check if dependencies are up to date
3. **Linting errors**: Run `make format` before committing

## Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- GitHub contributor statistics

Thank you for contributing to the WinGet Manifest Automation Tool!
