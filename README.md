# leakguard

> A linter that warns about common lookahead-bias and data-leakage patterns in pandas and scikit-learn code.

**It is a warning tool, not a proof of clean data.** A finding is a prompt to read the code; a clean run means only
that none of the patterns below was recognised. On a held-out set of 32 documented leaks it flagged 11 (34 %) and
stayed silent on the rest: see [the evaluation](docs/heldout-evaluation.md).

**Status:** v0.1 core built: 8 rules, CLI, notebooks, flake8 plugin, pre-commit hook · Portfolio project #4 · see `../README.md`

## The idea

Data leakage silently produces backtests and models that look great and are wrong. There is no good linter for it, so build one.

## Stack

Python (uv), `ast`, pytest; ships as a CLI, a pre-commit hook and a flake8 plugin.

Python project managed with `uv`; target a one-command run (`uv run ...`).

## Build plan (v1)

- [x] AST checker with rule IDs, messages and line/column reporting with rule IDs, messages and line/column reporting
- [x] Rules (7 so far):
  - [x] `LG001` `.shift(-n)` (skipped when assigned to a target-like name)
  - [x] `LG002` `rolling(..., center=True)`
  - [x] `LG003` `fit`/`fit_transform` on a scaler, encoder, imputer, PCA or selector **before the train/test split that its data feeds** (follows data lineage; every split in a scope is checked)
  - [x] `LG004` `bfill()` / `backfill()` / `fillna(method="bfill")` / `interpolate()`
  - [x] `LG005` `merge_asof(direction="forward" | "nearest")`
  - [x] `LG006` random `KFold` / `train_test_split` on time-ordered data (only when the file shows time-series signals)
  - [x] `LG007` `fillna(df.mean())` before the split it feeds
  - [x] `LG008` rolling/expanding/ewm statistic of the target column without a prior `.shift(1)`
- [x] Inline suppression comments (`# leakguard: ignore[LG003]`)
- [x] CLI, `.pre-commit-hooks.yaml`, flake8 entry point (plugin class unit-tested; not yet run under a real flake8)
- [x] Run against public notebooks (95; results below)

## Run it

```bash
uv sync
uv run leakguard check path/to/code_or_notebooks
uv run leakguard rules
uv run pytest -q      # 35 tests
```

Suppress a line with `# leakguard: ignore[LG003]` (or `# leakguard: ignore`).

Exit codes: `0` no known pattern found (stderr says this is not proof of leak-free code), `1` findings, `2` something
was not checked: an unreadable file, a non-Python notebook, or a notebook cell that is not valid Python. Findings
from the parts that were checked are still printed. In notebooks, `%time stmt` / `%timeit stmt` keep `stmt`, `!cmd`,
`x = !cmd` and `obj?` are neutralised line by line, `%%time` / `%%capture` cells are checked, and `%%bash`,
`%%writefile` and other non-Python cells are named on stderr. nbformat 3 and 4 are read.

As a pre-commit hook, exit code 2 blocks the commit, so a notebook with a cell that is not valid Python (or a
non-Python notebook) now fails the hook where it used to pass silently. Fix the cell, or keep the file out of the
hook with pre-commit's `exclude:`.

## How I know it's right

**Fixtures**: one file per rule (`tests/fixtures/`), every flagged line marked `# expect: LGxxx`, and the test asserts the set of findings equals the set of markers exactly (no missing, no extra). The false-positive cases below were added as regression fixtures.

**Public-notebook run**: the 95 notebooks in `ageron/handson-ml3` and `jakevdp/PythonDataScienceHandbook`. Final result: **9 findings in 4 notebooks, 0 of them real leakage into a model.** All are teaching or plotting demos of the exact pattern the rule looks for (`bfill` on a toy Series, centred rolling means drawn on a chart, `shift(-365)` to plot, `DatetimeIndex.shift(-1)` to iterate days, `interpolate()` on a small frame). So the patterns are detected correctly, but LG001/LG002/LG004 cannot tell a chart from a feature, and these textbook notebooks were never expected to leak. 7 cells in 4 notebooks (shell cells, `%%bash`, odd syntax) are not plain Python and are reported as not checked; they are not counted as clean.

