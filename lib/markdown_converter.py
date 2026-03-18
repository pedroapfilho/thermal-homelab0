import re
from copy import copy

from lib.formatting import PrinterText, PrinterTextFormat


class MarkdownConverter:
    max_line_width: int

    def __init__(self, max_line_width: int) -> None:
        self.max_line_width = max_line_width

    def convert(self, markdown_text: str) -> list[PrinterText]:
        lines = markdown_text.strip().splitlines()
        output: list[PrinterText] = []
        for line in lines:
            output.extend(self._parse_line(line))
        return self._fix_line_width(output, self.max_line_width)

    def _reset_format(self) -> PrinterTextFormat:
        return PrinterTextFormat()

    def _new_line(self) -> PrinterText:
        return PrinterText("\n", format=self._reset_format())

    def _is_format(
        self, name: str, start: bool, current_position: int, chars: list[str]
    ) -> bool:
        if name.lower() == "bold":
            c = "*"
        elif name.lower() == "underline":
            c = "_"
        else:
            return False

        if current_position + 1 >= len(chars):
            return False

        if chars[current_position] != c or chars[current_position + 1] != c:
            return False

        if start:
            if current_position + 2 >= len(chars):
                return False
            return not chars[current_position + 2].isspace()

        # Closing tag: must be preceded by a non-space character
        if current_position > 0 and chars[current_position - 1].isspace():
            return False

        # Avoid consuming part of a triple marker (like ***) as a double marker
        if current_position + 2 < len(chars) and chars[current_position + 2] == c:
            return False

        return True

    def _parse_line(self, input_line: str) -> list[PrinterText]:
        if len(input_line) == 0:
            return [self._new_line()]

        current_format = self._reset_format()

        effect = re.match(r"\[effect=line-(.)\]", input_line)
        if effect:
            input_line = effect.group(1) * self.max_line_width

        alignment = re.match(r"^\[align=(.*?)]", input_line)
        if alignment:
            if alignment.group(1) in ["left", "right", "center"]:
                current_format.align = alignment.group(1)
            input_line = input_line[len(alignment.group(0)) :].strip()

        qr = re.match(r"^\[qr=(.*?)]", input_line)
        if qr:
            return [PrinterText(qr.group(1), format=copy(current_format), qr=True)]

        if input_line.startswith("## "):
            input_line = input_line[3:]
            current_format.height = 2
            current_format.width = 2
        elif input_line.startswith("# "):
            input_line = input_line[2:]
            current_format.height = 3
            current_format.width = 3

        output: list[PrinterText] = []
        chars = list(input_line)
        chars_iter = enumerate(chars)

        for i, c in chars_iter:
            toggled = False

            for style in ["bold", "underline"]:
                current_state = getattr(current_format, style)
                if self._is_format(style, not current_state, i, chars):
                    setattr(current_format, style, not current_state)
                    next(chars_iter, None)
                    toggled = True
                    break

            if toggled:
                continue

            output.append(PrinterText(c, format=copy(current_format)))

        output.append(self._new_line())
        return output

    def _fix_line_width(
        self, data: list[PrinterText], max_width: int
    ) -> list[PrinterText]:
        output: list[PrinterText] = []
        lines = self._split_tokens_to_lines(data)

        for line in lines:
            tokens_to_wrap = [t for t in line if not t.is_newline()]
            physical_line_width = sum(t.format.width for t in tokens_to_wrap)

            if physical_line_width <= max_width:
                output.extend(line)
                continue

            current_row: list[PrinterText] = []
            current_len = 0

            while tokens_to_wrap:
                word = self._get_next_stream(tokens_to_wrap)
                tokens_to_wrap = tokens_to_wrap[len(word) :]

                if word[0].is_whitespace() and current_len == 0:
                    continue

                word_physical_width = sum(t.format.width for t in word)

                if current_len + word_physical_width > max_width:
                    if current_row:
                        output.extend(current_row + [self._new_line()])
                        current_row = []
                        current_len = 0

                    if word_physical_width > max_width:
                        for token in word:
                            if current_len + token.format.width > max_width:
                                output.extend(current_row + [self._new_line()])
                                current_row = [token]
                                current_len = token.format.width
                            else:
                                current_row.append(token)
                                current_len += token.format.width
                    else:
                        current_row = list(word)
                        current_len = word_physical_width
                else:
                    current_row.extend(word)
                    current_len += word_physical_width

            if current_row:
                output.extend(current_row + [self._new_line()])

        return output

    def _split_tokens_to_lines(
        self, data: list[PrinterText]
    ) -> list[list[PrinterText]]:
        lines: list[list[PrinterText]] = []
        line: list[PrinterText] = []
        for text in data:
            line.append(text)
            if text.is_newline():
                lines.append(line)
                line = []
        if line:
            lines.append(line)
        return lines

    def _get_next_stream(self, line: list[PrinterText]) -> list[PrinterText]:
        word: list[PrinterText] = []
        for letter in line:
            word.append(letter)
            if letter.is_word_terminator():
                break
        if len(word) > 1 and word[-1].is_newline():
            word.pop()
        return word
