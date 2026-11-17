"""Verify the claims this project's README makes about the agent's performance.

The headline is that the PPO agent is beaten by doing nothing. That is an
arithmetic claim about the price series and two reported returns, so it can be
checked without retraining, which matters because training needs
stable-baselines3 and therefore Python <= 3.12, while this runs anywhere.

It also checks the two things that make the reported numbers unreliable: no
random seed, and evaluation on the training series.

Run:  python test_baseline.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
CSV = ROOT / "data" / "aapl_1984_2025.csv"
NB = ROOT / "notebooks" / "ppo_trading_agent.ipynb"
MODEL = ROOT / "models" / "ppo_trading_model.zip"

START_CASH = 10_000.0
REPORTED_FINAL = 11_593.01      # from the saved notebook run
TRAIN_TIMESTEPS = 10_000        # total_timesteps in the notebook

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
    df = pd.read_csv(CSV)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def data_is_as_described():
    df = load()
    assert len(df) == 10_171, f"expected 10,171 daily bars, found {len(df):,}"
    assert df.Date.iloc[0].date().isoformat() == "1984-09-07", \
        f"series starts {df.Date.iloc[0].date()}, not 1984-09-07"
    assert df.Date.iloc[-1].date().isoformat() == "2025-01-17", \
        f"series ends {df.Date.iloc[-1].date()}, not 2025-01-17"
    assert {"Open", "High", "Low", "Close", "Volume"} <= set(df.columns)
    assert (df.Close > 0).all(), "non-positive closing prices present"
    return f"{len(df):,} bars, {df.Date.iloc[0]:%Y-%m-%d} to {df.Date.iloc[-1]:%Y-%m-%d}"


def buy_and_hold_beats_the_agent():
    df = load()
    first, last = float(df.Close.iloc[0]), float(df.Close.iloc[-1])
    bh_multiple = last / first
    bh_final = START_CASH * bh_multiple
    agent_multiple = REPORTED_FINAL / START_CASH
    ratio = bh_final / REPORTED_FINAL

    assert bh_multiple > 1000, f"buy-and-hold multiple is only {bh_multiple:.1f}x"
    assert ratio > 100, (
        f"buy-and-hold is only {ratio:.1f}x the agent; the README claims ~2000x")
    print(f"        buy-and-hold  ${bh_final:>14,.0f}  ({100 * (bh_multiple - 1):>10,.0f}%)")
    print(f"        PPO agent     ${REPORTED_FINAL:>14,.2f}  "
          f"({100 * (agent_multiple - 1):>10.2f}%)")
    return f"buy-and-hold is {ratio:,.0f}x the agent's final value"


def training_is_shorter_than_one_episode():
    """One episode is a full pass through the series."""
    df = load()
    episode_len = len(df)
    epochs = TRAIN_TIMESTEPS / episode_len
    assert epochs < 1.0, (
        f"training covered {epochs:.2f} episodes; the README claims under one")
    return (f"{TRAIN_TIMESTEPS:,} timesteps over a {episode_len:,}-step episode "
            f"= {epochs:.2f} epochs")


def notebook_sets_no_seed():
    """Why the reported return is not reproducible."""
    src = json.loads(NB.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in src.get("cells", [])
                     if c.get("cell_type") == "code")
    # `def reset(self, seed=None)` and `super().reset(seed=seed)` are the Gym API
    # signature, not a seed being chosen, so they do not count.
    import re
    seeded = []
    for m in re.finditer(r"(set_random_seed|np\.random\.seed|random\.seed)\s*\(", code):
        seeded.append(m.group(1))
    for m in re.finditer(r"\bseed\s*=\s*([^\s,)]+)", code):
        if m.group(1) not in ("None", "seed"):
            seeded.append(f"seed={m.group(1)}")
    for m in re.finditer(r"\brandom_state\s*=\s*([^\s,)]+)", code):
        seeded.append(f"random_state={m.group(1)}")

    assert not seeded, (
        f"a seed is now set ({seeded}) - the README's claim that the result is "
        f"irreproducible is stale")
    assert "total_timesteps=10000" in code.replace(" ", ""), \
        "training length changed; update TRAIN_TIMESTEPS in this file"
    return "no seed anywhere, so each run gives a different return"


def no_train_test_split():
    src = json.loads(NB.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in src.get("cells", [])
                     if c.get("cell_type") == "code")
    assert "train_test_split" not in code, \
        "a split was added - update the README, which says there is none"
    # the env is constructed from the same df for training and evaluation
    assert code.count("TradingEnv(df)") >= 2, \
        "the env is no longer built from the same frame twice; re-check the claim"
    return "agent is evaluated on the series it trained on"


def saved_model_is_present():
    assert MODEL.exists(), f"{MODEL.name} is missing"
    kb = MODEL.stat().st_size / 1024
    assert kb > 50, f"{MODEL.name} is only {kb:.0f} KB, likely truncated"
    return f"{MODEL.name}, {kb:.0f} KB"


def main():
    print("RL trading agent: README claims\n")
    check("price series as described", data_is_as_described)
    check("buy-and-hold beats the agent", buy_and_hold_beats_the_agent)
    check("training under one episode", training_is_shorter_than_one_episode)
    check("no random seed set", notebook_sets_no_seed)
    check("no train/test split", no_train_test_split)
    check("trained model committed", saved_model_is_present)

    print(f"\n{sum(results)} of {len(results)} claims verified")
    if not all(results):
        return 1
    print("OK: every performance claim in the README checks out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
