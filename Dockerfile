FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY pyproject.toml README.md ./
COPY farm_ontology ./farm_ontology

RUN addgroup --system app && adduser --system --ingroup app app
USER app

EXPOSE 8080

CMD ["python", "-m", "farm_ontology.http_service"]
