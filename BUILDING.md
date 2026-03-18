# Building a Thermal Printer Web Service

Everything you need to understand to build something like this from scratch.

---

## What this is

A web UI that accepts Markdown, converts it to printer commands, and sends them over USB to a thermal receipt printer. The stack is: FastAPI (Python) + python-escpos + pyusb + a single HTML page.

---

## The ESC/POS Protocol

Thermal receipt printers speak **ESC/POS** — a binary command language from Epson that became the industry standard. Instead of rendering a page like a laser printer, you stream commands and text sequentially.

Key commands:
- `ESC @` — initialize printer
- `ESC E n` — bold on/off
- `ESC a n` — alignment (left/center/right)
- `GS ! n` — character size (width/height multipliers)
- `GS V n` — cut paper
- `GS k` — barcode
- `GS ( k` — QR code

You almost never write raw ESC/POS bytes by hand. Use **python-escpos**, which wraps all of this:

```python
from escpos.printer import Usb

p = Usb(0x04b8, 0x0e27, in_ep=0x82, out_ep=0x01)
p.set(bold=True, align='center')
p.text('Hello\n')
p.cut()
```

---

## USB Connection

### Finding vendor/product IDs

Every USB device has a vendor ID and product ID. You need both to open the device.

- **macOS:** `ioreg -p IOUSB -l -w 0 | grep -A 5 "idVendor\|idProduct"`
- **Linux:** `lsusb` (shows `ID vendor:product`)

Values are hexadecimal. Epson's vendor ID is always `0x04b8`. The product ID varies by model.

### The USB stack

```
python-escpos
    └── pyusb          (Python bindings)
        └── libusb     (C library, cross-platform)
            └── USB device
```

- **libusb** is the C library that talks to the OS USB subsystem. Install it before anything else.
  - macOS: `brew install libusb`
  - Linux: `apt install libusb-1.0-0-dev`
- **pyusb** is the Python wrapper around libusb.
- **python-escpos** builds the ESC/POS command stream and writes it through pyusb.

### Endpoints

USB bulk transfer devices have IN and OUT endpoints. For the TM-T20X-II:
- OUT `0x01` — host → printer (commands and text)
- IN `0x82` — printer → host (status)

python-escpos auto-detects these in most cases. Specify them explicitly if auto-detection fails:
```python
Usb(vendor_id, product_id, in_ep=0x82, out_ep=0x01)
```

### macOS vs Linux

On **Linux**, Docker can pass through USB devices with `privileged: true` and a `/dev/bus/usb` device mount. This works because Docker runs directly on the Linux kernel.

On **macOS**, Docker Desktop runs inside a Linux VM. USB devices attached to the Mac are not visible inside that VM — `privileged` and device mounts do nothing. You must run the app natively on macOS.

---

## The Print Pipeline

```
Browser (Markdown text)
    │  POST /print
    ▼
FastAPI server
    │  writes to data/print_job.md
    │  subprocess: python print.py <file>
    ▼
Markdown parser
    │  produces list of PrinterText tokens
    │  each token has: text content + format (bold, underline, align, size)
    ▼
ThermalPrinter
    │  for each token: printer.set(...) then printer.text(...)
    │  adds timestamp + cut at end
    ▼
python-escpos → pyusb → libusb → USB → Printer
```

### Why subprocess?

`main.py` (the FastAPI server) shells out to `print.py` rather than calling the printer code directly. This isolates the USB session — each print job gets a fresh connection, so a failed job doesn't leave a stale USB handle blocking the next one.

---

## Markdown to ESC/POS

The converter walks the Markdown and emits a flat list of tokens. Each token is either:
- A `PrinterText` — carries text content and a `PrinterTextFormat` (bold, underline, alignment, height multiplier, width multiplier)
- A newline marker
- A QR code marker

Mapping:
| Markdown | ESC/POS |
|---|---|
| `# Heading` | height=3, width=3 |
| `## Heading` | height=2, width=2 |
| `**bold**` | bold=True |
| `__underline__` | underline=True |
| `[align=center]` | align='center' |
| `[qr=URL]` | QR code graphic |
| `[effect=line-X]` | repeated character X across full width |

Line width matters: the printer has a fixed character width (48 chars for 80mm paper at normal font). The converter word-wraps tokens to that width, accounting for the fact that a 2× wide character occupies 2 character positions.

---

## FastAPI Server

Two routes:

```python
GET  /       → serves www/index.html
POST /print  → accepts form field `markdown`, runs print.py
```

FastAPI handles the HTTP layer. `python-multipart` is required for `Form(...)` data.

For HTTPS, pass SSL cert and key to uvicorn:
```
uvicorn main:app --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
```

Self-signed certs work fine for local use. Generate them with:
```
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 3650 -nodes -subj "/CN=localhost"
```

HTTPS matters here because browsers block camera/clipboard APIs on plain HTTP origins, and you may want to use the page from a phone on your local network.

---

## Configuration

All config comes from environment variables (loaded via `python-dotenv` from `.env`):

| Variable | Purpose |
|---|---|
| `THERMAL_TYPE` | `usb` or `network` |
| `THERMAL_VENDOR_ID` | USB vendor ID (hex, e.g. `0x04b8`) |
| `THERMAL_PRODUCT_ID` | USB product ID (hex, e.g. `0x0e27`) |
| `THERMAL_IP` | Printer IP (network mode only) |
| `THERMAL_PORT` | Printer port, usually `9100` (network mode only) |
| `THERMAL_LINE_WIDTH` | Characters per line (48 for 80mm, 32 for 58mm) |
| `THERMAL_MAX_LINES` | Truncate after this many lines |

Network printers (Ethernet or Wi-Fi) are simpler to configure — no USB driver concerns. The printer exposes a raw TCP socket on port 9100.

---

## Docker (Linux only)

For Linux deployment, Docker handles the USB access cleanly:

```yaml
services:
  app:
    build: .
    network_mode: host
    privileged: true
    devices:
      - "/dev/bus/usb:/dev/bus/usb"
    env_file: .env
```

- `privileged: true` gives the container USB device access
- `network_mode: host` avoids NAT so the container can reach the printer on the local network if needed
- `env_file` loads your `.env` into the container environment

On Linux, udev rules are the proper long-term solution instead of running privileged:
```
SUBSYSTEM=="usb", ATTRS{idVendor}=="04b8", MODE="0666"
```

---

## Running Natively (macOS)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 \
  --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
```

The server needs to stay running in a terminal session (or be configured as a launchd service for persistence across reboots).

---

## Dependencies

```
python-escpos[all]   # ESC/POS protocol + USB/network/serial printer support
python-dotenv        # .env file loading
fastapi              # web framework
uvicorn              # ASGI server
python-multipart     # form data parsing (required by FastAPI for Form())
```

`python-escpos[all]` pulls in pyusb, pyserial, pycups, qrcode, Pillow, and python-barcode — covering all connection types and print features.

---

## What to extend

- **Image printing:** python-escpos supports `p.image('file.png')` — it converts to 1-bit and sends as a raster bitmap
- **Barcode printing:** `p.barcode('12345678', 'EAN8')` — many formats supported
- **Status polling:** the IN endpoint returns printer status bytes (paper out, cover open, etc.)
- **Serial connection:** some printers use RS-232 instead of USB — `escpos.printer.Serial('/dev/ttyUSB0', baudrate=9600)`
- **Multiple printers:** instantiate multiple `Usb` objects with different product IDs
