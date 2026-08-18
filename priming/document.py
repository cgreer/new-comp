
from dataclasses import dataclass
from typing import (Union,)
from pathlib import Path

Pathlike = Union[str, Path]


@dataclass
class Document:
    name: str
    text: str
    src_file: Pathlike
    indent_spaces: int = 4

    @classmethod
    def from_file(
        cls,
        name: str,
        file_path: Pathlike,
        indent_spaces: int = 4,
    ):
        text = open(file_path, 'r').read()
        src_file = file_path
        return cls(name, text, src_file, indent_spaces)
