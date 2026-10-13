"""A next-day sales forecast with five common leaks. Deliberately wrong: run `leakguard check examples/`."""
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

sales = pd.read_csv("sales.csv", parse_dates=["date"]).set_index("date")

sales["units"] = sales["units"].bfill()                                  # fills gaps with later days
sales["trend"] = sales["units"].rolling(7, center=True).mean()           # window reaches 3 days ahead
sales["tomorrow_price"] = sales["price"].shift(-1)                        # tomorrow's price as a feature
sales = sales.dropna()

X = StandardScaler().fit_transform(sales[["trend", "price", "tomorrow_price"]])  # scaled on test rows too
y = sales["units"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)  # shuffles days

model = Ridge().fit(X_train, y_train)
print("R^2:", model.score(X_test, y_test))
