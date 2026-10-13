"""Rule catalogue: ID -> (short name, message template, notes on when the rule can be wrong)."""

RULES: dict[str, tuple[str, str, str]] = {
    "LG001": (
        "negative-shift",
        "`.shift({n})` moves later values into this row. This is correct for a target, but it is a leak in a feature.",
        "Not reported when the result goes to a name that looks like a target (target, label, y, fwd, future, next).",
    ),
    "LG002": (
        "centered-rolling",
        "`rolling(..., center=True)` uses values after each row. On time series data, remove center=True.",
        "Correct on data that is not ordered in time, for example image or map smoothing.",
    ),
    "LG003": (
        "fit-before-split",
        ("`{call}` learns from rows that `train_test_split` (line {split}) later puts in the test set. Their statistics "
        "leak into training. Split first and fit on the training rows only, or use a Pipeline."),
        ("Compares each train_test_split with the earlier fits in the same function or module. It does not see fits "
        "in other functions, or leaks into cross validation folds."),
    ),
    "LG004": (
        "backward-fill",
        "`{call}` fills gaps with later values. On a time series, this leaks the future. Use ffill() instead.",
        "Correct if the data is not ordered in time, or if the fill uses only the training rows.",
    ),
    "LG005": (
        "forward-asof-merge",
        "`merge_asof(direction={direction!r})` can match a row to a later timestamp. Use direction='backward'.",
        "Correct when you align the right table to a known later event on purpose.",
    ),
    "LG006": (
        "random-split-on-time-data",
        ("{what} shuffles data that is ordered in time, so some training rows come after test rows. "
        "Use shuffle=False or TimeSeriesSplit."),
        ("For train_test_split, reported only when the split data comes from time series code (datetime parsing, "
        "shift, rolling, date columns). For KFold and ShuffleSplit, one such sign anywhere in the file is enough."),
    ),
    "LG007": (
        "global-statistic-imputation",
        ("`fillna` uses a statistic ({stat}) of rows that `train_test_split` (line {split}) later puts in the test "
        "set. This leaks their values. Calculate the statistic on the training rows only."),
        ("Reported only when the fill comes before a train_test_split in the same function or module, and its data "
        "reaches that split."),
    ),
    "LG008": (
        "unlagged-target-statistic",
        ("`{call}` on the target column `{col}` includes the current value. A feature made from it leaks `{col}` "
        "into the model. Add `.shift(1)` before or after the statistic."),
        ("Reported when the column name is y, target, label or y_true and no `.shift` comes before or after the "
        "statistic. Correct if the feature predicts a different, later quantity."),
    ),
}
