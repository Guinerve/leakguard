from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def leaky(X, y):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)  # expect: LG003
    pca = PCA(n_components=2)
    pca.fit(X_scaled)  # expect: LG003
    X_pca = pca.transform(X_scaled)
    X_train, X_test, y_train, y_test = train_test_split(X_pca, y)
    return X_train


def leaky_chained(X, y):
    X2 = SelectKBest(k=5).fit_transform(X, y)  # expect: LG003
    return train_test_split(X2, y)


def correct(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    enc = OneHotEncoder()
    enc.fit(X_train)
    return X_train, X_test


def no_split_here(X):
    # No train_test_split in this scope, so nothing to compare against
    return StandardScaler().fit_transform(X)


def not_a_transformer(model, X, y):
    model.fit(X, y)
    return train_test_split(X, y)


def toy_scaler_for_a_figure(X_iris, y_iris):
    # Found on a real notebook: a scaler fitted on unrelated toy data earlier in the file.
    # It never feeds the split, so it is not leakage.
    import numpy as np

    toy = np.array([[1.0, 50.0], [5.0, 20.0]])
    toy_scaled = StandardScaler().fit_transform(toy)
    return train_test_split(X_iris, y_iris), toy_scaled


def name_reused_for_a_different_model(X, y, X_iris, y_iris):
    # Found on a real notebook: `model` was a PCA, then reassigned to a classifier.
    model = PCA(n_components=2)
    model.fit(X)
    model = object()
    model.fit(X_iris, y_iris)
    return train_test_split(X_iris, y_iris)


def stateless_transform_is_fine(X, y):
    from sklearn.preprocessing import PolynomialFeatures

    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)
    return train_test_split(X_poly, y)


def leaky_through_derived_name(X, y):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)  # expect: LG003
    features = Xs[:, :3]
    return train_test_split(features, y)
