"""Verify the two headline claims in this project's README.

  Hepatitis C  the ensembles reach ~0.90 accuracy and ~0.97 ROC AUC, but one
               class is never predicted and macro F1 is around 0.5
  Diabetes     a tuned Random Forest barely beats a constant predictor, and
               finds about one diabetic in six

Both are claims about class imbalance rather than about model quality, which is
the point of the project's write-up. The diabetes model is refit with the
parameters the grid search chose rather than re-running 1,080 fits.

Run:  python test_results.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, f1_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

warnings.filterwarnings("ignore")
DATA = Path(__file__).parent / "data"

results = []


def check(name, fn):
    try:
        print(f"  OK    {name:<36} {fn() or ''}")
        results.append(True)
    except AssertionError as e:
        print(f"  FAIL  {name:<36} {e}")
        results.append(False)
    except Exception as e:
        print(f"  ERROR {name:<36} {type(e).__name__}: {e}")
        results.append(False)


# ------------------------------------------------------------------ hepatitis C

def hepatitis_is_imbalanced():
    df = pd.read_csv(DATA / "hepatitis_c.csv")
    assert len(df) == 615, f"expected 615 patients, found {len(df)}"
    target = [c for c in df.columns if "categor" in c.lower() or c.lower() == "category"]
    assert target, f"no diagnosis column found in {list(df.columns)[:6]}"
    counts = df[target[0]].value_counts()
    biggest = counts.max() / len(df)
    assert biggest > 0.8, (
        f"the majority class is only {biggest:.1%}; the README's imbalance claim "
        f"needs revisiting")
    return f"{len(df)} patients, majority class {biggest:.1%}, {len(counts)} classes"


def hepatitis_accuracy_is_inflated():
    """Macro F1 and accuracy must disagree sharply, which is the README's point."""
    df = pd.read_csv(DATA / "hepatitis_c.csv")
    target = [c for c in df.columns if "categor" in c.lower() or c.lower() == "category"][0]
    y = LabelEncoder().fit_transform(df[target].astype(str))
    # the notebook drops PatientID and Category, and does NOT stratify
    X = df.drop(columns=[target] + [c for c in df.columns if "patientid" in c.lower()],
                errors="ignore")
    for c in X.columns:
        # not `dtype == object`: pandas 3 reads CSV strings as StringDtype, so
        # that test misses `Sex` and the median imputer below fails on 'm'/'f'
        if not pd.api.types.is_numeric_dtype(X[c]):
            X[c] = LabelEncoder().fit_transform(X[c].astype(str))
    X = pd.DataFrame(SimpleImputer(strategy="median").fit_transform(X), columns=X.columns)

    # no stratify, matching the notebook: this is WHY a rare class ends up with
    # almost no test instances and an F1 of zero
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=42)
    sc = StandardScaler().fit(Xtr)
    m = LogisticRegression(max_iter=2000).fit(sc.transform(Xtr), ytr)
    pred = m.predict(sc.transform(Xte))

    acc = accuracy_score(yte, pred)
    macro = f1_score(yte, pred, average="macro")
    gap = acc - macro
    print(f"        accuracy {acc:.3f}   macro F1 {macro:.3f}   gap {gap:.3f}")
    assert gap > 0.15, (
        f"accuracy and macro F1 differ by only {gap:.3f}; the README argues the gap is large")

    return f"accuracy {acc:.3f} vs macro F1 {macro:.3f}, gap {gap:.3f}"


