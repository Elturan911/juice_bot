FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-interaction

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "src/bot.py"]
