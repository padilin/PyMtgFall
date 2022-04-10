
# Dev Getting Started

---

## First steps:

1. Install [Poetry](https://python-poetry.org/docs/master/#installing-with-the-official-installer)
2. Optional: Set poetry to make an in project venv with `poetry config virtualenvs.in-project true`
3. Run `poetry install`
4. TODO: steps to run


# Committing:

This repo uses pre-commit to run Mypy, Pylint, Black, build requirements.txt, check pyproject.toml vs poetry, and isort at time of commit.


# Adding dependencies:

Run `poetry add <library>` and add `--dev` at the end to add dev dependency.


# Running Tests, Black, Pylint, etc.:

Use `poetry run <program>` to use the correct environment.