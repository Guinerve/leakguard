"""Run leakguard over the frozen held-out corpus and print raw findings per labelled case.

    uv run python eval/fetch_marketcalls.py   # once: the two blog snippets are not vendored
    uv run python eval/run_heldout.py [--json out.json]

This prints what leakguard reports. Whether a finding points at the documented leak was judged by reading each
file; that judgement and the totals are in docs/heldout-evaluation.md.
"""
import argparse
import hashlib
import io
import json
from contextlib import redirect_stderr
from pathlib import Path

from leakguard.cli import UnreadableFile, check_file

HERE = Path(__file__).parent / "heldout"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    rows = []
    for case in json.loads((HERE / "labels.json").read_text()):
        path = HERE / case["file"]
        row = {**case, "findings": [], "status": "checked"}
        if not path.exists():
            row["status"] = "missing (run eval/fetch_marketcalls.py)"
        elif hashlib.sha256(path.read_bytes()).hexdigest() != case["sha256"]:
            row["status"] = "hash mismatch: corpus file changed after it was frozen"
        else:
            incomplete: list[str] = []
            notes = io.StringIO()
            try:
                with redirect_stderr(notes):
                    row["findings"] = [{"line": f.line, "rule": f.rule, "message": f.message} for f in check_file(path, incomplete)]
                if incomplete:
                    row["status"] = "incomplete: " + "; ".join(incomplete)
            except UnreadableFile as exc:
                row["status"] = f"could not check: {exc}"
        rows.append(row)
        rules = ",".join(f"{f['rule']}@{f['line']}" for f in row["findings"]) or "-"
        print(f"{case['label']:5}  {case['leak_type'] or '':16}  {case['file']:62}  {rules}"
              + ("" if row["status"] == "checked" else f"  [{row['status']}]"))
    counts = {label: (sum(1 for r in rows if r["label"] == label and r["findings"]), sum(1 for r in rows if r["label"] == label))
              for label in ("leaky", "clean")}
    print("\nfiles with >=1 finding: " + ", ".join(f"{k} {f}/{t}" for k, (f, t) in counts.items())
          + "  (raw; not yet checked against the documented leak)")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
