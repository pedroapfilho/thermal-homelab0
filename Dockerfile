FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libusb-1.0-0-dev \
    libcups2-dev \
    python3-dev \
    gcc \
    openssl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN UV_SYSTEM_PYTHON=1 uv sync --frozen --no-dev

COPY . .

RUN mkdir -p data certs \
    && openssl req -x509 -newkey rsa:4096 -days 3650 -nodes \
       -keyout certs/key.pem \
       -out    certs/cert.pem \
       -subj   "/CN=thermal-homelab0" \
       -addext "subjectAltName=DNS:localhost,DNS:thermal.homelab0.local" \
       2>/dev/null

EXPOSE 8000

# docker-compose overrides this to plain HTTP (Traefik handles TLS).
# When run directly, start.py generates certs if missing and serves HTTPS.
CMD ["python", "start.py"]
