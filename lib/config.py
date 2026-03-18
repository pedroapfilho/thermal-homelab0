import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    type: str
    ip: str
    port: int
    max_lines: int
    line_width: int
    vendor_id: int
    product_id: int


class ConfigHandler:
    @staticmethod
    def load() -> Config:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.is_file():
            load_dotenv(env_file)

        config = Config(
            type=os.getenv('MARKY_TYPE', 'network').strip().lower(),
            ip=os.getenv('MARKY_IP', '127.0.0.1').strip(),
            port=int(os.getenv('MARKY_PORT', '9100').strip()),
            max_lines=int(os.getenv('MARKY_MAX_LINES', '30').strip()),
            line_width=int(os.getenv('MARKY_LINE_WIDTH', '48').strip()),
            vendor_id=int(os.getenv('MARKY_VENDOR_ID', '0x04b8').strip(), 0),
            product_id=int(os.getenv('MARKY_PRODUCT_ID', '0x0e20').strip(), 0),
        )

        if config.max_lines <= 0:
            raise ValueError(f"Invalid max lines number: {config.max_lines}")
        if config.line_width <= 0:
            raise ValueError(f"Invalid line width number: {config.line_width}")

        if config.type == 'network':
            if not (0 <= config.port <= 65535):
                raise ValueError(f"Invalid port number: {config.port}")
            if not config.ip:
                raise ValueError(f"Invalid IP address: {config.ip}")
        elif config.type == 'usb':
            if config.vendor_id < 0:
                raise ValueError(f"Invalid Vendor ID: {config.vendor_id}")
            if config.product_id < 0:
                raise ValueError(f"Invalid Product ID: {config.product_id}")
        else:
            raise ValueError(f"Invalid type: {config.type}")

        return config
