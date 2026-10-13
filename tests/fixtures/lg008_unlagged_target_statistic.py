import pandas as pd

df = pd.DataFrame({"y": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})

# Includes the current value of y: a feature for predicting y that already contains y
df["rolling_mean"] = df["y"].rolling(3).mean()  # expect: LG008
df["running_total"] = df["y"].expanding().sum()  # expect: LG008
df["smoothed"] = df["y"].ewm(span=3).mean()  # expect: LG008

# Lagged first: only past values
df["safe_rolling"] = df["y"].shift(1).rolling(3).mean()
df["safe_expanding"] = df["y"].shift(1).expanding().sum()

# A different column is not the target
df["other"] = pd.Series([1, 2, 3, 4, 5, 6])
df["other_roll"] = df["other"].rolling(3).mean()

# Lagged after the statistic: the same past-only window, written the other common way
df["safe_lag_after"] = df["y"].rolling(3).mean().shift(1)
df["safe_lag_after_default"] = df["y"].expanding().max().shift()
df["leak_lead_after"] = df["y"].rolling(3).mean().shift(-1)  # expect: LG008  # expect: LG001
