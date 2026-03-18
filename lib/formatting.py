from dataclasses import dataclass, field


@dataclass
class PrinterTextFormat:
    align: str = 'left'
    underline: bool = False
    bold: bool = False
    height: int = 1
    width: int = 1

    @property
    def custom_size(self) -> bool:
        return self.height != 1 or self.width != 1

    @property
    def normal_size(self) -> bool:
        return self.height == 1 and self.width == 1


@dataclass
class PrinterText:
    text: str
    format: PrinterTextFormat = field(default_factory=PrinterTextFormat)
    qr: bool = False

    def is_newline(self) -> bool:
        return self.text in ['\n', '\r']

    def is_word_terminator(self) -> bool:
        return self.text == ' '

    def is_whitespace(self) -> bool:
        return self.text.isspace()

    def __str__(self) -> str:
        return self.text
