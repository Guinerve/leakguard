# Real example from scikit-learn's "Common pitfalls" guide (doc/common_pitfalls.rst, BSD-3-Clause), the documented leaky
# version. X and y come from the guide's earlier data setup.
from sklearn.model_selection import train_test_split
from sklearn.feature_selection import SelectKBest
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score
# Incorrect preprocessing: the entire data is transformed
X_selected = SelectKBest(k=25).fit_transform(X, y)  # expect: LG003
X_train, X_test, y_train, y_test = train_test_split(
    X_selected, y, random_state=42)
gbc = HistGradientBoostingClassifier(random_state=1)
gbc.fit(X_train, y_train)
y_pred = gbc.predict(X_test)
accuracy_score(y_test, y_pred)
