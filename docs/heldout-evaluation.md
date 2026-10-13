# Holdout evaluation (2026-10-13)

`docs/recall-on-documented-leaks.md` measured recall on 7 leaks. I then wrote LG008 after I read one of them, so
that set is no longer independent. This report uses a second set that nobody tuned leakguard against: 42 labelled
files from three sources that leakguard had never seen. The corpus and its licences are in `eval/heldout/README.md`.

## Protocol (written before the first run)

1. **Freeze the corpus first.** I collected the files and labels, hashed them into `eval/heldout/labels.json` and
   wrote this protocol before I ran leakguard on any of them. The labels come from the sources, not from me:
   - the ASE'22 authors' expected results (`test_preprocessing.py`, `test_overlap.py`);
   - the article's own description of its code as the look ahead bias and the walk forward fix;
   - the official scikit-learn examples, taken as clean.
2. **Run once, with no tuning.** The rules are the ones in the working tree at the time of the run. That tree
   already had the multi split and notebook fixes, which I built and tested on my own fixtures. No rule changes
   because of what this corpus shows. If I write a rule later because of something I saw here, that file is in
   sample, and I must report it that way. There is one deviation, reported below. I found a lineage bug afterwards
   on the *development* notebooks, fixed it and ran the holdout set again. Both runs are given.
3. **Count by file.** A leaky file counts as **caught** only if at least one finding points at the documented leak.
   The documented leak is the fit or statistic whose output reaches the evaluation data, the resampling before the
   split, or the fit on the full series. A finding somewhere else in a leaky file does not count.
4. **Clean files.** Any finding in a clean file is a **false positive** by label. If the code shows that the finding
   is a real problem that the label missed, it still counts as a false positive here, with a note.
5. **Extra findings** in leaky files that do not point at the documented leak are listed and judged by reading the
   code. Some ASE'22 files have a label only for overlap leakage and no preprocessing label. I judged the findings
   in those files by reading and kept them out of the totals.
6. A file that leakguard cannot parse counts as **missed**.

To reproduce: `uv run python eval/fetch_marketcalls.py && uv run python eval/run_heldout.py`.

## Results

42 files: 32 leaky (27 preprocessing, 4 overlap or oversampling, 1 fit on the full series) and 10 clean.

| | Run 1 (protocol run) | Run 2 (after the lineage fix) |
|---|---|---|
| Leaky files caught | **10 / 32 (31 %)** | **11 / 32 (34 %)** |
| of which preprocessing leaks | 10 / 27 (one only in part) | 11 / 27 |
| of which overlap or oversampling leaks | 0 / 4 | 0 / 4 |
| of which fit on the full series (marketcalls) | 0 / 1 | 0 / 1 |
| Clean files with a finding (by label) | 3 / 10 | 3 / 10 |
| of which false alarms after reading the code | 2 / 10 | 2 / 10 |
| Findings outside the overlap only files that point at a real leak | not counted | 13 / 20 |

**In short, leakguard flagged about one documented leak in three.** Most leaks in real notebooks are of kinds that
it has no rule for, or they sit in code that it cannot follow (see "Missed"). 42 files is a small sample, so the
interval around 34 % is wide: 20 % to 52 % at 95 % (Wilson). For run 1 it is 18 % to 49 %.

**Run 2.** After run 1, I ran leakguard again on the 164 development notebooks (`ageron/handson-ml3` and
`jakevdp/PythonDataScienceHandbook`, including its older `notebooks_v1` folder). This showed a false positive from
the multi split change. In handson-ml3 chapter 5, `X` is scaled for one demo, then bound to a new dataset before a
later split. Lineage now tracks which *binding* of a name reaches a split, not only the name. That fix also
repaired an older bug: when a name was bound again from itself (`X = f(X)`), the earlier lineage was lost.

Run 2 differs from run 1 in four files:

- `nb_282393` is newly caught.
- `nb_344873` is now fully caught.
- Three wrong LabelEncoder findings in `nb_362989` are gone.
- Two wrong LabelEncoder findings in the fraud notebook are gone.

A development notebook caused the fix, not a holdout file. But I had seen run 1 when I made it, so run 1 is the
clean number.

**What the fixes in this round added.** When leakguard checks every split, not only the first, it catches 2 of
the 11: `nb_205857` (PCA before a second split) and `nb_248151` (a scaler before a third split). This change also
added 1 false positive. The notebook fixes do not show here, because the corpus is `.py` files. On the 164
development notebooks, the fixes had these results:

- 69 statements behind `%time` or `%timeit` are now checked. Before, leakguard dropped them and gave no notice.
- Of the 8 cells that leakguard skipped before, 6 are now checked or named as not Python (`%%bash`, `%%writefile`).
- The other 2 cells are invalid Python on purpose in the PDSH book. leakguard now reports them as INCOMPLETE with
  exit code 2, not exit code 0.
- The findings did not change.

### Caught (run 2)

