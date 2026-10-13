# Several train_test_split calls in one scope, as in a notebook that walks through several examples.
# Every split must be checked, not only the first one.
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Example 1: clean
A = pd.read_csv("a.csv")
A_tr, A_te = train_test_split(A)

# Example 2: scaler fitted on all rows before the second split
B = pd.read_csv("b.csv")
B_scaled = StandardScaler().fit_transform(B)  # expect: LG003
B_tr, B_te = train_test_split(B_scaled)

# Example 3: global-mean imputation before the third split
C = pd.read_csv("c.csv")
C = C.fillna(C.mean())  # expect: LG007
C_tr, C_te = train_test_split(C)

# Example 4: scaler fitted on all training rows, then a validation split carved out of them
X = pd.read_csv("x.csv")
X_train, X_test = train_test_split(X)
sc = StandardScaler()
X_train_s = sc.fit_transform(X_train)  # expect: LG003
X_tr, X_val = train_test_split(X_train_s)

# Example 5: correct; fit after the split, on train only. Re-splitting the raw data is not leakage.
D = pd.read_csv("d.csv")
D_tr, D_te = train_test_split(D)
D_tr_s = StandardScaler().fit_transform(D_tr)
D_tr2, D_te2 = train_test_split(D, random_state=1)

# Example 6: a leak that feeds both a split and a later re-split is reported once
E = pd.read_csv("e.csv")
E_s = StandardScaler().fit_transform(E)  # expect: LG003
E_tr, E_te = train_test_split(E_s)
E_a, E_b = train_test_split(E_tr)

# Example 7: a module name (np) shared by an unrelated fit and a later split is not lineage
toy_s = StandardScaler().fit_transform(np.array([[1.0], [2.0]]))
F = np.ones((4, 2))
F_tr, F_te = train_test_split(F)

# Example 8 (found on handson-ml3 ch. 5): `X` is scaled for one demo, then rebound to a new dataset before a later
# split. The split sees the new `X`, not the one the scaler was fitted on.
X = pd.read_csv("iris.csv")
X_scaled = StandardScaler().fit_transform(X)
X = pd.read_csv("housing.csv")
X_tr8, X_te8 = train_test_split(X)

# Example 9: rebinding a name from itself keeps the lineage, so this leak is still found
G = pd.read_csv("g.csv")
G_s = StandardScaler().fit_transform(G)  # expect: LG003
G = G_s[:, :2]
G_tr, G_te = train_test_split(G)

# Example 10: the fitted data reaches the split through a name derived before the original is rebound
H = pd.read_csv("h.csv")
H = StandardScaler().fit_transform(H)  # expect: LG003
H2 = H * 2
H = None
H_tr, H_te = train_test_split(H2)
