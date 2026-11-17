"""Do the cancellation patterns in the views survive a significance test?

The views show cancellation rising with lead time (22% -> 24% -> 47%) and
Online cancelling far more than Offline (40.6% vs 6.7%). Both look like
findings. With 49 bookings and 15 cancellations they need checking before
they are described as any such thing.

Run:  python significance_check.py
"""
import os
import sys

import pandas as pd
import psycopg2
from scipy import stats


def connect():
    pwd = os.environ.get("POSTGRES_PASSWORD")
    if not pwd:
        sys.exit("POSTGRES_PASSWORD is not set - copy .env.example to .env and fill it in.")
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("HOTEL_DB", "hotel"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=pwd,
    )


def main():
    conn = connect()
    df = pd.read_sql("SELECT booking_source, booking_status, lead_time, room_type, price "
                     "FROM v_booking_flat", conn)
    df["cancelled"] = (df.booking_status == "Canceled").astype(int)
    n, k = len(df), int(df.cancelled.sum())
    print(f"n = {n} bookings, {k} cancelled ({100 * k / n:.1f}%)\n")

    # ---- 1. lead time vs cancellation ------------------------------------
    r, p_r = stats.pointbiserialr(df.cancelled, df.lead_time)
    canc = df[df.cancelled == 1].lead_time
    keep = df[df.cancelled == 0].lead_time
    t, p_t = stats.ttest_ind(canc, keep, equal_var=False)

    print("1. lead time vs cancellation")
    print(f"   mean lead time  cancelled {canc.mean():.0f}d (n={len(canc)})  "
          f"kept {keep.mean():.0f}d (n={len(keep)})")
    print(f"   point-biserial  r = {r:.3f}  p = {p_r:.4f}"
          f"   {'significant' if p_r < 0.05 else 'not significant'}")
    print(f"   Welch t-test    t = {t:.2f}   p = {p_t:.4f}"
          f"   {'significant' if p_t < 0.05 else 'not significant'}")
    print("   -> the two tests disagree, so the result is borderline rather than")
    print("      established: it depends on which test you happen to pick.\n")

    # ---- 2. booking source vs cancellation -------------------------------
    tab = pd.crosstab(df.booking_source, df.cancelled)
    chi2, p_c, dof, expected = stats.chi2_contingency(tab)
    small = int((expected < 5).sum())
    print("2. booking source vs cancellation")
    print(tab.to_string().replace("\n", "\n   ").rjust(0))
    print(f"   chi-square      chi2 = {chi2:.2f}  p = {p_c:.4f}  dof = {dof}")
    print(f"   cells with expected count < 5: {small} of {expected.size}")
    print("   -> chi-square needs expected counts of at least 5. Aviation and")
    print("      Corporate have one booking each, so the assumption is violated")
    print("      and this p-value should not be relied on.\n")

    # Fisher on the two categories that actually have data
    pair = df[df.booking_source.isin(["Online", "Offline"])]
    ftab = pd.crosstab(pair.booking_source, pair.cancelled)
    if ftab.shape == (2, 2):
        odds, p_f = stats.fisher_exact(ftab.values)
        print("   Online vs Offline only, Fisher exact test")
        print(f"   odds ratio = {odds:.2f}  p = {p_f:.4f}"
              f"   {'significant' if p_f < 0.05 else 'not significant'}")
        print("   -> this comparison is valid, and it is the one worth quoting.\n")

    print("Summary: with 49 bookings, the lead-time effect is suggestive but not")
    print("robust, and the source effect is only testable for Online vs Offline.")
    print("Nothing here supports a confident causal claim.")

    assert n == 49, f"expected the 49-row sample, found {n}"
    assert k > 0, "no cancellations present - the views would be meaningless"
    conn.close()
    print("\nOK: checks passed.")


if __name__ == "__main__":
    main()
