import sys

from lib.config import ConfigHandler
from lib.inputs import InputsHandler
from lib.markdown_converter import MarkdownConverter
from lib.printer import ThermalPrinter

__version__ = '1.0.0'

USAGE = (
    f"thermal-homelab0 v{__version__}\n\n"
    "Usage:\n\n"
    "  print.py file-to-print.md\n"
    "  cat file.md | python3 print.py"
)


def main() -> None:
    contents = InputsHandler.load()
    if not contents:
        raise ValueError(USAGE)

    config = ConfigHandler.load()
    data = MarkdownConverter(config.line_width).convert(contents)
    ThermalPrinter(config).print(data, config.max_lines)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
