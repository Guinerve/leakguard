# The guide's corrected versions (split first, and a Pipeline). Must not be flagged.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, random_state=42)
select = SelectKBest(k=25)
X_train_selected = select.fit_transform(X_train, y_train)
gbc = HistGradientBoostingClassifier(random_state=1)
gbc.fit(X_train_selected, y_train)
X_test_selected = select.transform(X_test)
y_pred = gbc.predict(X_test_selected)
accuracy_score(y_test, y_pred)

from sklearn.pipeline import make_pipeline
X_train, X_test, y_train, y_test = train_test_split(
    X, y, random_state=42)
pipeline = make_pipeline(SelectKBest(k=25),
                         HistGradientBoostingClassifier(random_state=1))
pipeline.fit(X_train, y_train)
