# Held-out evaluation (2026-10-13)

`docs/recall-on-documented-leaks.md` measured recall on 7 leaks, and I then wrote LG008 after reading one of them, so
that set is no longer independent. This is a second set nobody tuned leakguard against: 42 labelled files from
three sources leakguard had never been run on (corpus and licences: `eval/heldout/README.md`).

## Protocol (written before the first run)

1. **Corpus frozen first.** Files and labels were collected, hashed into `eval/heldout/labels.json`, and this
   protocol was written before leakguard was run on any of them. Labels come from the sources, not from me: the
   ASE'22 authors' expected results (`test_preprocessing.py`, `test_overlap.py`), the article's own "this is the
   look-ahead bias" / "walk-forward fix" framing, and scikit-learn's official examples taken as clean.
2. **One run, no tuning.** The rules are the ones in the working tree at the time of the run (after the
   multi-split and notebook fixes, which were built and tested on my own fixtures). No rule is changed because of
   what this corpus shows. A rule written later because of something seen here makes that file in-sample, and it
   must be reported that way. (One deviation, reported below: a lineage bug found afterwards on the *development*
   notebooks was fixed and the held-out set re-run; both runs are given.)
3. **Unit: one file.** A leaky file counts as **caught** only if at least one finding points at the documented
   leak (the fit or statistic whose output reaches the evaluation data, the resampling before the split, the fit on
   the full series). A finding somewhere else in a leaky file does not count as catching it.
4. **Clean files.** Any finding in a clean file is a **false positive** by label. If reading the code shows the
   finding is a real problem the label missed, it is still counted as a false positive here, and noted.
5. **Extra findings** in leaky files that don't point at the documented leak are listed and judged by reading.
   ASE'22 files labelled only for overlap leakage have no preprocessing label, so findings there are judged by
   reading and kept out of the totals.
6. A file leakguard cannot parse counts as **missed**.

Reproduce: `uv run python eval/fetch_marketcalls.py && uv run python eval/run_heldout.py`.

## Results

42 files: 32 leaky (27 preprocessing, 4 overlap/oversampling, 1 fit-on-the-full-series), 10 clean.

| | Run 1 (protocol run) | Run 2 (after the lineage fix) |
|---|---|---|
| Leaky files caught | **10 / 32 (31 %)** | **11 / 32 (34 %)** |
| of which preprocessing leaks | 10 / 27 (one only partly) | 11 / 27 |
| of which overlap / oversampling leaks | 0 / 4 | 0 / 4 |
| of which fit on the full series (marketcalls) | 0 / 1 | 0 / 1 |
| Clean files with a finding (by label) | 3 / 10 | 3 / 10 |
| ...that are false alarms on reading | 2 / 10 | 2 / 10 |
| Findings outside the overlap-only files that point at a real leak | — | 13 / 20 |

**Read this as: leakguard flagged about one documented leak in three.** Most leaks in real notebooks are of kinds
it has no rule for, or sit in code it cannot follow (see "Missed"). Forty-two files is a small sample; the
interval around 34 % is wide (20-52 % at 95 %, Wilson; 18-49 % for run 1).

**Run 2.** After run 1, re-running the 164 development notebooks (`ageron/handson-ml3`, `jakevdp/PythonDataScienceHandbook`)
showed that the multi-split change had a false positive: `X` scaled for one demo, then rebound to a new dataset
before a later split (handson-ml3 ch. 5). Lineage now tracks which *binding* of a name reaches a split, not just
the name. That fix also repaired an older bug (rebinding a name from itself, `X = f(X)`, dropped the earlier
lineage), and run 2 differs from run 1 in four files: `nb_282393` newly caught, `nb_344873` now fully caught,
three wrong LabelEncoder findings in `nb_362989` and two in the fraud notebook gone. The fix was motivated by a
development notebook, not by a held-out file, but I had seen run 1 when I made it, so run 1 is the clean number.

**What the fixes in this round contributed.** Checking every split, not only the first, caught 2 of the 11
(`nb_205857`, PCA before a second split; `nb_248151`, a scaler before a third) and added 1 false positive. The
notebook fixes do not show here (the corpus is `.py`). On the 164 development notebooks: 69 statements behind
`%time` / `%timeit` that used to be dropped without notice are now checked; of the 8 cells previously skipped, 6 are
now checked or named as non-Python (`%%bash`, `%%writefile`), and 2 (deliberately invalid Python in the PDSH book)
are reported as INCOMPLETE with exit code 2 instead of exit 0; findings are unchanged.

### Caught (run 2)

