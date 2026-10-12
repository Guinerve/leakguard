"""flake8 plugin: `pip install leakguard` makes flake8 report LG0xx codes."""

from __future__ import annotations

import ast
from collections.abc import Iterator

from . import __version__
from .checker import check_source


class LeakguardPlugin:
    name = "leakguard"
    version = __version__

    def __init__(self, tree: ast.AST, lines: list[str] | None = None) -> None:
        self.lines = lines or []

    def run(self) -> Iterator[tuple[int, int, str, type]]:
        try:
            findings = check_source("".join(self.lines))
        except SyntaxError:
            return  # flake8 reports E999 for this itself
        for f in findings:
            yield f.line, f.col, f"{f.rule} {f.message}", type(self)
