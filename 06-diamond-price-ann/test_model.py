"""Verify the performance claims in this project's README.

The README reports MAE $780, RMSE $1,366 and R^2 = 0.883 from four predictors,
against a predict-the-mean baseline of MAE $3,032. The R^2 is the figure worth
quoting, so it is the one checked here.

The data and baseline checks need only pandas. Retraining the network needs
TensorFlow, which has no release for Python 3.13+, so that part is skipped with
a clear message rather than failing on a newer interpreter.

Run:  python test_model.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
CSV = Path(__file__).parent / "data" / "diamonds.csv"

# the README's reported figures
MAE, RMSE, R2 = 780.0, 1366.0, 0.883
QUALITY_MAP = {"premium": 5, "ideal": 4, "very good": 3, "good": 2, "fair": 1}

results = []


def check(name, fn):
    try:
        print(f"  OK    {name:<34} {fn() or ''}")
        results.append(True)
    except AssertionError as e:
        print(f"  FAIL  {name:<34} {e}")
        results.append(False)
    except Exception as e:
        print(f"  ERROR {name:<34} {type(e).__name__}: {e}")
        results.append(False)


def load():
    # semicolon-delimited, which is itself easy to get wrong
    df = pd.read_csv(CSV, sep=";")
    df["quality_numeric"] = df["quality"].str.lower().map(QUALITY_MAP)
    return df


def data_is_as_described():
    df = load()
    assert len(df) == 53_940, f"expected 53,940 diamonds, found {len(df):,}"
    assert list(df.columns)[:5] == ["carat", "depth", "table", "price", "quality"], \
        f"unexpected columns: {list(df.columns)[:5]}"
    assert df["quality_numeric"].notna().all(), \
        f"unmapped quality values: {sorted(set(df['quality'].str.lower()) - set(QUALITY_MAP))}"
    assert (df.price > 0).all(), "non-positive prices present"
    return (f"{len(df):,} rows, price ${df.price.min():,}-${df.price.max():,}, "
            f"mean ${df.price.mean():,.0f}")


def single_delimiter_matters():
    """Reading this file with the default comma gives one column, not five."""
    wrong = pd.read_csv(CSV, nrows=5)
    assert wrong.shape[1] == 1, (
        f"the file now parses as {wrong.shape[1]} columns with a comma delimiter; "
        f"the README's note about sep=';' may be stale")
    return "comma parsing yields 1 column; sep=';' is required"


def baseline_is_as_reported():
    df = load()
    p = df.price
    mae_base = float((p - p.mean()).abs().mean())
    rmse_base = float(p.std())
    assert abs(mae_base - 3032) < 60, f"baseline MAE is ${mae_base:,.0f}, README says $3,032"
    assert abs(rmse_base - 3989) < 60, f"baseline RMSE is ${rmse_base:,.0f}, README says $3,989"
    return f"predict-the-mean MAE ${mae_base:,.0f}, RMSE ${rmse_base:,.0f}"


def reported_metrics_are_consistent():
    """R^2, MAE and RMSE must agree with each other and with the price variance."""
    df = load()
    var = float(df.price.var())
    implied_r2 = 1 - (RMSE ** 2) / var
    assert abs(implied_r2 - R2) < 0.01, (
        f"RMSE ${RMSE:,.0f} implies R^2 = {implied_r2:.3f}, but the README says {R2}")
    assert MAE < RMSE, "MAE should be below RMSE"
    pct = 100 * MAE / df.price.mean()
    assert 15 < pct < 25, f"MAE is {pct:.1f}% of mean price; README says ~20%"
    return f"RMSE implies R^2 = {implied_r2:.3f}, MAE is {pct:.1f}% of mean price"


def network_reproduces_the_metrics():
    """Retrain the 64-32-16-8-1 network. Needs TensorFlow."""
    try:
        import tensorflow as tf
    except ImportError:
        raise RuntimeError(
            f"TensorFlow unavailable on Python {sys.version_info.major}."
            f"{sys.version_info.minor} - run this on 3.12 or earlier") from None

    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    df = load()
    X = df[["carat", "depth", "table", "quality_numeric"]]
    y = df["price"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    sc = StandardScaler().fit(Xtr)

    tf.random.set_seed(42)
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, input_dim=X.shape[1], activation="relu"),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(8, activation="relu"),
        tf.keras.layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    model.fit(sc.transform(Xtr), ytr, epochs=30, batch_size=32,
              validation_split=0.1, verbose=0)

    pred = model.predict(sc.transform(Xte), verbose=0).ravel()
    mae = mean_absolute_error(yte, pred)
    r2 = r2_score(yte, pred)
    print(f"        retrained: MAE ${mae:,.0f}   R^2 {r2:.3f}   "
          f"(README: ${MAE:,.0f}, {R2})")
    # a shorter run than the notebook's, so allow a generous band
    assert r2 > 0.80, f"R^2 fell to {r2:.3f}; the README claims {R2}"
    assert mae < 1200, f"MAE rose to ${mae:,.0f}; the README claims ${MAE:,.0f}"
    return f"MAE ${mae:,.0f}, R^2 {r2:.3f} - consistent with the README"


def main():
    print("diamond price ANN: README claims\n")
    check("dataset as described", data_is_as_described)
    check("semicolon delimiter required", single_delimiter_matters)
    check("baseline figures", baseline_is_as_reported)
    check("reported metrics self-consistent", reported_metrics_are_consistent)

    try:
        import tensorflow  # noqa: F401
        check("network reproduces metrics", network_reproduces_the_metrics)
    except ImportError:
        print(f"  skip  {'network reproduces metrics':<34} "
              f"TensorFlow unavailable on Python {sys.version_info.major}."
              f"{sys.version_info.minor}; run on 3.12")

    print(f"\n{sum(results)} of {len(results)} claims verified")
    if not all(results):
        return 1
    print("OK: the reported performance is consistent and the data is as described.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
