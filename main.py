import os
import sys
import subprocess
import tempfile

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


@app.get("/")
async def read_index() -> FileResponse:
    return FileResponse("www/index.html")


@app.post("/print")
async def print_markdown(markdown: str = Form(...)) -> dict[str, str]:
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
        raise HTTPException(status_code=500, detail=f"Print script error:\n{error_msg}")

    return {"status": "success", "message": "Printed successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
