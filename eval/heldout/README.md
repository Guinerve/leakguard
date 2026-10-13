# Held-out leak corpus

Frozen before leakguard was run on it (see `docs/heldout-evaluation.md` for the protocol). `labels.json` records, for
every file, the label its source gives it, where that label comes from, and the file's SHA-256; `eval/run_heldout.py`
refuses to score a file whose hash has changed. Do not tune rules against these files: once a rule is written after
reading one of them, that file is in-sample and must be reported as such.

| Directory | Source | Licence |
|---|---|---|
| `ase22/` | `tests/inputs/` of [malusamayo/leakage-analysis](https://github.com/malusamayo/leakage-analysis) at `a7d038b`, the artifact of Yang et al., "Data Leakage in Notebooks: Static Detection and Better Processes", ASE 2022. Kaggle notebooks converted to Python, plus small test programs. Labels are the expected results in that repo's `tests/test_preprocessing.py` and `tests/test_overlap.py`. | MIT (repo); public Kaggle notebooks are Apache-2.0 |
| `sklearn/` | Two official scikit-learn examples at `bebaf70`: `plot_cyclical_feature_engineering.py`, `plot_time_series_lagged_features.py`. Time-series feature engineering evaluated with `TimeSeriesSplit`; labelled clean. | BSD-3-Clause |
| `marketcalls/` | Two code blocks from marketcalls.in, "Understanding Look-Ahead Bias and How to Avoid It in Trading Strategies": the article's leaky example and its walk-forward fix. Not vendored; `uv run python eval/fetch_marketcalls.py` downloads them and checks the hashes. | © the author; not redistributed |

The ASE'22 `nb_1215904.py` input has no expected result in either test file, so it is not included.
