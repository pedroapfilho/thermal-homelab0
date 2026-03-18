# Homelab Setup: Ubuntu Server

Running this on a Linux machine is the cleanest deployment. Docker USB passthrough works properly on Linux, so you get a fully containerised setup that survives reboots without any macOS workarounds.

---

## Prerequisites

SSH into your Ubuntu Server machine, then install Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER   # lets you run docker without sudo (re-login after)
```

---

## Get the project on the server

```bash
git clone <repo-url> ~/thermal-homelab0
cd ~/thermal-homelab0
```

Or copy from your Mac:
```bash
rsync -av --exclude='.venv' /path/to/thermal-homelab0/ user@server:~/thermal-homelab0/
```

---

## Find the printer's USB IDs

Plug in the printer, then:

```bash
lsusb
# Bus 001 Device 027: ID 04b8:0e27 Seiko Epson Corp. TM-T20X-II
```

The format is `vendor:product`. For the TM-T20X-II: `04b8:0e27`.

---

## USB permissions (udev rule)

By default, USB devices are only accessible by root. A udev rule grants access to the Docker group without needing `privileged: true`.

Create the rule:

```bash
sudo tee /etc/udev/rules.d/99-thermal-printer.rules <<EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="04b8", ATTRS{idProduct}=="0e27", MODE="0666"
EOF
```

Apply it without rebooting:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Verify the device node is now world-readable:
```bash
ls -la /dev/bus/usb/001/027   # bus/device numbers from lsusb output
# crw-rw-rw- 1 root root ...
```

With this rule in place you can remove `privileged: true` from `docker-compose.yml` if you want a tighter security posture. The project's default keeps it in for simplicity.

---

## Configure .env

```bash
cp .env.example .env
nano .env
```

```dotenv
THERMAL_TYPE=usb
THERMAL_VENDOR_ID=0x04b8
THERMAL_PRODUCT_ID=0x0e27
THERMAL_MAX_LINES=30
THERMAL_LINE_WIDTH=48
```

---

## SSL certificate

The server uses HTTPS. The repo includes self-signed certs that work for local use. If you're accessing from other devices on your network, regenerate them with your server's IP in the Subject Alt Name so browsers don't reject them:

```bash
openssl req -x509 -newkey rsa:4096 -days 3650 -nodes \
  -keyout certs/key.pem \
  -out certs/cert.pem \
  -subj "/CN=thermal-homelab0" \
  -addext "subjectAltName=IP:$(hostname -I | awk '{print $1}'),DNS:localhost"
```

Browsers will still show a warning for self-signed certs, but the connection is encrypted and you only need to accept it once per browser.

---

## Run with Docker

```bash
docker compose up -d
```

The `-d` flag runs it detached (background). The `deploy.restart_policy: condition: any` in `docker-compose.yml` means it will come back up automatically after a reboot or crash.

Check it's running:
```bash
docker compose ps
docker compose logs -f    # follow logs
```

---

## Access from your network

Find the server's LAN IP:
```bash
hostname -I | awk '{print $1}'
# e.g. 192.168.1.50
```

Open `https://192.168.1.50:8000` from any device on your network.

If you have a firewall (ufw) enabled:
```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

---

## Point a local domain at it (optional)

If you run a local DNS server (Pi-hole, AdGuard Home, or router custom DNS), you can add an A record:

```
thermal.home  →  192.168.1.50
```

Then access it at `https://thermal.home:8000`. If you want to drop the port, put nginx or Caddy in front as a reverse proxy.

### Minimal nginx reverse proxy

```bash
sudo apt install -y nginx
sudo tee /etc/nginx/sites-available/thermal <<EOF
server {
    listen 80;
    server_name thermal.home;

    location / {
        proxy_pass https://127.0.0.1:8000;
        proxy_ssl_verify off;
    }
}
EOF
sudo ln -s /etc/nginx/sites-available/thermal /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Updating

```bash
cd ~/thermal-homelab0
git pull
docker compose up -d --build
```

`--build` rebuilds the image with the new code. The old container is replaced; the new one starts immediately.

---

## Troubleshooting

**Printer not found in container**
```bash
lsusb                          # confirm it shows up on the host
docker compose exec thermal-homelab0 lsusb   # confirm it's visible inside
```
If it shows on the host but not inside, the `/dev/bus/usb` mount isn't working — check the udev rule and re-trigger it.

**Port already in use**
```bash
sudo lsof -i :8000
```

**View print job errors**
```bash
docker compose logs --tail=50
```

**Reset a stuck printer**
Power-cycle the printer. The USB session is per print job (subprocess model), so there's no persistent connection to clear.
