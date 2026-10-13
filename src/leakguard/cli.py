from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

from . import __version__
from .checker import Finding, check_source
from .rules import RULES

# Cell magics whose body is Python, and line magics that run the Python statement after them.
PY_CELL_MAGICS = {"time", "timeit", "capture", "prun", "memit", "debug"}
PY_LINE_MAGIC = re.compile(r"^%(?:time|timeit|prun|memit|debug)\s+(?:-[A-Za-z]+(?:\s*\d+)?\s+)*(?P<stmt>\S.*)$")
SHELL_OR_MAGIC_ASSIGN = re.compile(r"^(?P<lhs>[A-Za-z_][\w.,\s\[\]]*?)\s*=\s*[!%]")
HELP = re.compile(r"^(\?{1,2}[\w.]+|[\w.]+\?{1,2})$")


def _ipython_to_python(line: str) -> str:
    """Rewrite one line of IPython syntax as Python with the same indentation, keeping any Python it runs."""
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]
    if m := PY_LINE_MAGIC.match(stripped):
        return indent + m.group("stmt")
    if stripped.startswith(("%", "!")) or HELP.match(stripped.rstrip()):
        return indent + "pass"
    if m := SHELL_OR_MAGIC_ASSIGN.match(stripped):
        return indent + m.group("lhs") + " = None"
    return line


def _code_cells(nb: dict) -> list[str]:
    if "cells" in nb:  # nbformat 4
        cells = nb["cells"]
    elif "worksheets" in nb:  # nbformat 3
        cells = [c for ws in nb["worksheets"] for c in ws.get("cells", [])]
    else:
        raise ValueError("no cells found; not a notebook format leakguard understands")
    out = []
    for cell in cells:
        if cell.get("cell_type") == "code":
            src = cell.get("source", cell.get("input", []))
            out.append("".join(src) if isinstance(src, list) else str(src))
    return out


def notebook_to_source(text: str, skipped: list[int] | None = None, other_language: dict[int, str] | None = None) -> str:
    """Concatenate code cells so line numbers refer to the combined source.

    IPython syntax becomes Python at the same indentation (keeps `if x:` blocks valid); `%time stmt` keeps `stmt`.
    A cell in another language (`%%bash`, `%%sql`, ...) is blanked and recorded in `other_language`. A cell that
    still isn't valid Python is blanked and its number appended to `skipped`: the scan of it is incomplete.
    """
    nb = json.loads(text)
    meta = nb.get("metadata", {})
    lang = (meta.get("kernelspec", {}).get("language") or meta.get("language_info", {}).get("name") or "python")
    if lang.lower() != "python":
        raise ValueError(f"not a Python notebook (kernel language: {lang})")
    out: list[str] = []
    for n, cell in enumerate(_code_cells(nb), 1):
        lines = cell.splitlines()
        magic = lines[0].strip()[2:].split()[0] if lines and lines[0].strip().startswith("%%") and lines[0].strip()[2:] else None
        if magic is not None and magic not in PY_CELL_MAGICS:
            if other_language is not None:
                other_language[n] = f"%%{magic}"
            out.extend([""] * len(lines) + [""])
            continue
        fixed, continued = [], False
        for i, ln in enumerate(lines):
            if continued:
                fixed.append("")  # rest of a `!cmd \\` line; an indented `pass` here would be an IndentationError
            elif i == 0 and magic is not None:
                fixed.append(ln[: len(ln) - len(ln.lstrip())] + "pass")
            else:
                fixed.append(_ipython_to_python(ln))
            continued = fixed[-1] in {"", ln[: len(ln) - len(ln.lstrip())] + "pass"} and ln.rstrip().endswith("\\")
        try:
            ast.parse("\n".join(fixed))
        except SyntaxError:
            if skipped is not None:
                skipped.append(n)
            fixed = [""] * len(fixed)
        out.extend(fixed)
        out.append("")
    return "\n".join(out)


