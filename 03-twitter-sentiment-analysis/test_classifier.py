"""Quantify what the 90% accuracy in this project is actually worth.

The notebook reports Naive Bayes at 0.90 accuracy on a 20-tweet test set. This
puts numbers on the two caveats the README states in words - how wide the
interval is at n = 20, and how much of the accuracy is the majority class - and
tests the structural problem it raises: the classifier is trained on VADER's own
labels, so agreeing with VADER is not evidence about sentiment.

The notebook's pipeline is reused rather than reimplemented. That matters here:
VADER is applied to `cleaned_text` (after URL stripping, tokenisation, spell
correction and stopword removal), not to the raw tweet, and labelling raw text
instead gives a different class distribution and a materially lower accuracy.

Run:  python test_classifier.py
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import pandas as pd
from scipy import stats
from sklearn.metrics import accuracy_score

NB = Path(__file__).parent / "notebooks" / "twitter_sentiment.ipynb"


def run_notebook_pipeline():
    """Execute the notebook's code cells and hand back its namespace.

    Run from the notebooks directory: the notebook resolves its data with
    `Path.cwd().parent / "data"`, so the working directory is part of its
    contract.
    """
    import os

    nb = json.loads(NB.read_text(encoding="utf-8"))
    ns = {"__name__": "__notebook__"}
    buf = io.StringIO()
    skipped = []
    prev = os.getcwd()
    os.chdir(NB.parent)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            for i, cell in enumerate(nb.get("cells", [])):
                if cell.get("cell_type") != "code":
                    continue
                code = "\n".join(l for l in "".join(cell["source"]).splitlines()
                                 if "plt.show" not in l and "savefig" not in l)
                if not code.strip():
                    continue
                try:
                    exec(compile(code, str(NB), "exec"), ns)
                except Exception as e:
                    skipped.append(f"cell {i}: {type(e).__name__}: {str(e)[:40]}")
    finally:
        os.chdir(prev)
    return ns, skipped


def main():
    print("reproducing the notebook pipeline (spell-checking 100 tweets, ~20s) ...")
    ns, skipped = run_notebook_pipeline()
    if skipped:
        print(f"  cells skipped: {skipped}")

    df = ns.get("maindf")
    assert df is not None, "the notebook did not produce `maindf`"
    assert len(df) == 100, f"expected 100 tweets, found {len(df)}"
    assert "cleaned_text" in df and "sentiment" in df, \
        "the notebook no longer produces cleaned_text / sentiment"

    dist = df.sentiment.value_counts()
    print(f"\ndataset: {len(df)} tweets, VADER labels on cleaned text {dist.to_dict()}")

    y_te = ns.get("y_test")
    pred = ns.get("y_pred")
    assert y_te is not None and pred is not None, \
        "the notebook no longer exposes y_test / y_pred"

    n = len(y_te)
    k = int(accuracy_score(y_te, pred) * n + 0.5)
    acc = k / n
    counts = pd.Series(y_te).value_counts()
    baseline = counts.max() / n
    maj = counts.idxmax()

    lo, hi = stats.binomtest(k, n).proportion_ci(confidence_level=0.95)
    p_vs_base = stats.binomtest(k, n, baseline, alternative="greater").pvalue

    print(f"\ntest set: {n} tweets  {counts.to_dict()}")
    print(f"  accuracy                  {acc:.2f}  ({k}/{n})")
    print(f"  95% confidence interval   [{lo:.2f}, {hi:.2f}]   width {hi - lo:.2f}")
    print(f"  majority-class baseline   {baseline:.2f}  (predict '{maj}' always)")
    print(f"  vs baseline, binomial     p = {p_vs_base:.3f}"
          f"   {'significant' if p_vs_base < 0.05 else 'not significant'}")
    print(f"  one reclassified tweet moves accuracy by {1 / n:.2f}")

    # 1. the headline number is what the README says it is
    assert acc >= 0.85, f"notebook accuracy is now {acc:.2f}, README says ~0.90"

    # 2. the interval is far too wide to call it precise - the main caveat
    assert hi - lo > 0.20, (
        f"CI width is {hi - lo:.2f}; the README's 'too small to be stable' claim "
        f"would need revisiting")

    # 3. circularity: the labels ARE VADER's output
    full_pred = ns["nb_model"].predict(ns["vectorizer"].transform(df["cleaned_text"]))
    agreement = accuracy_score(df["sentiment"], full_pred)
    print(f"\n  agreement with VADER over all {len(df)} tweets: {agreement:.2f}")
    print("  The training labels ARE VADER's output, so high agreement is expected")
    print("  by construction and is not evidence of sentiment accuracy.")
    assert agreement > 0.5, "the model no longer reproduces its own training labels"

    # 4. the minority class is effectively absent from the test set
    neg = int((pd.Series(y_te) == "negative").sum())
    print(f"\n  'negative' instances in the test set: {neg}")
    assert neg <= 2, (
        f"{neg} negative test cases; the README's claim that the class is "
        f"effectively absent needs updating")

    # 5. sensitivity: labelling the RAW text instead changes the result
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    an = SentimentIntensityAnalyzer()

    def lab(t):
        c = an.polarity_scores(str(t))["compound"]
        return "positive" if c >= 0.05 else ("negative" if c <= -0.05 else "neutral")

    raw_labels = df["text"].map(lab)
    moved = int((raw_labels.values != df["sentiment"].values).sum())
    print(f"\n  labelling raw text instead of cleaned text moves {moved}/{len(df)} labels")
    print("  so the reported accuracy is specific to this preprocessing chain.")
    assert moved > 0, "preprocessing no longer affects the VADER labels"

    print("\nOK: the README's caveats about this result are confirmed numerically.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
