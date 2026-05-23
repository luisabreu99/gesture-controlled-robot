import pandas as pd

from sklearn.ensemble import (
    RandomForestClassifier
)

from sklearn.model_selection import (
    train_test_split
)

import joblib

data = pd.read_csv(
    "gestures.csv",
    header=None
)

X = data.iloc[:, :-1]

y = data.iloc[:, -1]

X_train, X_test, y_train, y_test = (
    train_test_split(
        X,
        y,
        test_size=0.2
    )
)

model = RandomForestClassifier()

model.fit(
    X_train,
    y_train
)

accuracy = model.score(
    X_test,
    y_test
)

print(
    "Accuracy:",
    accuracy
)

joblib.dump(
    model,
    "right_model.pkl"
)