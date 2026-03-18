"""
Local dev / Docker fallback entry point.

Generates self-signed certs if they are missing, then starts uvicorn with SSL.
For production (Traefik / Cloudflare), docker-compose overrides CMD to plain HTTP
and this file is not used.
"""

import subprocess
from pathlib import Path

import uvicorn

CERTS_DIR = Path(__file__).parent / "certs"


def ensure_certs() -> None:
    cert = CERTS_DIR / "cert.pem"
    key  = CERTS_DIR / "key.pem"

    if cert.exists() and key.exists():
        return

    CERTS_DIR.mkdir(exist_ok=True)
    print("Generating self-signed certificates…", flush=True)

    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-days", "3650", "-nodes",
            "-keyout", str(key),
            "-out",    str(cert),
            "-subj",   "/CN=thermal-homelab0",
            "-addext", "subjectAltName=DNS:localhost,DNS:thermal.homelab0.local",
        ],
        check=True,
        capture_output=True,
    )

    print(f"Certificates written to {CERTS_DIR}/", flush=True)


if __name__ == "__main__":
    ensure_certs()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile=str(CERTS_DIR / "key.pem"),
        ssl_certfile=str(CERTS_DIR / "cert.pem"),
    )
