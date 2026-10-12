# No time-series signals in this file, so random splits are normal practice.
import pandas as pd
from sklearn.model_selection import KFold, train_test_split

df = pd.read_csv("iris.csv")
X, y = df.drop(columns="species"), df["species"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
cv = KFold(n_splits=5, shuffle=True, random_state=0)
