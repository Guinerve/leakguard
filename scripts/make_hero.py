"""Render real `leakguard check` output on the leaky example as docs/hero.svg (the README image).

    uv run python scripts/make_hero.py

The text in the image is whatever the CLI prints, wrapped to fit; nothing is typed in by hand.
"""

import re
import subprocess
import sys
import textwrap
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = "examples/leaky_forecast.py"
WIDTH_CHARS, CHAR_W, LINE_H, PAD = 88, 8.3, 19, 18
BG, FG, DIM, PROMPT, RULE, LOC = "#0f1419", "#d6dde4", "#7d8a96", "#7fd962", "#ffb454", "#59c2ff"


def run() -> tuple[list[str], int]:
    proc = subprocess.run([sys.executable, "-m", "leakguard.cli", "check", TARGET],
                          cwd=ROOT, capture_output=True, text=True, check=False)  # exit 1 is expected
    out = proc.stdout.splitlines() + [""] + [ln for ln in proc.stderr.splitlines() if ln.strip()]
    return out, proc.returncode


def styled(line: str) -> str:
    """One output line as SVG tspans: location in blue, rule ID in amber, message in the default colour."""
    m = re.match(r"^(\S+:\d+:\d+:)( LG\d{3})(.*)$", line)
    if not m:
        return escape(line)
    loc, rule, rest = m.groups()
    return (f'<tspan fill="{LOC}">{escape(loc)}</tspan><tspan fill="{RULE}" font-weight="700">{escape(rule)}</tspan>'
            f"{escape(rest)}")


def main() -> int:
    out, code = run()
    if code != 1:
        print(f"expected findings (exit 1) from {TARGET}, got exit {code}", file=sys.stderr)
        return 1
    rows: list[tuple[str, str]] = [("prompt", f"$ leakguard check {TARGET}"), ("plain", "")]
    for line in out:
        wrapped = textwrap.wrap(line, WIDTH_CHARS, subsequent_indent="    ") or [""]
        rows.append(("finding", wrapped[0]))
        rows += [("plain", w) for w in wrapped[1:]]
    rows += [("plain", ""), ("note", f"exit code {code}  (1 findings · 0 no known pattern, not proof · 2 not fully checked)")]

    width = int(PAD * 2 + WIDTH_CHARS * CHAR_W)
    height = int(PAD * 2 + 26 + len(rows) * LINE_H)
    body = []
    for i, (kind, text) in enumerate(rows):
        y = PAD + 26 + (i + 1) * LINE_H - 5
        if kind == "prompt":
            content = f'<tspan fill="{PROMPT}">{escape(text[:1])}</tspan>{escape(text[1:])}'
        elif kind == "note" or text.startswith("leakguard:") or "potential leak" in text:
            content = f'<tspan fill="{DIM}">{escape(text)}</tspan>'
        else:
            content = styled(text)
        body.append(f'<text x="{PAD}" y="{y}" xml:space="preserve">{content}</text>')
    dots = "".join(f'<circle cx="{PAD + 6 + 18 * k}" cy="{PAD + 4}" r="5.5" fill="{c}"/>'
                   for k, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="leakguard output on a deliberately leaky forecast: five findings">
<rect width="100%" height="100%" rx="10" fill="{BG}"/>
{dots}
<g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13" fill="{FG}">
{chr(10).join(body)}
</g>
</svg>
"""
    (ROOT / "docs" / "hero.svg").write_text(svg)
    print(f"wrote docs/hero.svg ({len(rows)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
