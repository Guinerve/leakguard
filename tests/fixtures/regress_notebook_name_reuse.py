# Regressions found by running leakguard over 95 public notebooks (cells concatenated into one scope).
import pandas as pd
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

# Example 1: a scaler fitted on one dataset...
X_train, y_train = pd.DataFrame({"a": [1.0, 2.0]}), [0, 1]
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
scores = cross_val_score(SGDClassifier(), X_train_scaled, y_train, cv=2)

# ...then the same names reused for a completely different example. No leakage between them.
X = pd.DataFrame({"b": [3.0, 4.0, 5.0, 6.0]})
y = [0, 1, 0, 1]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Unrelated time handling elsewhere in the file must not make a tabular split "time-ordered".
stamp = pd.to_datetime("2024-01-01")
tabular = pd.DataFrame({"f": [1, 2, 3, 4], "t": [0, 1, 0, 1]})
Xt, Xv, yt, yv = train_test_split(tabular[["f"]], tabular["t"], test_size=0.25)

# Stratified CV is a classification tool
skf = StratifiedKFold(n_splits=3)
