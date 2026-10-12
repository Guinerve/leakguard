import pandas as pd

df = pd.DataFrame({"close": [1, 2, 3], "volume": [4, 5, 6]})

df["feature_tomorrow"] = df["close"].shift(-1)  # expect: LG001
df["ret_lead"] = df["close"].pct_change().shift(-2)  # expect: LG001
shifted = df["close"].shift(periods=-3)  # expect: LG001

# Targets are meant to look ahead
df["target"] = df["close"].shift(-1)
df["fwd_return"] = df["close"].pct_change().shift(-5)
y = df["close"].shift(-1)

# Lags are fine
df["lag1"] = df["close"].shift(1)
df["lag2"] = df["close"].shift(2)
df["same"] = df["close"].shift(0)
n = 3
df["dyn"] = df["close"].shift(n)

df["suppressed"] = df["close"].shift(-1)  # leakguard: ignore[LG001]
df["suppressed_all"] = df["close"].shift(-1)  # leakguard: ignore
df["wrong_rule_suppressed"] = df["close"].shift(-1)  # leakguard: ignore[LG002]  # expect: LG001