def hepatitis_notebook_reports_an_unpredicted_class():
    """Check the README against the notebook's own saved output.

    The 'one class is never predicted' claim belongs to the notebook's voting and
    stacking ensembles, not to the simpler proxy model above - a single logistic
    regression manages a non-zero F1 for all five classes on the same split. So
    this reads the executed notebook rather than refitting the ensemble.
    """
    import json
    nb_path = Path(__file__).parent / "notebooks" / "hepatitis_c_classification.ipynb"
    nb = json.loads(nb_path.read_text(encoding="utf-8"))

    blocks = []
    for cell in nb.get("cells", []):
        for o in cell.get("outputs", []):
            if o.get("output_type") == "stream":
                blocks.append("".join(o.get("text", [])))
            elif o.get("output_type") in ("execute_result", "display_data"):
                blocks.append("".join(o.get("data", {}).get("text/plain", "")))

    reports = [b for b in blocks if "precision" in b and "f1-score" in b]
    assert reports, "the notebook has no saved classification report to check"

    # a per-class row of exactly 0.00 across precision, recall and f1
    zero_rows = []
    for b in reports:
        for line in b.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].isdigit():
                p, r, f = parts[1], parts[2], parts[3]
                if p == "0.00" and r == "0.00" and f == "0.00":
                    zero_rows.append((parts[0], parts[4]))

    assert zero_rows, (
        "no class with F1 = 0.00 in the notebook's saved output; the README's claim "
        "that one class is never predicted is stale")
    cls, support = zero_rows[0]
    return f"class {cls} has F1 = 0.00 with support {support} in the saved run"


# --------------------------------------------------------------------- diabetes

def diabetes_barely_beats_a_constant():
    sample = DATA / "diabetes_brfss2015_sample.csv"
    full = DATA / "diabetes_brfss2015.csv"
    path = full if full.exists() else sample
    df = pd.read_csv(path)
    assert len(df) > 10_000, f"{path.name} has only {len(df)} rows"

    df = df[df["Diabetes_012"] != 1]                  # as the notebook does
    X, y = df.drop(columns=["Diabetes_012"]), df["Diabetes_012"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # the parameters GridSearchCV selected, rather than 1,080 refits
    rf = RandomForestClassifier(n_estimators=300, max_depth=30, min_samples_leaf=2,
                                min_samples_split=10, bootstrap=True,
                                random_state=42, n_jobs=-1).fit(Xtr, ytr)
    pred = rf.predict(Xte)

    acc = accuracy_score(yte, pred)
    baseline = yte.value_counts().max() / len(yte)
    minority = yte.value_counts().idxmin()
    rec = recall_score(yte, pred, pos_label=minority)
    macro = f1_score(yte, pred, average="macro")

    print(f"        source {path.name}  test n={len(yte):,}")
    print(f"        model accuracy {acc:.4f}   constant predictor {baseline:.4f}   "
          f"gain {100 * (acc - baseline):+.2f} pp")
    print(f"        minority recall {rec:.3f}   macro F1 {macro:.3f}")

    assert acc > baseline, "the model is now worse than a constant predictor"
    assert (acc - baseline) < 0.05, (
        f"the model now beats the baseline by {100 * (acc - baseline):.1f} pp; the "
        f"README's 'barely' claim is stale")
    assert rec < 0.40, (
        f"minority recall is now {rec:.2f}; the README says roughly one in six")
    return (f"+{100 * (acc - baseline):.2f} pp over constant, "
            f"recall {rec:.2f}")


def diabetes_sample_matches_full_distribution():
    s = pd.read_csv(DATA / "diabetes_brfss2015_sample.csv")
    props = (s["Diabetes_012"].value_counts(normalize=True) * 100).round(2)
    expected = {0.0: 84.24, 2.0: 13.93, 1.0: 1.83}
    for cls, pct in expected.items():
        got = float(props.get(cls, 0))
        assert abs(got - pct) < 0.5, (
            f"class {cls} is {got}% in the sample, expected ~{pct}%")
    return f"{len(s):,} rows, class balance {dict(props)} matches the full dataset"


def main():
    print("clinical prediction: README claims\n")
    check("hepatitis C: class imbalance", hepatitis_is_imbalanced)
    check("hepatitis C: accuracy inflated", hepatitis_accuracy_is_inflated)
    check("hepatitis C: class never predicted", hepatitis_notebook_reports_an_unpredicted_class)
    check("diabetes: sample is stratified", diabetes_sample_matches_full_distribution)
    check("diabetes: barely beats constant", diabetes_barely_beats_a_constant)

    print(f"\n{sum(results)} of {len(results)} claims verified")
    if not all(results):
        return 1
    print("OK: the imbalance findings in the README hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
