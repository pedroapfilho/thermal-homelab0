import sys
from pathlib import Path


class InputsHandler:
    @staticmethod
    def load() -> str | None:
        contents = InputsHandler.load_stdin()
        if contents is None and len(sys.argv) > 1:
            contents = InputsHandler.load_file(sys.argv[1])
        return contents

    @staticmethod
    def load_stdin() -> str | None:
        if sys.stdin.isatty():
            return None
        contents = sys.stdin.read().strip()
        return contents if contents else None

    @staticmethod
    def load_file(path: str) -> str | None:
        file = Path(path)
        if not file.is_file():
            return None
        contents = file.read_text().strip()
        return contents if contents else None
