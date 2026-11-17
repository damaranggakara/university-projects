# Apple Stock Trading Agent (Reinforcement Learning)

A PPO agent trained in a custom OpenAI Gym environment to make buy / sell / hold decisions
on Apple stock.

## Environment

`TradingEnv` is written from scratch as a `gym.Env`:

- **Observation**: current price and portfolio state (cash balance, shares held)
- **Actions**, discrete: buy, sell, hold
- **Reward**: change in total asset value (cash + shares at market price)
- **Episode**: one pass through the price series, starting from $10,000 cash

Agent: `PPO("MlpPolicy")` from stable-baselines3, `total_timesteps=10000`.

## Data

`data/aapl_1984_2025.csv`, 10,171 daily AAPL bars, **1984-09-07 to 2025-01-17**
(Open/High/Low/Close/Volume). Close rises from $0.0998 to $229.98 over the period.

## Results, and the problem with them

Evaluation over 10,160 steps:

| | $10,000 becomes | Return |
|---|---|---|
| **Buy and hold** | **$23,038,571** | **+230,286%** |
| PPO agent (saved run) | $11,593 | +15.93% |
| PPO agent (re-run here) | $10,165 | +1.65% |

Two things follow, and both matter more than the headline number.

**The agent is comprehensively beaten by doing nothing.** Holding AAPL from 1984 to 2025
returns about 230,000%; the agent returns 1.7-16%. That is roughly a **2,000x** shortfall
against the simplest possible baseline. For a long-only strategy on a single appreciating
asset, buy-and-hold is the benchmark, and the notebook does not implement it.

**The result is not reproducible.** No random seed is set anywhere, so retraining moves the
outcome from 15.93% to 1.65%, a tenfold spread on identical code and data. Any single
reported figure from this notebook is one sample from a wide distribution.

### Why it underperforms

- **Training is shorter than one episode.** `total_timesteps=10000` against a 10,171-step
  series means the agent sees the data less than once end to end. PPO on a task like this
  needs orders of magnitude more interaction.
- **Reward encourages inaction.** Per-step change in asset value, with no penalty for
  holding cash, lets a mostly-idle policy score near zero rather than negative, so there
  is weak pressure to find a profitable strategy.
- **No train/test split.** The agent is evaluated on the same series it trained on, so even
  a good score would not demonstrate generalisation.
- **Non-stationary target.** 41 years spanning several market regimes, with price moving
  three orders of magnitude, fed to a policy with no normalisation of the observation.

### What would make it a fair experiment

Set a seed; split train and test chronologically; add buy-and-hold and random-action
baselines; normalise observations to returns rather than raw prices; train for millions of
timesteps; and report the mean and spread across several seeds instead of one run.

## Running it

```bash
pip install -r requirements.txt
jupyter notebook notebooks/ppo_trading_agent.ipynb
```

**Needs Python 3.12 or earlier.** `models/ppo_trading_model.zip` is the originally trained
agent; re-running the notebook overwrites it.

## Notes

Group coursework (Kelompok 5, Tugas Case Based) for Pembelajaran Mesin, Semester 4. Three
near-identical copies existed in the archive; the group's final submission is the one kept
here. Verified end to end on Python 3.12.10 with stable-baselines3 2.4.0.

The environment, reward design and evaluation loop are original work. The critique above is
added analysis, not part of the original submission.
