# Public demo image. No torch, no local GGUF.
# Parser = Tinker hosted sampling. Teacher/compare = DigitalOcean Gemma.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE NOTICE ./
COPY pillclerk ./pillclerk
COPY app ./app
COPY data/drugs.csv data/patterns.yaml data/demo ./data/
COPY eval/results.md ./eval/results.md

RUN pip install --no-cache-dir uv \
 && uv sync --frozen --no-dev --no-install-project \
 && uv pip install --system .

EXPOSE 8080
ENV STREAMLIT_SERVER_PORT=8080 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    PARSER_BACKEND=tinker \
    LLM_BACKEND=digitalocean \
    EXTRACT_BACKEND=hosted

CMD ["uv", "run", "streamlit", "run", "app/Home.py", "--server.port=8080", "--server.address=0.0.0.0"]
