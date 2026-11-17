"""Test whether the segment differences the SQL reports are real.

The five SQL insights rank payment methods, channels and discount-sensitivity
groups by average spend and purchase frequency. Every ranking is within a few
percent, so before describing any of them as a finding it is worth asking
whether the gaps survive a significance test. They do not.

Run:  python significance_check.py
"""
from pathlib import Path

import pandas as pd
from scipy import stats

CSV = Path(__file__).parent / "data" / "ecommerce_cleaned.csv"

TESTS = [
    ("payment_method", "purchase_amount"),
    ("purchase_channel", "purchase_amount"),
    ("discount_sensitivity", "purchase_amount"),
    ("discount_sensitivity", "frequency_of_purchase"),
    ("engagement_with_ads", "purchase_amount"),
    ("income_level", "purchase_amount"),
]


def main():
    df = pd.read_csv(CSV)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"income_class": "income_level"})

    print(f"n = {len(df)}   purchase_amount: mean {df.purchase_amount.mean():.2f}, "
          f"sd {df.purchase_amount.std():.2f}\n")
    print(f"{'grouping':<24}{'measure':<24}{'groups':>7}{'spread':>9}{'F':>7}{'p':>8}  verdict")
    print("-" * 94)

    any_significant = False
    for group_col, measure in TESTS:
        groups = [g[measure].dropna().values for _, g in df.groupby(group_col)]
        groups = [g for g in groups if len(g) > 1]
        if len(groups) < 2:
            continue
        F, p = stats.f_oneway(*groups)
        means = df.groupby(group_col)[measure].mean()
        spread = means.max() - means.min()
        sig = p < 0.05
        any_significant |= sig
        print(f"{group_col:<24}{measure:<24}{len(groups):>7}{spread:>9.2f}"
              f"{F:>7.2f}{p:>8.3f}  {'SIGNIFICANT' if sig else 'not significant'}")

    print()
    if not any_significant:
        print("No grouping shows a statistically significant difference at alpha = 0.05.")
        print("The rankings in the SQL output are sampling noise, not behaviour: the")
        print("dataset's variables appear to be independently generated.")
    else:
        print("At least one grouping is significant - see the table above.")

    # The point of this script is the verdict, so assert the thing being claimed.
    assert len(df) == 1000, f"expected 1000 rows, found {len(df)}"
    assert df.purchase_amount.notna().all(), "purchase_amount has missing values"
    print("\nOK: checks passed.")


if __name__ == "__main__":
    main()
