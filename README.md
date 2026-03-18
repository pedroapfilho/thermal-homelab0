# thermal-homelab0

Markdown thermal printer web service. Accepts Markdown via a web UI or CLI, converts it to ESC/POS commands, and sends it to a USB or network thermal receipt printer.

Forked from [ThermalMarky](https://github.com/sadreck/ThermalMarky) by Pavel Tsakalidis.

## Features

- **Markdown support:** headers, bold, underline, lists
- **Custom tags:** alignment (`[align=center]`), horizontal lines, QR codes
- **Web UI:** browser-based editor with formatting shortcuts
- **CLI mode:** print from terminal or pipe content into it
- **Docker ready:** USB passthrough works on Linux hosts

## Quick start

### 1. Configure

```bash
cp .env.example .env
```

Fill in your printer's connection details. For USB, find the vendor/product IDs:

- **Linux:** `lsusb` → `ID vendor:product`
- **macOS:** `ioreg -p IOUSB -l -w 0 | grep -A 5 "idVendor\|idProduct"`

```dotenv
MARKY_TYPE=usb
MARKY_VENDOR_ID=0x04b8
MARKY_PRODUCT_ID=0x0e27
MARKY_MAX_LINES=30
MARKY_LINE_WIDTH=48
```

### 2. Run with Docker (Linux)

```bash
docker compose up -d --build
```

Open `https://localhost:8000`. Uses self-signed certs in `certs/` — accept the browser warning once.

> **Note:** this service must be started with `docker compose up`, not `docker stack deploy`. Docker Swarm drops the `devices:` key silently, so USB passthrough will not work.

### 3. Run locally (macOS / development)

Requires [uv](https://docs.astral.sh/uv/) and `libusb` (`brew install libusb`).

```bash
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 \
  --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
```

## Usage

```bash
# Print a file
uv run python print.py my_list.md

# Pipe content
echo "# Hello World" | uv run python print.py

# HTTP request
curl -sk -X POST "https://127.0.0.1:8000/print" \
  --data-urlencode "markdown@my-message.md"
```

## Markdown reference

| Tag | Description |
|:----|:------------|
| `**word**` | Bold |
| `__word__` | Underline |
| `#` | H1 (3× size) |
| `##` | H2 (2× size) |
| `[align=center]` | Alignment (`left`, `center`, `right`) |
| `[qr=https://...]` | QR code |
| `[effect=line--]` | Full-width line of dashes |
| `[effect=line-*]` | Full-width line of asterisks |

## Homelab / Traefik

See [HOMELAB.md](HOMELAB.md) for the full Ubuntu Server setup guide including udev rules, Traefik integration, and Cloudflare tunnel configuration.

## License

MIT — Copyright (c) 2026 Pavel Tsakalidis.

You are free to use, modify, and distribute this software. The copyright notice and license text must be included in any copies or substantial portions of the code. See [LICENSE](LICENSE) for the full terms.
