FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Atualize pip, set -e para fail fast, e instale as dependências
RUN set -e && \
    apt-get update && \
    apt-get install -y build-essential sqlite3 python3-dev && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --force-reinstall --no-cache-dir google-search-results && \
    pip list

COPY . .

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
