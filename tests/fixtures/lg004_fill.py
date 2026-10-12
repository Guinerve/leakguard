import pandas as pd

s = pd.Series([1.0, None, 3.0])

a = s.bfill()  # expect: LG004
b = s.backfill()  # expect: LG004
c = s.fillna(method="bfill")  # expect: LG004
d = s.interpolate()  # expect: LG004
e = s.interpolate(method="linear")  # expect: LG004

ok1 = s.ffill()
ok2 = s.fillna(method="ffill")
e2 = s.interpolate(limit_direction="forward")  # expect: LG004
ok4 = s.interpolate(method="pad")
ok5 = s.fillna(0)
