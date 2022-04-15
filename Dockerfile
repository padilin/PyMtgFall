FROM python:3.10

ADD --chown=1001 . /app
ENV PATH="/app:${PATH}"
WORKDIR /app

USER 1001

RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/app/poetry python -
ENV PATH="/app/poetry/bin:${PATH}"
RUN poetry config virtualenvs.in-project true
RUN poetry config cache-dir /app/poetry/cache
RUN poetry install

ENTRYPOINT ["poetry"]
CMD ["run", "pytest"]