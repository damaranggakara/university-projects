# Data provenance

Every dataset in this repository, where it came from, and why it is safe to publish.
Redistributing other people's data without stating its origin and terms is not acceptable,
and some of the source material for these projects was **not** publishable at all, and that is
recorded here too.

## Committed datasets

| Project | File | Source | Licence / terms |
|---|---|---|---|
| 02 | `biodata_pasien.xlsx` and four others | Synthetic, generated for the coursework | n/a, fabricated |
| 03 | `deadpool_wolverine_raw_tweets.csv` | Collected via the X/Twitter API v2, Nov 2024 | See note on X below |
| 04 | `tokopedia_raw.csv` | Scraped from Tokopedia search results, Sep 2025 | See note on scraping below |
| 05 | `real_estate.csv` | UCI ML Repository, *Real Estate Valuation* (Sindian, New Taipei City) | CC BY 4.0 |
| 06 | `diamonds.csv` | `ggplot2` diamonds dataset, widely redistributed | GPL-2 (as part of ggplot2) |
| 07 | `aapl_1984_2025.csv` | Daily AAPL OHLCV, 1984-2025 | Public market data; factual, not copyrightable |
| 09 | `ecommerce_raw.csv`, `ecommerce_cleaned.csv` | Kaggle, *E-commerce Consumer Behavior Analysis* | Synthetic dataset, public |
| 10 | `penguins.csv` | Palmer Penguins (Horst, Hill & Gorman) | CC0 |
| 10 | `boston.csv` | Boston housing, see the ethical note below | Public, deprecated |
| 10 | `survey_lung_cancer.csv` | Kaggle survey dataset | Public |
| 11 | `sample_image.jpeg` | Photograph taken by the author | Author's own |
| 12 | `hotel_0nf.xlsx` | Derived from a Kaggle hotel-reservations dataset | Public |
| 13 | `books.txt`, `borrowed_movies.csv`, `Reservasi.csv` | Hand-written test data | Author's own |
| 14 | `hepatitis_c.csv` | UCI ML Repository, *HCV data* | CC BY 4.0 |
| 14 | `diabetes_brfss2015_sample.csv` | CDC BRFSS 2015 via Kaggle, stratified 20% sample | US public domain (CDC) |
| 08 | `customer_feedback.csv` | Coursework sample for the prompt-engineering exercise | Public |

## Fetched, not committed

| Project | File | How |
|---|---|---|
| 14 | `diabetes_brfss2015.csv` (253,680 rows, 22 MB) | `python 14-clinical-prediction/fetch_data.py` |
| 08 | four research PDFs (~8 MB) | see `08-rag-llm-applications/data/papers/README.md` |

22 MB of publicly available data was most of this repository's size, so it is fetched on
demand. It is listed in `.gitignore` so it cannot be committed back by accident. The
stratified sample preserves the class distribution exactly, so the notebooks run on a fresh
clone without it.

## Judgement calls and exclusions

**Credit risk (project 01): included, after an earlier exclusion was found to be mistaken.**

An earlier assessment of this file was wrong and is corrected here. The source is
`Data RMRM (confidential).xlsx`, 2,700 survey responses across five banking institutions,
and it was initially excluded on the belief that its `Nama` column held customer names;
*nama* is Indonesian for "name", and the filename says confidential.

It does not. The file is **already anonymised at source**:

| Column | Contents |
|---|---|
| `IDR` | sequential respondent id, 1-2700 |
| `IDR1` | respondent index within bank, 1-100 |
| `No Bank` | branch number, 1-27 |
| `Nama` | the **bank's** pseudonym, `Bank XA` through `Bank XE` |

There are no personal names, addresses or phone numbers in any of the 208 columns; the rest
are coded questionnaire items about credit behaviour. Re-identification risk is low.

What remains is a permissions question rather than a privacy one: the file is labelled
confidential and came from a third party. It is committed here as
`01-credit-risk-analysis/data/credit_risk_survey.xlsx` on the author's judgement that the
anonymisation above makes it publishable; if the originating institution says otherwise it
should be removed and the project reduced to its code.

**`kaggle.json`** and any `.env` file are gitignored. An earlier version of the coursework
had X/Twitter API keys, a Redshift password, two Google API keys and database passwords
hardcoded in notebooks; all have been replaced with environment lookups and the credentials
revoked. CI enforces this; see `.github/workflows/checks.yml`.

## Notes

**X/Twitter data.** The 100 tweets were collected under the free API tier in November 2024.
X's terms restrict redistribution of tweet *content*; the file is retained here because it
is a small academic sample and the project cannot otherwise be reproduced at all: the
endpoint now requires a paid tier. If that is a concern it should be replaced with tweet IDs
for rehydration, which is the convention the research community uses.

**Scraped data.** The Tokopedia extract is 60 product listings gathered once for a
coursework exercise. Live scraping in the notebook is opt-in (`LIVE_SCRAPE=1`) and off by
default, so running the project does not generate traffic against their site.

**Boston housing.** This dataset contains a feature engineered as a proxy for the proportion
of Black residents in a neighbourhood, and it was constructed to demonstrate that
association. `scikit-learn` removed it in version 1.2 for this reason. It appears here only
because the Semester 4 coursework used it as a regression target, and it is kept so the
original work is reproducible rather than endorsed. New work should use California housing
or the Ames dataset.

**Patient data in project 02.** Verified synthetic before committing: one patient row named
"John Doe", UUID identifiers, a single doctor "Dr. Andi", and generic diagnoses. The
remaining 60 patients are generated by `build_warehouse.py` from fixed name lists under a
seeded RNG.