def iter_files(paths: list[str]):
    for p in map(Path, paths):
        if p.is_dir():
            # Hidden/vendored directories are skipped relative to the root given, so `../project` or a
            # project that lives under a dot-directory still gets scanned.
            yield from sorted(f for f in p.rglob("*") if f.suffix in {".py", ".ipynb"} and not f.is_dir()
                              and not any(part.startswith(".") or part in {"node_modules", "__pycache__"}
                                          for part in f.relative_to(p).parts))
        else:
            yield p


class UnreadableFile(Exception):
    pass


def check_file(path: Path, incomplete: list[str] | None = None) -> list[Finding]:
    """Raises UnreadableFile when the file can't be parsed, so callers never mistake it for clean.

    A notebook with some unparseable Python cells is still checked; those cells are appended to `incomplete`.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise UnreadableFile(f"{path}: cannot read ({exc.strerror or exc})") from exc
    if path.suffix == ".ipynb":
        skipped_cells: list[int] = []
        other: dict[int, str] = {}
        try:
            text = notebook_to_source(text, skipped_cells, other)
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            raise UnreadableFile(f"{path}: not a valid notebook ({exc})") from exc
        except ValueError as exc:  # a notebook leakguard can't check: another kernel language, unknown layout
            raise UnreadableFile(f"{path}: {exc}") from exc
        if other:
            kinds = ", ".join(sorted(set(other.values())))
            print(f"leakguard: {path}: cell(s) {sorted(other)} are not Python ({kinds}) and were not checked", file=sys.stderr)
        if skipped_cells and incomplete is not None:
            incomplete.append(f"{path}: Python cell(s) {skipped_cells} could not be parsed and were not checked")
    try:
        return check_source(text, str(path))
    except SyntaxError as exc:
        raise UnreadableFile(f"{path}:{exc.lineno or 0}: cannot parse ({exc.msg})") from exc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="leakguard", description="Catch lookahead bias and data leakage.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="Check files or directories")
    c.add_argument("paths", nargs="+")
    c.add_argument("--format", choices=["text", "json"], default="text")
    c.add_argument("--select", help="Comma-separated rule IDs to run (default: all)")
    sub.add_parser("rules", help="List rules")
    args = p.parse_args(argv)

    if args.cmd == "rules":
        for rid, (name, _msg, note) in RULES.items():
            print(f"{rid}  {name}\n       {note}")
        return 0

    select = {s.strip().upper() for s in args.select.split(",")} if args.select else None
    if select and (unknown := select - set(RULES)):
        p.error(f"unknown rule id(s): {', '.join(sorted(unknown))}. Run `leakguard rules`.")
    results, skipped, incomplete, scanned = [], [], [], 0
    for f in iter_files(args.paths):
        scanned += 1
        try:
            findings = check_file(f, incomplete)
        except UnreadableFile as exc:
            skipped.append(str(exc))
            continue
        results += [(str(f), x) for x in findings if select is None or x.rule in select]
    for msg in skipped:
        print(f"leakguard: SKIPPED {msg}", file=sys.stderr)
    for msg in incomplete:
        print(f"leakguard: INCOMPLETE {msg}", file=sys.stderr)
    if scanned == 0:
        print("leakguard: no .py or .ipynb files found in the given paths", file=sys.stderr)
    if args.format == "json":
        print(json.dumps([{"path": path, "line": f.line, "col": f.col + 1, "rule": f.rule, "message": f.message} for path, f in results], indent=2))
    else:
        for path, f in results:
            print(f.format(path))
        if results:
            print(f"\n{len(results)} potential leak(s) found.", file=sys.stderr)
    if not results and scanned and not (skipped or incomplete):
        print("leakguard: no known leak patterns found. This is not proof the data is leak-free: "
              "leakguard only recognises the patterns listed by `leakguard rules`.", file=sys.stderr)
    if skipped or incomplete or scanned == 0:
        return 2  # could not check everything: never report success
    return 1 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())
