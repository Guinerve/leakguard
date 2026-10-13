# Changelog

## Unreleased

**Fixes**
- On Python 3.9 to 3.11, a file with a null byte (for example a UTF-16 file) crashed the scan. leakguard now
  reports it as SKIPPED with exit code 2.
- LG008 no longer flags `y.rolling(n).mean().shift(1)`. A lag after the statistic sees only past values.
- LG007 also finds `fillna(value=df.mean())` and `fillna(df["a"].mode()[0])`.
- A folder whose name ends in `.py` is now searched, not read as a file.
- Rule messages, `--help` text and the docs use plainer English.

## 0.2.0 (2026-10-13)

**Detection**
- LG003 and LG007 check every `train_test_split` in a scope, not only the first, and report each leak once,
  against the first split it feeds.
- Lineage tracks which value of a name reaches a split. A name rebound to a new dataset between a fit and a split
  no longer links them, and `X = f(X)` no longer drops X's earlier history.
- Imported module names (`np`, `pd`) are no longer treated as data lineage.

**Notebooks**
- `%time stmt` / `%timeit stmt` keep `stmt` (it used to be dropped silently).
- `!cmd`, `x = !cmd`, `obj?` and `!cmd \` continuations are handled line by line instead of blanking the cell.
- `%%time` / `%%capture` cells are checked; `%%bash`, `%%writefile` and other cells that are not Python are named on stderr.
- nbformat 3 is read.

**Reporting**
- Exit code 2 when anything was not checked: a notebook cell that cannot be parsed, a notebook that is not Python, a missing path.
- A clean run says on stderr that it is not proof that the code is free of leaks; the README and package description now present
  leakguard as a warning tool.

**Evaluation**
- Holdout evaluation on 42 labelled files (`docs/heldout-evaluation.md`): 10 of 32 documented leaks flagged in the
  protocol run, 11 after the lineage fix; 3 of 10 clean files flagged.

**Project**
- Examples (`examples/`), a README image generated from real output, CI on Python 3.9 and 3.13 with ruff, package
  metadata.

## 0.1.0 (2026-10-12; LG008 added 2026-10-13)

- First release: rules LG001 to LG008, CLI with text and JSON output, notebook support, inline suppression, flake8
  plugin and pre-commit hook.
