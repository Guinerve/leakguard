"""Rule catalogue: ID -> (short name, message template, false-positive notes)."""

RULES: dict[str, tuple[str, str, str]] = {
    "LG001": (
        "negative-shift",
        "`.shift({n})` pulls future values into this row. Fine for building a target, leakage if it feeds a feature.",
        "Heuristic: skipped when assigned to a name that looks like a target (target, label, y, fwd, future, next).",
    ),
    "LG002": (
        "centered-rolling",
        "`rolling(..., center=True)` uses values after each row. Use a trailing window on time-indexed data.",
        "Safe on non-temporal data such as image or spatial smoothing.",
    ),
    "LG003": (
        "fit-before-split",
        "`{call}` is fitted on rows that `train_test_split` (line {split}) later holds out, so their statistics leak into training. Split first, fit on train only, or use a Pipeline.",
        "Checks every train_test_split in a function or module scope against the fits earlier in that scope; fits in other scopes, and leaks into cross-validation folds, are not seen.",
    ),
    "LG004": (
        "backward-fill",
        "`{call}` fills gaps with later values. On a time series this leaks the future; use ffill.",
        "Safe if the data is not time-ordered, or the fill is applied inside the training fold only.",
    ),
    "LG005": (
        "forward-asof-merge",
        "`merge_asof(direction={direction!r})` matches rows to future timestamps. Use direction='backward'.",
        "Safe when the right table is deliberately aligned to a known later event.",
    ),
    "LG006": (
        "random-split-on-time-data",
        "{what} shuffles time-ordered data, so training rows come from after test rows. Use shuffle=False or TimeSeriesSplit.",
        "Only reported when the file shows time-series signals (datetime parsing, shift, rolling, date columns).",
    ),
    "LG007": (
        "global-statistic-imputation",
        "`fillna` with a statistic ({stat}) computed on rows that `train_test_split` (line {split}) later holds out leaks their values. Compute it on the training rows only.",
        "Only reported when the fill happens earlier than a train_test_split in the same scope.",
    ),
    "LG008": (
        "unlagged-target-statistic",
        "`{call}` on the target column `{col}` includes the current value, so a feature built from it for predicting `{col}` leaks it. Apply `.shift(1)` before the rolling/expanding/ewm statistic.",
        "Heuristic: fires when the source column name looks like a target (y, target, label, ...) and no `.shift` appears in the chain. Safe if the feature predicts a different, later quantity.",
    ),
}
