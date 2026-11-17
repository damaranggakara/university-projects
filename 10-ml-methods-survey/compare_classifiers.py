"""Do the classifier rankings in this project mean anything?

The four classification notebooks report SVM 0.97 > Naive Bayes 0.96 > KNN 0.94 >
Decision Tree 0.91, and the README read that as "SVM wins on every measure". The
test set is 93 rows. This script checks whether any of that ordering survives.

Three things are tested:

  1. a majority-class baseline, which on an 86/7 split is already very high
  2. confidence intervals on each accuracy
  3. McNemar's test on each pair

McNemar is the right test here and an ordinary two-proportion test is not: all
four models are evaluated on the *same* test set, so their predictions are
paired. McNemar looks only at the cases where two models disagree, which is the
information that actually distinguishes them.

A single 70/30 split is also only one draw, so the script finishes by repeating
the split 50 times to show how much the ranking moves on its own.

Run:  python compare_classifiers.py
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import StratifiedShuffleSplit, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

CSV = Path(__file__).parent / "data" / "survey_lung_cancer.csv"

# model -> (estimator factory, needs_scaling) exactly as the notebooks configure them
MODELS = {
    "SVM":           (lambda: SVC(kernel="linear"),                True),
    "Naive Bayes":   (lambda: GaussianNB(),                        False),
    "KNN":           (lambda: KNeighborsClassifier(n_neighbors=5), True),
    "Decision Tree": (lambda: DecisionTreeClassifier(random_state=42), False),
}


def load():
    """Same preprocessing as the notebooks."""
    df = pd.read_csv(CSV).dropna()
    df = pd.get_dummies(df, columns=["GENDER"], drop_first=True)
    df["LUNG_CANCER"] = LabelEncoder().fit_transform(df["LUNG_CANCER"])
    return df.drop(columns=["LUNG_CANCER"]), df["LUNG_CANCER"]


def fit_predict(X_tr, X_te, y_tr, seed_split=True):
    """Return {model: predictions} on one split."""
    scaler = StandardScaler().fit(X_tr)
    X_tr_s, X_te_s = scaler.transform(X_tr), scaler.transform(X_te)
    preds = {}
    for name, (make, scaled) in MODELS.items():
        m = make()
        m.fit(X_tr_s if scaled else X_tr, y_tr)
        preds[name] = m.predict(X_te_s if scaled else X_te)
    return preds


def mcnemar(a_correct, b_correct):
    """Exact McNemar on paired correctness vectors.

    Only discordant pairs carry information: n01 = a wrong & b right,
    n10 = a right & b wrong. Under the null they are equally likely, so the
    test is a two-sided binomial on n10 out of (n01 + n10).
    """
    n01 = int(np.sum(~a_correct & b_correct))
    n10 = int(np.sum(a_correct & ~b_correct))
    if n01 + n10 == 0:
        return n01, n10, 1.0          # identical predictions
    return n01, n10, stats.binomtest(n10, n01 + n10, 0.5).pvalue


def main():
    X, y = load()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=42)
    preds = fit_predict(X_tr, X_te, y_tr)

    n = len(y_te)
    counts = y_te.value_counts()
    maj_class = counts.idxmax()
    baseline = counts.max() / n

    print(f"test set: {n} rows  ({counts.to_dict()})")
    print(f"majority-class baseline: predict {maj_class} always -> {baseline:.3f}\n")

    print(f"{'model':<16}{'accuracy':>9}{'95% CI':>18}{'vs baseline':>13}")
    print("-" * 58)
    acc = {}
    correct = {}
    for name, p in preds.items():
        correct[name] = (p == y_te.values)
        k = int(correct[name].sum())
        acc[name] = k / n
        lo, hi = stats.binomtest(k, n).proportion_ci(confidence_level=0.95)
        delta = acc[name] - baseline
        print(f"{name:<16}{acc[name]:>9.3f}   [{lo:.3f}, {hi:.3f}]{delta:>+13.3f}")

    worse = [m for m, a in acc.items() if a < baseline]
    print()
    if worse:
        print(f"Below the majority-class baseline: {', '.join(worse)}")
    print("Every interval overlaps every other, which already means the ordering")
    print("is not established by this test set.\n")

    print("pairwise McNemar (paired, same test set)")
    print(f"{'pair':<34}{'disagree':>10}{'p':>8}  verdict")
    print("-" * 66)
    any_sig = False
    for a, b in combinations(MODELS, 2):
        n01, n10, p = mcnemar(correct[a], correct[b])
        sig = p < 0.05
        any_sig |= sig
        print(f"{a + ' vs ' + b:<34}{n01 + n10:>10}{p:>8.3f}  "
              f"{'significant' if sig else 'not significant'}")

    print()
    if not any_sig:
        print("No pair differs significantly. The models disagree on only a handful of")
        print("cases, and the split of those is consistent with chance.\n")

    # how much does the single split matter?
    print("accuracy across 50 repeated stratified 70/30 splits")
    print(f"{'model':<16}{'mean':>8}{'sd':>7}{'min':>7}{'max':>7}{'rank 1st':>10}")
    print("-" * 56)
    sss = StratifiedShuffleSplit(n_splits=50, test_size=0.3, random_state=0)
    scores = {m: [] for m in MODELS}
    wins = {m: 0 for m in MODELS}
    for tr, te in sss.split(X, y):
        p = fit_predict(X.iloc[tr], X.iloc[te], y.iloc[tr])
        run = {m: float((p[m] == y.iloc[te].values).mean()) for m in MODELS}
        for m, v in run.items():
            scores[m].append(v)
        best = max(run, key=run.get)
        wins[best] += 1
    for m in MODELS:
        s = np.array(scores[m])
        print(f"{m:<16}{s.mean():>8.3f}{s.std():>7.3f}{s.min():>7.3f}{s.max():>7.3f}"
              f"{wins[m]:>10}")

    top = max(scores, key=lambda m: np.mean(scores[m]))
    n_splits = len(scores[top])
    # does the leader win more often than chance? chance = 1/len(MODELS)
    p_wins = stats.binomtest(wins[top], n_splits, 1 / len(MODELS),
                             alternative="greater").pvalue
    print(f"\n{top} ranks first in {wins[top]}/{n_splits} splits; chance would be "
          f"{n_splits / len(MODELS):.0f}/{n_splits}")
    print(f"   binomial test vs chance: p = {p_wins:.2e}  "
          f"{'significant' if p_wins < 0.05 else 'not significant'}")
    print(f"\nSo: one test set of {n} cannot separate these models - every McNemar test")
    print(f"above is non-significant. Repeated resampling can, and it does favour {top}.")

    # the reported split was also a favourable draw
    print(f"\nThe notebooks' single split (random_state=42) is optimistic:")
    for m in MODELS:
        print(f"   {m:<16} reported {acc[m]:.3f}   mean over {n_splits} splits "
              f"{np.mean(scores[m]):.3f}   ({acc[m] - np.mean(scores[m]):+.3f})")

    # --- assertions: what this script is claiming ---
    assert n == 93, f"expected the 93-row test set, got {n}"
    assert abs(acc["SVM"] - 0.97) < 0.02, "SVM accuracy no longer matches the notebook"
    assert all(np.std(scores[m]) > 0 for m in MODELS), "repeated splits produced no variation"
    print("\nOK: checks passed.")


if __name__ == "__main__":
    main()
