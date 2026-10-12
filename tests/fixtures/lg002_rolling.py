import pandas as pd

s = pd.Series([1, 2, 3, 4, 5], index=pd.date_range("2024-01-01", periods=5))

smooth = s.rolling(3, center=True).mean()  # expect: LG002
smooth2 = s.rolling(window=3, min_periods=1, center=True).median()  # expect: LG002

trailing = s.rolling(3).mean()
trailing2 = s.rolling(3, center=False).mean()
expanding = s.expanding().mean()
