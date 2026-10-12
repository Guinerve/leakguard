from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .checker import Finding, check_source
from .rules import RULES


def notebook_to_source(text: str, skipped: list[int] | None = None) -> str:
    """Concatenate code cells so line numbers refer to the combined source.

    IPython magics become `pass` at the same indentation (keeps `if x:` blocks valid). A cell that still
    isn't valid Python (shell cells, `%%bash`, odd syntax) is blanked and its number appended to `skipped`.
    """
    import ast

    nb = json.loads(text)
    out: list[str] = []
    for n, cell in enumerate((c for c in nb.get("cells", []) if c.get("cell_type") == "code"), 1):
        src = cell.get("source", [])
        lines = "".join(src).splitlines() if isinstance(src, list) else str(src).splitlines()
        fixed, continued = [], False
        for ln in lines:
            stripped = ln.lstrip()
            if continued or stripped.startswith(("%", "!")):
                fixed.append(ln[: len(ln) - len(stripped)] + "pass")
                continued = ln.rstrip().endswith("\\")
            else:
                fixed.append(ln)
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
            yield from sorted(f for f in p.rglob("*") if f.suffix in {".py", ".ipynb"}
                              and not any(part.startswith(".") or part in {"node_modules", "__pycache__"}
                                          for part in f.relative_to(p).parts))
        else:
            yield p


class UnreadableFile(Exception):
    pass


def check_file(path: Path) -> list[Finding]:
    """Raises UnreadableFile when the file can't be parsed, so callers never mistake it for clean."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".ipynb":
        skipped_cells: list[int] = []
        try:
            text = notebook_to_source(text, skipped_cells)
            if skipped_cells:
                print(f"leakguard: {path}: {len(skipped_cells)} cell(s) are not plain Python and were not checked: {skipped_cells}", file=sys.stderr)
        except (json.JSONDecodeError, AttributeError) as exc:
            raise UnreadableFile(f"{path}: not a valid notebook ({exc})") from exc
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
    results, skipped, scanned = [], [], 0
    for f in iter_files(args.paths):
        scanned += 1
        try:
            findings = check_file(f)
        except UnreadableFile as exc:
            skipped.append(str(exc))
            continue
        results += [(str(f), x) for x in findings if select is None or x.rule in select]
    for msg in skipped:
        print(f"leakguard: SKIPPED {msg}", file=sys.stderr)
    if scanned == 0:
        print("leakguard: no .py or .ipynb files found in the given paths", file=sys.stderr)
    if args.format == "json":
        print(json.dumps([{"path": path, "line": f.line, "col": f.col + 1, "rule": f.rule, "message": f.message} for path, f in results], indent=2))
    else:
        for path, f in results:
            print(f.format(path))
        if results:
            print(f"\n{len(results)} potential leak(s) found.", file=sys.stderr)
    if skipped or scanned == 0:
        return 2  # could not check everything: never report success
    return 1 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())