| File | Finding | Documented leak |
|---|---|---|
| `test0` | LG007 | `fillna(np.mean(df['Fare']))` before the split |
| `nb_100841` | LG003 | `CountVectorizer` fitted on all text before the split (the `TfidfTransformer` after it is not flagged, because it is not in the class list) |
| `nb_334422` | LG003 | text vectoriser fitted before the split |
| `nb_344873` | LG007, LG003 | `fillna(all_data.mean())` on train and test; scaler fitted before a validation split |
| `nb_194503` | LG003 | `StandardScaler` on all of `X` |
| `nb_205857` | LG003 | PCA on all rows before the second split |
| `nb_387986` | LG003 | feature selection like `SelectKBest` fitted on all rows (the `Imputer` fits before it are missed, because `Imputer` is an old class name) |
| `nb_175471` | LG003 | scaler fitted on train and test in a loop |
| `nb_248151` | LG003 | scaler before the third split in one scope |
| `nb_292583` | LG003 | `MinMaxScaler` on all rows |
| `nb_282393` | LG003 | scaler on train and test that reaches a validation split (run 2 only) |

### Missed (run 2), by cause

21 files. `nb_424904` is in two rows.

| Cause | Files |
|---|---|
| No rule: resampling (SMOTE, under sampling or over sampling) before the split | `testOversampler`, `yogmoh_news-category`, `dktalaicha_…smote-adasyn`, `shahules_tackling-class-imbalance` |
| No rule: statistic calculated after the split from the wrong rows (test mean for the test set; mean of all data for the train set) | `test1`, `test2` |
| No rule: quantile binning (`pd.qcut`) or manual `(x - mean) / std` on all rows | `nb_1090319`, `nb_1255091`, `nb_1080148` |
| No rule: no test data at all (the model is fitted and evaluated on the full series) | `marketcalls/gmm_full_series` |
| The split is not `train_test_split` (positional slicing `data[:n]`, `torch.random_split`) | `titanic0`, `nb_504` |
| Fit and split in different functions or class methods | `nb_303674`, `nb_481597`, `nb_362989` (scaler inside a function passed to `.apply`), `nb_424904` |
| Transformer class not in the list (`Imputer`, `DataFrameMapper`, `DictVectorizer`, a `Pipeline` used as a transformer) | `nb_132929`, `nb_276778`, `nb_424904` |
| Leak into cross validation folds (fit on all of `X_train`, then cross validation) | `nb_471253`, `nb_273933`, `nb_344814` |

### False positives and other findings

| File (label) | Finding | Verdict |
|---|---|---|
| `nb_473437` (clean) | LG006 | False positive. Bike trip records with time columns, but the task is not forecasting |
| `nb_277256` (clean) | LG003 `LabelEncoder` | The data flow is correct (the encoded columns reach the split), but a LabelEncoder learns only the list of categories. The source labels it clean |
| `sklearn/plot_time_series_lagged_features` (clean) | LG006 | **Real.** It is the example's own "Naive evaluation" section, which scikit-learn shows as the wrong way before it shows `TimeSeriesSplit`. My "clean" label for the whole file was wrong |
| `nb_282393`, `nb_273933` (leaky) | LG006 | False positive. The file "looks like a time series" only because of `import time` and `from datetime import datetime`, used for timing |
| `nb_344814` (leaky) | LG006 | False positive. A dict of salary units contains `'month'` and `'year'` |
| `nb_471253` (leaky) | LG003 | False positive. PCA is fitted on data that is later split, but its output only feeds a plot |
| `nb_276778` (leaky) | LG003 `LabelEncoder` | The same as `nb_277256`. The documented leak is the imputing Pipeline, which leakguard misses |
| `yogmoh_news-category` (overlap only) | LG003 ×2 | Real. Vectorisers fitted on all text before the split (the source has no preprocessing label) |
| `dktalaicha_…` (overlap only) | LG003 ×1, LG006 ×10 | The LG003 finding is a false positive (PCA for a scatter plot). The LG006 findings are on random splits of a fraud dataset whose time columns are dropped from `X`. They are arguable, and the source does not name them as a leak |

**Where the false positives come from.** LG006 gave 15 findings, and only one is a real issue. Its test for
"this file is a time series" fires on timing code and on words for date units. For `KFold` and `ShuffleSplit`, it
still uses signs from the whole file. LG003 flags a fit whose *input* is later split, even when no model uses the
fit's output. There were two such cases, and both were plots.

## What this means for leakguard users

leakguard is a warning tool. A finding tells you which code to read. **A clean run is not evidence that the data
or the evaluation is free of leaks.** On this corpus, leakguard was silent on 21 of 32 documented leaks. These
include every resampling leak and every leak that crosses a function boundary.

These are the next improvements, in the order that this corpus suggests. Each one must be judged on a *new*
holdout set, because these files are now in sample for them.

1. A rule for resampling before the split (4 misses).
2. LG006 that uses only the lineage of the split data for `KFold` and `ShuffleSplit`, and ignores `import time`
   (about 13 false positives).
3. A rule for fitted statistics after the split for `fillna` (2 misses).
4. A rule for `pd.qcut` and manual standardisation before a split (3 misses).
5. Positional slicing as a split.
