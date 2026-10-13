"""Download the two marketcalls.in snippets of the held-out set (blog code, so not vendored) and verify their hashes.

    uv run python eval/fetch_marketcalls.py
"""
import hashlib
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

URL = "https://www.marketcalls.in/python/understanding-look-ahead-bias-and-how-to-avoid-it-in-trading-strategies.html"
HERE = Path(__file__).parent / "heldout"
BLOCKS = {1: "marketcalls/gmm_full_series.py", 2: "marketcalls/walk_forward.py"}  # <pre> index -> corpus file


def main() -> int:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    blocks = [html.unescape(re.sub(r"<[^>]+>", "", b)) for b in re.findall(r"<pre[^>]*>(.*?)</pre>", page, re.DOTALL)]
    expected = {c["file"]: c["sha256"] for c in json.loads((HERE / "labels.json").read_text())}
    ok = True
    for i, name in BLOCKS.items():
        out = HERE / name
        out.parent.mkdir(exist_ok=True)
        out.write_text(blocks[i])
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        if expected.get(name) and digest != expected[name]:
            print(f"{name}: page changed since the corpus was frozen (sha256 {digest})", file=sys.stderr)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
