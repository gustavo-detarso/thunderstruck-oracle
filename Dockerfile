FROM python:3.12-slim

WORKDIR /app

# Copia apenas o requirements e instala dependências
COPY requirements.txt .

RUN set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        sqlite3 \
        python3-dev \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        poppler-utils \
        ghostscript \
        tesseract-ocr \
        tesseract-ocr-por \
        libtesseract-dev \
        libleptonica-dev \
        ffmpeg \
        python3-opencv \
        fonts-liberation \
        fonts-dejavu \
        curl \
        # Opcional: locale para UTF-8
        locales \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --force-reinstall --no-cache-dir google-search-results \
    && pip list

# Ajuste opcional de locale (evita erros com pdfplumber/camelot/unstructured)
RUN sed -i '/^#.*pt_BR.UTF-8/s/^# //' /etc/locale.gen && \
    locale-gen

# Copia os arquivos principais da aplicação
COPY app.py .
COPY config/layout.py ./config/

# Copia as pastas organizadas
COPY config/ ./config/
COPY chat/ ./chat/
COPY pages/ ./pages/
COPY rag/ ./rag/
COPY db/tags.json ./db/

# Estas pastas serão montadas via volume (e não precisam ser copiadas no build)
# models/, db/, data/, logs/

# Porta e execução do app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

