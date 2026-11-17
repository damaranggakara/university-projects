"""Compare the classifiers in this project against a constant predictor.

The notebooks report 97-99% accuracy across four models. With 33 non-performing
loans in 2,700 records, a model that always predicts "will repay" scores 98.8%,
so accuracy says almost nothing here. This measures what the models actually do
about the 1.2% that matters.

Run:  python test_baselines.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             f1_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")
XLSX = Path(__file__).parent / "data" / "credit_risk_survey.xlsx"

MODELS = {
    "Logistic Regression": (lambda: LogisticRegression(max_iter=2000), True),
    "Random Forest": (lambda: RandomForestClassifier(random_state=42, n_jobs=-1), False),
    "SVM": (lambda: SVC(kernel="rbf"), True),
}
try:
    from xgboost import XGBClassifier
    MODELS["XGBoost"] = (lambda: XGBClassifier(eval_metric="logloss",
                                               random_state=42), False)
except ImportError:
    pass


def load():
    df = pd.read_excel(XLSX, sheet_name="Full Data")
    # `Z (cat)` holds the five-level Indonesian loan classification:
    #   1 Lancar, 2 Dalam Perhatian Khusus  -> performing (PL)
    #   3 Kurang Lancar, 4 Diragukan, 5 Macet -> non-performing (NPL)
    # The notebooks split PL/NPL at 3, giving 2,667 vs 33. Splitting at 2
    # instead would be a different and far easier problem (433 positives).
    target = "Z (cat)"
    assert target in df.columns, f"{target} not found in {list(df.columns)[:8]}"
    y = (df[target] >= 3).astype(int)          # 1 = non-performing
    drop = [c for c in ("IDR", "IDR1", "No Bank", "Nama", target, "Z (day)")
            if c in df.columns]
    X = df.drop(columns=drop)
    X = X.select_dtypes(include=[np.number]).fillna(0)
    return df, X, y


def main():
    df, X, y = load()
    print(f"dataset: {df.shape[0]:,} respondents x {df.shape[1]} columns, "
          f"{X.shape[1]} numeric predictors")
    print(f"banks   : {df['Nama'].nunique()} ({', '.join(sorted(df['Nama'].unique()))})")
    npl = int(y.sum())
    print(f"target  : {npl} non-performing of {len(y):,} "
          f"({100 * npl / len(y):.1f}%)\n")

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42,
                                          stratify=y)
    sc = StandardScaler().fit(Xtr)
    Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)

    n = len(yte)
    npl_te = int(yte.sum())
    baseline = 1 - npl_te / n                 # always predict "performing"
    print(f"test set: {n} rows, {npl_te} non-performing")
    print(f"constant predictor ('everyone repays'): accuracy {baseline:.4f}\n")

    print(f"{'model':<22}{'accuracy':>9}{'vs base':>9}{'NPL recall':>12}"
          f"{'NPL F1':>8}{'ROC AUC':>9}{'PR AUC':>8}")
    print("-" * 78)

    rows = []
    for name, (make, scaled) in MODELS.items():
        m = make()
        m.fit(Xtr_s if scaled else Xtr, ytr)
        pred = m.predict(Xte_s if scaled else Xte)
        acc = float((pred == yte.values).mean())

        try:
            score = (m.predict_proba(Xte_s if scaled else Xte)[:, 1]
                     if hasattr(m, "predict_proba")
                     else m.decision_function(Xte_s if scaled else Xte))
            roc = roc_auc_score(yte, score)
            pr = average_precision_score(yte, score)
        except Exception:
            roc = pr = float("nan")

        rec = recall_score(yte, pred, pos_label=1, zero_division=0)
        f1 = f1_score(yte, pred, pos_label=1, zero_division=0)
        caught = int(((pred == 1) & (yte.values == 1)).sum())
        rows.append((name, acc, rec, f1, roc, pr, caught))
        print(f"{name:<22}{acc:>9.4f}{acc - baseline:>+9.4f}{rec:>12.2f}"
              f"{f1:>8.2f}{roc:>9.3f}{pr:>8.3f}")

    print()
    worse = [r[0] for r in rows if r[1] < baseline]
    never = [r[0] for r in rows if r[6] == 0]
    print(f"below the constant predictor : {', '.join(worse) or 'none'}")
    print(f"never predicts a default     : {', '.join(never) or 'none'}")
    best_caught = max(r[6] for r in rows)
    print(f"most defaults identified     : {best_caught} of {npl_te}")

    print("\nconfusion matrix, best model by NPL recall:")
    best = max(rows, key=lambda r: r[2])
    make, scaled = MODELS[best[0]]
    m = make(); m.fit(Xtr_s if scaled else Xtr, ytr)
    cm = confusion_matrix(yte, m.predict(Xte_s if scaled else Xte))
    print(f"  {best[0]}")
    print(f"             predicted PL   predicted NPL")
    print(f"  actual PL   {cm[0][0]:>10}   {cm[0][1]:>13}")
    print(f"  actual NPL  {cm[1][0]:>10}   {cm[1][1]:>13}")

    # --- the claims this script exists to check -------------------------------
    assert df.shape[0] == 2700, f"expected 2,700 respondents, found {df.shape[0]}"
    assert df["Nama"].nunique() == 5, "expected five banks"
    assert npl / len(y) < 0.02, "the target is no longer extremely imbalanced"
    assert baseline > 0.97, f"constant predictor scores only {baseline:.3f}"
    assert all(r[1] <= baseline + 0.01 for r in rows), (
        "a model now beats the constant predictor by more than a point - the "
        "README's framing needs revisiting")
    assert best_caught <= npl_te // 2, (
        f"a model now identifies {best_caught} of {npl_te} defaults; the README "
        f"says the models essentially cannot")

    print("\nOK: accuracy here tracks the class balance, not model skill.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
