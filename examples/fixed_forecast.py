"""The same forecast with the leaks removed: only past data in features, split by time, scaler fitted on train."""
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sales = pd.read_csv("sales.csv", parse_dates=["date"]).set_index("date")

sales["units"] = sales["units"].ffill()                                  # carry the last known value forward
sales["trend"] = sales["units"].shift(1).rolling(7).mean()               # last 7 days, excluding today
sales["yesterday_price"] = sales["price"].shift(1)
sales = sales.dropna()

features = ["trend", "price", "yesterday_price"]
cutoff = int(len(sales) * 0.8)
train, test = sales.iloc[:cutoff], sales.iloc[cutoff:]                   # earlier days train, later days test

model = make_pipeline(StandardScaler(), Ridge()).fit(train[features], train["units"])
print("R^2:", model.score(test[features], test["units"]))
