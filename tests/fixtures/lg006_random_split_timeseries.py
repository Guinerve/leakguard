import pandas as pd
from sklearn.model_selection import KFold, TimeSeriesSplit, train_test_split

df = pd.read_csv("prices.csv")
df["date"] = pd.to_datetime(df["date"])
df["lag1"] = df["close"].shift(1)

X, y = df[["lag1"]], df["close"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)  # expect: LG006
a = train_test_split(X, y, shuffle=True)  # expect: LG006
cv = KFold(n_splits=5, shuffle=True)  # expect: LG006

ok1 = train_test_split(X, y, shuffle=False)
ok2 = TimeSeriesSplit(n_splits=5)
ok3 = KFold(n_splits=5)
