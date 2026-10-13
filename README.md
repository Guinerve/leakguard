# leakguard

[![CI](https://github.com/Guinerve/leakguard/actions/workflows/ci.yml/badge.svg)](https://github.com/Guinerve/leakguard/actions/workflows/ci.yml)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A linter that warns about lookahead bias and data leakage in pandas and scikit-learn code.

![leakguard output on a leaky next day sales forecast: five findings, each with a file, line, rule ID and fix](docs/hero.svg)

> [!IMPORTANT]
> **leakguard is a warning tool, not proof of clean data.** A finding tells you which line to read. A clean run
> means only that leakguard found none of its 8 patterns. On a holdout set of 32 documented leaks, it flagged 11
> (34 %) and missed the other 21 ([evaluation](docs/heldout-evaluation.md)).

Data leakage gives you a backtest or a model score that looks good and is wrong. Nothing crashes to tell you.
The usual causes are small: a scaler fitted before the split, a centred rolling mean, a backward fill. They are
easy to miss in review. I built leakguard to point at those lines automatically, the way a style linter points at
style. It reads your code with Python's `ast` module. It never runs the code and never sees your data.

## Quick start

Install it as a tool, then check a file, a folder or a notebook:

```bash
uv tool install git+https://github.com/Guinerve/leakguard
leakguard check path/to/code_or_notebooks
```

With pip, use `pip install git+https://github.com/Guinerve/leakguard`. Two more examples:

```bash
leakguard check src/ --select LG003,LG007 --format json
leakguard rules
```

To try it from a clone:

```bash
git clone https://github.com/Guinerve/leakguard
cd leakguard
uv run leakguard check examples/
```

This checks the leaky forecast in the image above and its corrected version, `examples/fixed_forecast.py`. The
corrected file gives no findings.

## What it flags

| Rule | Pattern | Can also flag (by design) |
|---|---|---|
| `LG001` | `.shift(-n)` that feeds a feature | Plots. Not reported when the result goes to a target name (`target`, `y`, `future`, ...) |
| `LG002` | `rolling(..., center=True)` | Smoothing of data that is not ordered in time (images, maps) |
| `LG003` | `fit` or `fit_transform` of a scaler, encoder, imputer, PCA or selector on rows that a later `train_test_split` puts in the test set | Fits whose output only feeds a plot. `LabelEncoder`, which learns only the list of categories |
| `LG004` | `bfill()`, `backfill()`, `fillna(method="bfill")`, `interpolate()` | Data that is not ordered in time |
| `LG005` | `merge_asof(direction="forward" \| "nearest")` | Alignment to a known later event on purpose |
| `LG006` | Shuffled `KFold`, `ShuffleSplit` or `train_test_split` on data ordered in time | Files that only *look* like time series (`import time`, date words). This is the noisiest rule |
| `LG007` | `fillna(df.mean())` (or median or mode) on rows that a later split puts in the test set | |
| `LG008` | `rolling`, `expanding` or `ewm` statistic of the target column with no `.shift(1)` before or after it | Features that predict a different, later quantity |

`leakguard rules` prints the same list.

## How it works

leakguard parses each file into a syntax tree and walks it. Most rules match one call, for example `.shift(-1)` or
`rolling(center=True)`. LG003 and LG007 follow the data inside one function or module. For each `train_test_split`,
they trace assignments back to find the earlier fits and fills that feed it. They also track which value of a
reused name (`X`, `X_train`) reaches each split. LG006 looks for signs of a time series (datetime parsing, `shift`,
`rolling`, date column names) in the data that reaches the split.

## Integrations

**pre-commit**

```yaml
repos:
  - repo: https://github.com/Guinerve/leakguard
    rev: v0.2.0
    hooks:
      - id: leakguard
```

**flake8.** Install leakguard in the same environment as flake8. flake8 then reports the `LG` codes
(`flake8 --select LG`).

**Suppress a finding** after you review it. Add `# leakguard: ignore[LG003]` to the line, or
`# leakguard: ignore` for all rules.

**Exit codes**

- `0`: no known pattern found. The message on stderr says that this is not proof.
- `1`: one or more findings.
- `2`: some code was not checked. Examples: a file leakguard cannot read, a notebook that is not Python, or a
  notebook cell that is not valid Python.

With exit code 2, leakguard still prints the findings from the parts it checked. A pre-commit run fails on 2. Fix
the cell, or keep the file out of the hook with the pre-commit `exclude:` option.

**Notebooks.** leakguard reads `.ipynb` files in nbformat 3 and 4. It checks all code cells together as one scope,
in the order they run. Line numbers count through the code cells joined together.

- `%time stmt` and `%timeit stmt`: leakguard checks `stmt`.
- `!cmd`, `x = !cmd` and `obj?`: leakguard replaces only that line and checks the rest of the cell.
- `%%time` and `%%capture` cells: checked.
- `%%bash`, `%%writefile` and other cells that are not Python: named on stderr and not checked.

## Results

| Check | Result |
|---|---|
| **Holdout leaks** ([report](docs/heldout-evaluation.md)): 42 labelled files that leakguard had never seen, frozen before the first run | **10 of 32 documented leaks flagged (31 %)** in the protocol run. 11 of 32 (34 %) after a lineage fix. 3 of 10 clean files flagged, 2 of them false alarms |
| **Public notebooks**: the 95 notebooks in `ageron/handson-ml3` and `jakevdp/PythonDataScienceHandbook` | 9 findings in 4 notebooks. None of them is leakage into a model. They are textbook demos of the same patterns (`bfill` on a small example Series, centred rolling means for a chart) |
| **Rule fixtures** (`tests/fixtures/`) | Each line that must be flagged has a `# expect: LGxxx` marker. The test requires the findings to match the markers exactly |
| **Earlier recall check** ([notes](docs/recall-on-documented-leaks.md)): the scikit-learn pitfalls guide and `temporalcv` failure cases | 4 of 7 (57 %) before LG008 existed. 5 of 7 after, but that result is in sample |

The holdout files come from these sources:

- Kaggle notebooks from the ASE'22 paper on leakage in notebooks, labelled by the authors' expected results.
- Two official scikit-learn time series examples.
- The leaky code and the fixed code from an article about lookahead bias.

leakguard missed 21 leaky files. One file has two causes:

- resampling (SMOTE and similar) before the split: 4
- fit and split in different functions: 4
- leaks into cross validation folds: 3
- transformer classes that are not in the list: 3
- `pd.qcut` or manual standardisation: 3
- statistics calculated after the split from the wrong rows: 2
- splits made by slicing, not `train_test_split`: 2
- a model evaluated on its own training data: 1

The sample is small: 42 files. The 95 % confidence interval around 34 % runs from 20 % to 52 %.

On the public notebooks, leakguard names 10 cells in 4 notebooks as not Python (`%%bash`, `%%file`,
`%%writefile`). It reports 1 cell as not checked (exit code 2). The book makes that cell invalid Python on purpose.

Each false positive I found became a regression fixture. Examples: `date` matched inside `update` (LG006); toy data,
reused names and the stateless `PolynomialFeatures` (LG003); a name bound to a new dataset between the fit and the
split; files reported clean when leakguard could not parse them. The git history has the full list.

## Limits

- Static analysis cannot see the data. LG001, LG002 and LG004 match patterns, so they cannot tell a chart from a
  feature.
- LG006 guesses whether a file is a time series, and it often guesses wrong. On the holdout set it gave 15
  findings, and 1 was real.
- LG003 and LG007 see one function or module at a time. They know only a fixed list of transformer classes, and
  only `train_test_split` as a split. They do not see positional slicing or cross validation folds. They ignore
  control flow.
- There is no rule yet for resampling before a split, `pd.qcut` or manual standardisation on all rows, statistics
  calculated after the split from the wrong rows, models evaluated on their training data, thresholds tuned on the
  full data, or forecast horizon gaps.

## Development

```bash
uv sync
uv run pytest -q                                  # 38 tests
uv run ruff check src tests eval scripts examples
uv run python eval/fetch_marketcalls.py           # download the two blog snippets in the holdout set
uv run python eval/run_heldout.py                 # print the raw findings on the holdout set
uv run python scripts/make_hero.py                # make docs/hero.svg again from real output
```

CI runs the tests and the linter on Python 3.9 and 3.13. It fails if `docs/hero.svg` no longer matches the real
output. The holdout files are now in sample for any rule written after I read them. A new rule needs a new test
set (see the last section of the report).

## Roadmap

In the order that the holdout set suggests:

1. A rule for resampling (SMOTE and similar) before a split.
2. LG006 that uses only the lineage of the split data and ignores timing code.
3. A rule for statistics calculated after the split from the wrong rows.
4. `pd.qcut` and manual standardisation before a split. Positional slicing and cross validation calls as split
   points.

## Licence

MIT, see [LICENSE](LICENSE). The holdout corpus keeps its own licences (`eval/heldout/README.md`).
