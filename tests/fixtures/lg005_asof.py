import pandas as pd

trades = pd.DataFrame({"time": pd.to_datetime(["2024-01-01"]), "px": [1.0]})
quotes = pd.DataFrame({"time": pd.to_datetime(["2024-01-02"]), "bid": [1.0]})

bad = pd.merge_asof(trades, quotes, on="time", direction="forward")  # expect: LG005
bad2 = pd.merge_asof(trades, quotes, on="time", direction="nearest")  # expect: LG005

ok = pd.merge_asof(trades, quotes, on="time")
ok2 = pd.merge_asof(trades, quotes, on="time", direction="backward")
