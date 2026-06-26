# Tessera API — one image, runs cloud (Cloud Run) or air-gapped (Compose/k3s).
# The warehouse is regenerated deterministically at startup, so there is no database to provision.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TESSERA_BIND_HOST=0.0.0.0 \
    PORT=8080

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --upgrade pip && pip install ".[api,crypto]"

# Run as a non-root user; the per-install signing key lands under its home (~/.config/tessera).
RUN useradd --create-home --uid 10001 tessera
USER tessera

EXPOSE 8080
# Binds 0.0.0.0 → the app FAILS CLOSED unless TESSERA_API_TOKEN is set (see api/security.py).
# For stable receipts across cold starts, also set TESSERA_SIGNING_KEY (64 hex chars).
CMD ["sh", "-c", "tessera serve --host 0.0.0.0 --port ${PORT:-8080}"]
