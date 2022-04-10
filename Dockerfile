FROM python:3.10

ADD --chown=1001 . /app
ENV PATH="/app/src:${PATH}"
WORKDIR /app

USER 1001

RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/app/poetry python -
ENV PATH="/app/poetry/bin:${PATH}"
RUN poetry config virtualenvs.create false
RUN poetry config cache-dir /app/poetry/cache
RUN poetry install --no-dev

CMD ["poetry", "run", "python", "src/main.py"]