| File | Finding | Documented leak |
|---|---|---|
| `test0` | LG007 | `fillna(np.mean(df['Fare']))` before the split |
| `nb_100841` | LG003 | `CountVectorizer` fitted on all text before the split (the `TfidfTransformer` after it is not flagged: not in the class list) |
| `nb_334422` | LG003 | text vectoriser fitted before the split |
| `nb_344873` | LG007, LG003 | `fillna(all_data.mean())` on train + test; scaler fitted before a validation split |
| `nb_194503` | LG003 | `StandardScaler` on all of `X` |
| `nb_205857` | LG003 | PCA on all rows before the second split |
| `nb_387986` | LG003 | `SelectKBest`-style selection fitted on all rows (the `Imputer` fits before it are missed: old class name) |
| `nb_175471` | LG003 | scaler fitted on train + test in a loop |
| `nb_248151` | LG003 | scaler before the third split in one scope |
| `nb_292583` | LG003 | `MinMaxScaler` on all rows |
| `nb_282393` | LG003 | scaler on train + test reaching a validation split (run 2 only) |

### Missed (run 2), by cause

21 files; `nb_424904` appears under two causes.

| Cause | Files |
|---|---|
| No rule: resampling (SMOTE, under/over-sampling) before the split | `testOversampler`, `yogmoh_news-category`, `dktalaicha_…smote-adasyn`, `shahules_tackling-class-imbalance` |
| No rule: statistic computed after the split from the wrong rows (test mean for the test set; full-data mean for the train set) | `test1`, `test2` |
| No rule: quantile binning (`pd.qcut`) or manual `(x - mean) / std` on all rows | `nb_1090319`, `nb_1255091`, `nb_1080148` |
| No rule: no held-out data at all (model fitted and evaluated on the full series) | `marketcalls/gmm_full_series` |
| Split is not `train_test_split` (positional slicing `data[:n]`, `torch.random_split`) | `titanic0`, `nb_504` |
| Fit and split in different functions / class methods | `nb_303674`, `nb_481597`, `nb_362989` (scaler inside a function passed to `.apply`), `nb_424904` |
| Transformer class not in the list (`Imputer`, `DataFrameMapper`, `DictVectorizer`, a `Pipeline` used as a transformer) | `nb_132929`, `nb_276778`, `nb_424904` |
| Leak into cross-validation folds (fit on all of `X_train`, then CV) | `nb_471253`, `nb_273933`, `nb_344814` |

### False positives and other findings

| File (label) | Finding | Verdict |
|---|---|---|
| `nb_473437` (clean) | LG006 | false positive: bike-trip records with time columns, but the task is not forecasting |
| `nb_277256` (clean) | LG003 `LabelEncoder` | data flow is right (the encoded columns reach the split), but a LabelEncoder learns only the category list; the source labels it clean |
| `sklearn/plot_time_series_lagged_features` (clean) | LG006 | **real**: the example's own "Naive evaluation" section, which scikit-learn presents as the wrong way before showing `TimeSeriesSplit`. My file-level "clean" label was wrong |
| `nb_282393`, `nb_273933` (leaky) | LG006 | false positive: the file "looks like time series" only because of `import time` / `from datetime import datetime` used for timing |
| `nb_344814` (leaky) | LG006 | false positive: a salary-unit dict containing `'month'`, `'year'` |
| `nb_471253` (leaky) | LG003 | false positive: PCA fitted on data that is later split, but its output only feeds a plot |
| `nb_276778` (leaky) | LG003 `LabelEncoder` | as for `nb_277256`; the documented leak is the imputing Pipeline, which is missed |
| `yogmoh_news-category` (overlap only) | LG003 ×2 | real: vectorisers fitted on all text before the split (no preprocessing label in the source) |
| `dktalaicha_…` (overlap only) | LG003 ×1, LG006 ×10 | LG003 false positive (PCA for a scatter plot); LG006 on random splits of a fraud dataset whose time columns are dropped from `X`: arguable, not a leak the source names |

**Where the false positives come from.** LG006 produced 15 findings and only one is a real issue. Its
"this file is time-series" test fires on timing code and date-unit words, and for `KFold`/`ShuffleSplit` it
still uses the whole-file signal. LG003 flags a fit whose *input* is later split even when the fit's output is
never used by a model (two cases, both plots).

## What this says about using leakguard

leakguard is a warning tool. A finding is a prompt to look at the code. **A clean run is not evidence that the
data or the evaluation is leak-free**: on this corpus it stayed silent on 21 of 32 documented leaks, including every
resampling leak and every leak that crosses a function boundary.

Candidate improvements, in the order this corpus suggests, each to be judged on a *new* held-out set because these
files are now in-sample for them: a resample-before-split rule (4 misses); LG006 using only the split data's own
lineage for `KFold`/`ShuffleSplit` and ignoring `import time` (≈13 false positives); fitted-statistic-after-split
for `fillna` (2 misses); `pd.qcut` / manual standardisation before a split (3 misses); positional slicing as a split.