The runs drove fixes to **false positives**: `date` matched inside words like `update` (LG006); a scaler on toy data, a reused variable name and a stateless `PolynomialFeatures` (LG003); an `X_train` name reused across unrelated examples in one notebook (LG003; lineage is now flow-sensitive); tabular splits flagged because time handling appeared elsewhere in the file (LG006 now needs the split data's own lineage to be time-related); `StratifiedKFold` (dropped from LG006). A code review also found and I fixed: unparseable files and notebooks were silently reported clean (now exit 2 with a message), `../project` or dot-directory paths scanned nothing, a mistyped `--select` hid everything, `interpolate(limit_direction="forward")` was wrongly exempt, and an operator-precedence bug in LG007. Each is a regression test.

**Held-out evaluation** (`docs/heldout-evaluation.md`, reproducible with `eval/run_heldout.py`): 42 labelled files
that leakguard had never been run on, frozen with their labels before the first run: the test notebooks of the
ASE'22 leakage-analysis tool (Kaggle notebooks with the authors' expected results), two scikit-learn time-series
examples, and a look-ahead-bias article's leaky and fixed code. **Caught 10 of 32 documented leaks (31 %) in the
protocol run, 11 (34 %) after a lineage bug found on the development notebooks was fixed; flagged 3 of 10 clean
files, 2 of them false alarms.** Every resampling-before-split leak, every leak that crosses a function boundary
and every leak into cross-validation folds was missed. LG006 is the noisiest rule: 15 findings, 1 real.

**Earlier recall check**, measured on leaks other people documented (scikit-learn's pitfalls guide, the `temporalcv` failure cases; `docs/recall-on-documented-leaks.md`): **4 of 7 caught (57 %)** before I added rule LG008, **5 of 7 after (in-sample: I wrote that rule after reading the missed example)**. Seven is a small sample. Still missed: a classification threshold tuned on the full data and train/test gaps for multi-step forecasts.

## Limits

Rules LG001, LG002, LG004 are pattern matches and will flag legitimate uses (targets, plots, non-temporal data); LG006 depends on a heuristic for "this file is time-series". LG003/LG007 only see leaks inside one function or module scope, only for the transformer classes in a fixed list, and only for `train_test_split` (not positional slicing, not cross-validation folds). LG006's time-series test fires on timing code (`import time`) and date words in strings. There is no rule for resampling (SMOTE etc.) before a split, `pd.qcut` or manual standardisation on all rows, statistics computed after the split from the wrong rows, or models evaluated on their training data.

Static analysis can't see runtime data, so some rules are heuristics. Document which rules can false-positive and why.

## Next (tomorrow)

- Grow the documented-leak corpus well beyond 7 examples (Kaggle write-ups, the Kapoor & Narayanan leakage survey) to get a stable recall estimate; add rules for threshold-on-full-data and horizon gaps.
- Rules to add: target encoding before split, `groupby().transform()` on the full frame, `cross_val_score` on pre-transformed data, `pd.get_dummies` before split.
- README hero: terminal output on a deliberately leaky example.

## Stretch

Notebook (`.ipynb`) support, Ruff plugin, auto-fix suggestions.

## Definition of done

- [ ] Hero GIF or screenshot at the top of this README
- [x] Live demo link or one-command run (`uv run leakguard check .`)
- [ ] "How I know it's right" section filled in with real results
- [ ] Tests passing in CI, badge added
- [ ] "Limits" section written
- [ ] Licence chosen, repo description and topics set
- [ ] Pinned on GitHub profile and added to guinerve.github.io
- [ ] Added to `career-radar/data/cv/portfolio.json`
