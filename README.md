
# Dev Getting Started

---

## Steps:

1. Install [Poetry](https://python-poetry.org/docs/master/#installing-with-the-official-installer)
2. Optional: Set poetry to make an in project venv with `poetry config virtualenvs.in-project true`
3. Run `poetry install`
4. Run `poetry run pre-commit install`
5. Edit files
6. Run `poetry run python <file>`
7. Run `poetry run pre-commit` to lint, format, generate requirements.txt, and more.
9. On commit: see committing section


# Committing:

This repo uses pre-commit to run Mypy, Pylint, Black, build requirements.txt, check pyproject.toml vs poetry, and isort at time of commit.  
Commit will run black on all files, sort imports, and generate requirements.txt. Make sure requirements.txt is added and re-commit  
This can be avoided by running `poetry run pre-commit`


# Commands:

`poetry add/remove <library> [--dev]` to add or remove dev dependency.  
`poetry run pytest` to run pytest with coverage and generate HTML report in htmlcov/  
`poetry run black .` to black format code.  
`poetry run pre-commit` to run all of the pre-commit checks. Will modify files and generate some.  
`poetry run python <script>` to use the environment to run code.


# Running Tests, Black, Pylint, etc.:

Use `poetry run <program>` to use the correct environment.


# Changes from API

Some words are reserved by python, so they are translated.  

Data:  
"id" = "api_id"  
"object" = "obj"  
"format" = "format_response"  
"dir" = "direction"  
"set" = "set_code"  
"type" = "api_type"

Objects:  
"list" = "APIList"  