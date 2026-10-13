# Recall on documented leaks (2026-10-13)

The larger, untouched set in `docs/heldout-evaluation.md` now gives the main result. This page is the earlier
check.

The false positive runs show only what `leakguard` reports too often. This check measures what it misses. It uses
leaks that other people documented and labelled as wrong, not examples that I wrote.

Sources: the scikit-learn "Common pitfalls" guide (the data leakage section) and the `temporalcv` failure case
examples 16 to 20 (https://temporalcv.readthedocs.io, `auto_examples_python.zip`). I read and linted the files. I
did not run them.

| Documented leak | Source | leakguard |
|---|---|---|
| Feature selection (`SelectKBest`) fitted before `train_test_split` | scikit-learn guide | **caught** (LG003) |
| Corrected versions (split first; Pipeline) | scikit-learn guide | clean (2 of 2, no false positive) |
| `KFold(shuffle=True)` on a time series | temporalcv 20 | **caught** (LG006, 2 sites) |
| `KFold(shuffle=True)` on financial returns | temporalcv 06 | **caught** (LG006) |
| `GridSearchCV(cv=KFold(shuffle=True))` on a time series | temporalcv 07 | **caught** (LG006) |
| Rolling features on the full series without a lag (`y.rolling(10).mean()` feeding a model for the next `y`) | temporalcv 16 | missed at first; **caught after I added LG008** (see below) |
| Classification threshold tuned on the full data, test rows included | temporalcv 17 | missed: no rule |
| No gap between train and test for a forecast horizon of several steps | temporalcv 19 | missed: no rule |
| Nested Diebold and Mariano test setup | temporalcv 18 | out of scope (a statistical procedure, not a code pattern) |

**Recall: 4 of 7 documented leaks (57 %) before LG008, and 5 of 7 (71 %) after.** The count leaves out the leak
that is out of scope. **The 71 % is in sample.** I wrote LG008 after I read example 16, so the 71 % shows that the
rule works on the case that caused it. It does not show better recall on leaks that leakguard has not seen. Only
the 57 % is an independent measurement. Seven is a small sample, so do not read 57 % as a stable estimate.

The misses are three kinds of leak that `leakguard` has no rule for. These are the possible rules, in order of how
easy they are to detect from the code alone:

1. ~~A rolling, expanding or ewm statistic of the target column, assigned to a feature with no `.shift(1)` before
   it.~~ Done as LG008. It fires on columns named y, target, label or y_true. A first version also matched
   `returns` and `close`. That was too aggressive and flagged normal feature engineering.
2. A threshold or cutoff calculated from `y` or from predictions over all rows (`np.percentile`,
   `precision_recall_curve`) before the split.
3. Gaps for the forecast horizon. These are detectable only if the horizon is a literal value near the cross
   validation call, so a rule would likely be a heuristic only.
