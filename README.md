# University Projects

[![checks](https://github.com/damaranggakara/university-projects/actions/workflows/checks.yml/badge.svg)](../../actions/workflows/checks.yml)

Selected projects from my undergraduate Data Science programme (Statistics / Data Science,
Semesters 1-6). Each folder is self-contained: data, notebooks, a README explaining the
problem and findings, pinned dependencies, and a verification script.

**Every project in this repository has been executed end to end on current library versions,
not just archived.** Where a project doesn't work, or where its original results don't hold
up, the README says so; several of them document bugs I found in my own coursework while
getting it to run.

## Projects

| # | Project | Domain | Key tools | Status |
|---|---|---|---|---|
| 01 | [Credit Risk Analysis](01-credit-risk-analysis/) | Banking / risk | sklearn, XGBoost, SMOTE, lifelines | **runs clean** |
| 02 | [Pediatric Health Data Warehouse](02-pediatric-data-warehouse/) | Health / data eng | PostgreSQL, 1NF-3NF, star schema | **runs clean** |
| 03 | [Twitter Movie Sentiment](03-twitter-sentiment-analysis/) | NLP | NLTK, VADER, Naive Bayes | **runs clean** |
| 04 | [Tokopedia Scraper + ETL](04-tokopedia-scraper-etl/) | Web scraping / ETL | Selenium, BeautifulSoup, SQLite | **runs clean** |
| 05 | [Real Estate Price Prediction](05-real-estate-price-prediction/) | Regression | RF, SVR, GBM, LightGBM, GridSearch | **runs clean** |
| 06 | [Diamond Price Prediction (ANN)](06-diamond-price-ann/) | Deep learning | TensorFlow / Keras | **runs clean** (Python ≤3.12) |
| 07 | [Apple Stock Trading Bot](07-rl-trading-agent/) | Reinforcement learning | PPO, stable-baselines3, custom Gym env | **runs clean** (Python ≤3.12) |
| 08 | [RAG / LLM Applications](08-rag-llm-applications/) | GenAI | LangChain, LangGraph, FAISS, Gemini | needs an API key |
| 09 | [E-commerce Consumer Analytics](09-ecommerce-analytics/) | Analytics | pandas, PostgreSQL, SQL | **runs clean** |
| 10 | [ML Methods Survey](10-ml-methods-survey/) | ML comparison | K-Means, AGNES, DIANA, SOM, SVM, KNN, NB, DT, ANN | **runs clean** |
| 11 | [Image Compression](11-image-compression/) | Information theory | DCT, Hamming(7,4), OpenCV | **runs clean** |
| 12 | [Hotel Normalisation + ETL](12-hotel-etl-normalisation/) | Data engineering | PostgreSQL, SQLAlchemy, 0NF→3NF | **runs clean** |
| 13 | [Python Software Engineering](13-python-software-engineering/) | OOP / web | Flask, Tkinter, CGI, packages | **runs clean** |
| 14 | [Clinical Prediction Set](14-clinical-prediction/) | Health ML | sklearn, XGBoost, ensembles | **runs clean** |
| 15 | [Symbolic AI](15-symbolic-ai/) | Classical AI | FOL inference, partial-order planning, fuzzy logic | **runs clean** |

## A few things worth opening first

If you only read one: **[02 Pediatric Data Warehouse](02-pediatric-data-warehouse/notebooks/normalisation_to_warehouse.ipynb)**
walks 1NF→2NF→3NF against a live PostgreSQL schema, calculates the 9,261× fan trap that
made the original fact table impossible, and demonstrates the constraints by deliberately
getting four inserts rejected. **[12 Hotel Normalisation](12-hotel-etl-normalisation/notebooks/normalisation_to_postgres.ipynb)**
does the same for 0NF→3NF on a simpler schema.

- **[11 Image Compression](11-image-compression/)**: found a real bug in my own
  Hamming(7,4) decoder. The syndrome bits were assembled in reverse, so it recovered 71.4%
  of single-bit errors instead of 100% and corrected PSNR *down* from 31.9 dB to 6.9 dB.
  `test_hamming.py` proves it over all 112 single-error cases, and an error-rate sweep shows
  the residual gap afterwards is Hamming's design limit rather than a second bug.
- **[09 E-commerce Analytics](09-ecommerce-analytics/)**: the five SQL insights rank
  payment methods and channels by spend. One-way ANOVA on every grouping returns p = 0.36 to
  0.79, **nothing is significant**, and the rankings are noise. A ranked table always
  produces a winner, which is why the test comes before the narrative.
- **[10 ML Methods Survey](10-ml-methods-survey/)**: four classifiers ranked SVM > NB >
  KNN > Decision Tree. On the single 93-row test set no pair differs significantly by
  McNemar, every CI overlaps, and the Decision Tree scores *below* a majority-class
  baseline. Across 50 repeated splits SVM does genuinely lead (43/50 first place,
  p = 1.8e-19), but 4 to 7 points of each reported accuracy was split luck.
- **[14 Clinical Prediction](14-clinical-prediction/)**: a tuned Random Forest reaches
  86.2% accuracy on diabetes screening. Always predicting "non-diabetic" reaches 85.8%. The
  model finds 16% of actual diabetics, so 1,080 grid-search fits bought 0.39 percentage
  points over a constant predictor.
- **[01 Credit Risk](01-credit-risk-analysis/)**: four classifiers report 97-99% accuracy
  on 2,700 borrowers. A model predicting "everyone repays" scores 98.70%, and all four
  identify **0 of 7 defaults**, one scores *below* the constant predictor and XGBoost's
  ROC AUC is 0.432, worse than random.
- **[07 RL Trading Agent](07-rl-trading-agent/)**: the PPO agent returns 15.9% on AAPL
  over 1984-2025. Buy-and-hold returns 230,286%. The README works through why: under one
  epoch of training, a reward that tolerates idleness, and no train/test split. It also notes the
  result is not even reproducible, since no seed is set.

## Verification

Every project carries an assert-based check. One command runs all of them:

```bash
python run_checks.py              # everything available
python run_checks.py --no-db      # skip the four needing PostgreSQL
python run_checks.py -k hamming   # filter by name
```

```
10 passed, 0 failed, 0 skipped
```

CI runs the same script on every push against a PostgreSQL 17 service container, and also
enforces that notebooks are valid and carry saved outputs, and that no credential or local
path has been committed, all three have gone wrong here before, so they are checked rather
than remembered.

## Environment

| | |
|---|---|
| Python | **3.12** for everything; 3.14 also works except projects 06 and 07 |
| Why | TensorFlow and stable-baselines3 have no release supporting 3.13+ |
| Database | PostgreSQL 17 for projects 02, 09 and 12; project 04 uses SQLite (no server) |

Dependencies are pinned per project, since the set varies widely and installing all of them
at once is unnecessary for any single one:

```bash
cd 05-real-estate-price-prediction
pip install -r requirements.txt
```

Credentials come from the environment. Copy `.env.example` to `.env` and fill in what you
need; `.env` is gitignored.

## Conventions

```
NN-project-name/
├── README.md              the problem, the method, the results, and the caveats
├── requirements.txt       pinned, project-specific
├── data/                  committed where licensing permits (see DATA.md)
├── notebooks/             executed, with outputs saved
├── sql/                   DDL and views, where a database is involved
└── <check>.py             assert-based verification, run by run_checks.py
```

**Notebook outputs are committed deliberately.** The cost is unreadable diffs, marked
`-diff` in `.gitattributes`. The benefit is that the analysis and its results are visible on
GitHub without anyone installing anything, which for a portfolio matters more.

**Original coursework is preserved.** Where I rebuilt something, the original notebook stays
alongside it (with credentials redacted) so the before and after are both readable. Added
files are kept separate from original ones rather than folded in, and each README says which
is which.

## Data and licensing

Code is MIT ([LICENSE](LICENSE)). The datasets are third-party material under their own
terms. **[DATA.md](DATA.md)** records the source and licence of each one, which files are
fetched rather than committed, and one dataset that is deliberately excluded because it
contains real named individuals.

## Honest limitations

- Project 08's notebooks are **not executed** and have no saved outputs: every cell calls a
  paid API. Everything else in this repository runs and its results are committed.
- Projects 03, 04 and 07 depend on APIs or sites that have changed since the work was done.
  Live collection is opt-in and off by default; the analyses run from archived extracts.
- Several datasets are synthetic coursework data, and a few are internally inconsistent in
  ways the relevant README describes. Where that undermines a result, the README says so
  rather than quoting the number.
- Projects 11, 13 and 15 are coursework in information theory, software engineering and
  classical AI rather than statistics, included because the range is the point.
