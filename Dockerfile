FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml ./

RUN uv sync

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]