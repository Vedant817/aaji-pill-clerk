# Public demo image. No torch, no local GGUF. Synthetic data only.
# Parser = Tinker hosted sampling. Teacher/compare = Google AI Studio Gemma (not in this image).
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

ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    PARSER_BACKEND=tinker \
    LLM_BACKEND=template \
    EXTRACT_BACKEND=manual

# Render sets $PORT. Local default 8080.
CMD ["sh", "-c", "uv run streamlit run app/Home.py --server.port ${PORT:-8080} --server.address 0.0.0.0 --server.headless true"]
