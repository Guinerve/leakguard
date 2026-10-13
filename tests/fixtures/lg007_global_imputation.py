import pandas as pd
from sklearn.model_selection import train_test_split


def leaky(df, y):
    df = df.fillna(df.mean())  # expect: LG007
    df["a"] = df["a"].fillna(df["a"].median())  # expect: LG007
    return train_test_split(df, y)


def correct(df, y):
    X_train, X_test, y_train, y_test = train_test_split(df, y)
    means = X_train.mean()
    return X_train.fillna(means), X_test.fillna(means)


def constant_fill(df, y):
    df = df.fillna(0)
    return train_test_split(df, y)


def unrelated_frame_filled_with_its_own_mean(df, other, y):
    other = other.fillna(other.mean())
    return other, train_test_split(df, y)


def leaky_keyword_and_mode(df, y):
    df = df.fillna(value=df.median())  # expect: LG007
    df["b"] = df["b"].fillna(df["b"].mode()[0])  # expect: LG007
    return train_test_split(df, y)
