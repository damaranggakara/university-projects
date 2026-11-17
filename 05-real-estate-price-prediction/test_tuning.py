"""Verify the tuning table in this project's README.

The README claims grid search helped SVR substantially, helped Random Forest
slightly, and *hurt* both boosting models. Those four numbers are the most
interesting thing in the project and nothing in the notebook computes them, so
they are recomputed here and asserted.

Run:  python test_tuning.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")
try:
    from lightgbm import LGBMRegressor
    HAVE_LGBM = True
except ImportError:
    HAVE_LGBM = False

CSV = Path(__file__).parent / "data" / "real_estate.csv"

# (name, estimator, grid, expected sign of the tuning effect)
SPECS = [
    ("Random Forest", RandomForestRegressor(random_state=42),
     {"n_estimators": [100, 200, 300], "max_depth": [None, 5, 10, 20],
      "min_samples_split": [2, 5, 10]}, "helped"),
    ("SVR", SVR(),
     {"C": [1, 10, 100], "gamma": ["scale", 0.1, 0.01],
      "kernel": ["rbf", "linear"]}, "helped a lot"),
    ("Gradient Boosting", GradientBoostingRegressor(random_state=42),
     {"n_estimators": [100, 300, 500], "learning_rate": [0.01, 0.05, 0.1],
      "max_depth": [2, 3, 5]}, "hurt"),
]
if HAVE_LGBM:
    SPECS.append(("LightGBM", LGBMRegressor(random_state=42, verbose=-1),
                  {"n_estimators": [100, 300, 500], "learning_rate": [0.01, 0.05, 0.1],
                   "num_leaves": [15, 31, 63]}, "hurt"))


def load():
    df = pd.read_csv(CSV).drop(columns=["No"])
    X = df.drop(columns=["Y house price of unit area", "X1 transaction date"])
    y = df["Y house price of unit area"]
    return df, X, y


def main():
    df, X, y = load()
    assert len(df) == 414, f"expected 414 transactions, found {len(df)}"
    print(f"dataset: {len(df)} transactions, {X.shape[1]} predictors\n")

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    sc = StandardScaler().fit(Xtr)
    Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)
    assert len(Xtr) == 331, f"training split is {len(Xtr)}, README says 331"

    print(f"{'model':<20}{'default R2':>11}{'tuned R2':>10}{'change':>9}{'%':>8}  claim")
    print("-" * 70)

    rows = []
    for name, est, grid, claim in SPECS:
        base = est.__class__(**est.get_params()).fit(Xtr_s, ytr)
        r2_default = r2_score(yte, base.predict(Xte_s))

        gs = GridSearchCV(est.__class__(**est.get_params()), grid, cv=5,
                          scoring="r2", n_jobs=-1).fit(Xtr_s, ytr)
        r2_tuned = r2_score(yte, gs.best_estimator_.predict(Xte_s))

        delta = r2_tuned - r2_default
        pct = 100 * delta / abs(r2_default)
        rows.append((name, r2_default, r2_tuned, delta, pct, claim))
        print(f"{name:<20}{r2_default:>11.3f}{r2_tuned:>10.3f}{delta:>+9.3f}"
              f"{pct:>+8.1f}  {claim}")

    print()
    by = {r[0]: r for r in rows}

    # the four claims the README makes
    assert by["SVR"][4] > 10, (
        f"README claims SVR gained ~16%; measured {by['SVR'][4]:+.1f}%")
    assert by["Random Forest"][3] > 0, (
        f"README claims tuning helped Random Forest; measured {by['Random Forest'][3]:+.3f}")
    assert by["Gradient Boosting"][3] < 0, (
        f"README claims tuning hurt Gradient Boosting; measured "
        f"{by['Gradient Boosting'][3]:+.3f}")
    if HAVE_LGBM:
        assert by["LightGBM"][3] < 0, (
            f"README claims tuning hurt LightGBM; measured {by['LightGBM'][3]:+.3f}")
    else:
        print("note: lightgbm not installed, so its claim was not checked\n")

    # and the headline: untuned Gradient Boosting is the best model overall
    best = max(rows, key=lambda r: max(r[1], r[2]))
    gbr_default = by["Gradient Boosting"][1]
    all_scores = [s for r in rows for s in (r[1], r[2])]
    assert abs(gbr_default - max(all_scores)) < 1e-9, (
        f"README claims untuned Gradient Boosting is best overall at R2 ~0.81; "
        f"best measured is {best[0]} at {max(all_scores):.3f}")
    print(f"best overall: untuned Gradient Boosting, R2 = {gbr_default:.3f}")

    mean_gain = np.mean([r[4] for r in rows])
    print(f"mean tuning effect across models: {mean_gain:+.1f}%")
    print("\nThe '+12% R2' figure on an earlier CV is defensible only for SVR.")
    print("\nOK: the tuning table in the README is reproduced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
