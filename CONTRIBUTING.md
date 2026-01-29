# Contributing to WhatsApp Agent

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to this project. These are mostly guidelines, not rules. Use your best judgment and feel free to propose changes to this document in a pull request.

## 🛠️ Development Setup

1.  **Clone the repository**
2.  **Install dependencies**:
    We recommend using `uv` for faster installation, but `pip` works too.
    ```bash
    pip install -e ".[dev]"
    ```
3.  **Install pre-commit hooks**:
    This is crucial to ensure code quality before every commit.
    ```bash
    pre-commit install
    ```

## 🧪 Testing

We use `pytest` for testing. Ensure all tests pass before submitting a PR.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

## 🎨 Code Style

We use `ruff` for linting and formatting, and `mypy` for static type checking.
These are automatically run by the `pre-commit` hooks, but you can run them manually:

```bash
# Format and Lint
ruff format .
ruff check . --fix

# Type check
mypy src/
```

## 🔀 Pull Requests

1.  Create a new branch for your feature (`feat/my-feature`) or fix (`fix/my-fix`).
2.  Make sure your code passes all tests and pre-commit hooks.
3.  Open a Pull Request describing your changes.

## 📝 Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

- `feat: ...` for new features
- `fix: ...` for bug fixes
- `docs: ...` for documentation changes
- `refactor: ...` for code refactoring
- `test: ...` for adding tests
- `chore: ...` for maintenance tasks

Example:
> `feat: implement google calendar integration`
