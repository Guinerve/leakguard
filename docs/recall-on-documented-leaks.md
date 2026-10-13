# Recall on documented leaks (2026-10-13)

Superseded as the headline number by the larger, untouched set in `docs/heldout-evaluation.md`.

The false-positive runs only show what `leakguard` over-reports. This measures what it misses, using leaks that other
people documented and labelled as wrong, not examples I wrote.

Sources: scikit-learn "Common pitfalls" guide (data leakage section) and the `temporalcv` failure-case examples 16-20
(https://temporalcv.readthedocs.io, `auto_examples_python.zip`). The files were read and linted, never executed.

| Documented leak | Source | leakguard |
|---|---|---|
| Feature selection (`SelectKBest`) fitted before `train_test_split` | scikit-learn guide | **caught** (LG003) |
| Corrected versions (split first; Pipeline) | scikit-learn guide | clean (2/2, no false positive) |
| `KFold(shuffle=True)` on time series | temporalcv 20 | **caught** (LG006, 2 sites) |
| `KFold(shuffle=True)` on financial returns | temporalcv 06 | **caught** (LG006) |
| `GridSearchCV(cv=KFold(shuffle=True))` on time series | temporalcv 07 | **caught** (LG006) |
| Rolling features on the full series without a lag (`y.rolling(10).mean()` feeding a model for the next `y`) | temporalcv 16 | missed at first; **caught after I added LG008** (see below) |
| Classification threshold tuned on the full data including test | temporalcv 17 | missed: no rule |
| No gap between train and test for a multi-step forecast horizon | temporalcv 19 | missed: no rule |
| Nested Diebold-Mariano test setup | temporalcv 18 | out of scope (a statistical procedure, not a code pattern) |

**Recall: 4 of 7 documented leaks (57 %) before LG008, 5 of 7 (71 %) after**, excluding the out-of-scope one. **The 71 % is in-sample**: I wrote LG008 after reading example 16, so it says the rule works on its motivating case, not that recall improved on unseen leaks. Only the 57 % is an independent measurement. Seven is a small sample; do not
read 57 % as a stable estimate. The misses are three classes of leak that `leakguard` has no rule for.
Candidate rules, in order of how detectable they are statically:

1. ~~A rolling/expanding/ewm statistic of the target column assigned to a feature without a preceding `.shift(1)`.~~ Done as LG008 (fires on columns named y / target / label / y_true; a first version that also matched `returns` and `close` was too aggressive and flagged ordinary feature engineering).
2. A threshold or cutoff computed from `y` / predictions over all rows (`np.percentile`, `precision_recall_curve`) before the split.
3. Forecast-horizon gaps: only detectable if the horizon is a literal near the CV call; likely heuristic-only.
