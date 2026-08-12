FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md persona.md ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --upgrade pip && pip install .

RUN useradd --create-home --uid 10001 studyme && chown -R studyme:studyme /app
USER studyme

EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
