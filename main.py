import os
import sys
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse

app = FastAPI()

DATA_DIR = Path(__file__).parent / "data"
LOGS_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOGS_DIR / "prints.log"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

SEPARATOR = "=" * 48


def log_print(ip: str, markdown: str, *, success: bool, error: str = "") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "SUCCESS" if success else f"ERROR\n{error.strip()}"
    entry = (
        f"{SEPARATOR}\n"
        f"{timestamp} | {ip}\n"
        f"{'-' * 48}\n"
        f"{markdown.strip()}\n"
        f"{'-' * 48}\n"
        f"{status}\n\n"
    )
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry)


@app.get("/")
async def read_index() -> FileResponse:
    return FileResponse("www/index.html")


@app.post("/print")
async def print_markdown(request: Request, markdown: str = Form(...)) -> dict[str, str]:
    client_ip = request.client.host if request.client else "unknown"

    # Write to a unique temp file so concurrent requests don't clobber each other.
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", dir=DATA_DIR, delete=False
        ) as f:
            f.write(markdown)
            temp_path = f.name
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e

    try:
        result = subprocess.run(
            [sys.executable, "print.py", temp_path],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
    finally:
        os.unlink(temp_path)

    if result.returncode != 0:
        error_msg = f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        log_print(client_ip, markdown, success=False, error=error_msg)
        raise HTTPException(status_code=500, detail=f"Print script error:\n{error_msg}")

    log_print(client_ip, markdown, success=True)
    return {"status": "success", "message": "Printed successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
