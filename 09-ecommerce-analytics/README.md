# E-commerce Consumer Behaviour Analytics

An end-to-end analytics pipeline: clean a raw consumer-behaviour dataset in pandas, load it
into PostgreSQL, and answer five business questions in SQL. Final project for the Semester 6
data science track.

## Pipeline

```
data/ecommerce_raw.csv  ──▶  notebooks/data_cleaning.ipynb  ──▶  data/ecommerce_cleaned.csv
                                                                        │
                                              load_to_postgres.py  ◀────┘
                                                        │
                                                        ▼
                                        public.ecommerce_cleaned (PostgreSQL)
                                                        │
                                              notebooks/sql_insights.ipynb
```

**Dataset**: 1,000 customers, 28 raw columns → 32 after cleaning: demographics (age,
gender, income, education, marital status, location), behaviour (purchase category, amount,
frequency, channel, payment method, brand loyalty), and attitudinal fields (discount
sensitivity, ad engagement, purchase intent). Cleaning derives calendar features
(month, quarter, day of week) and reclassifies income into bands.

## The five SQL insights

| # | Question |
|---|---|
| 1 | Average purchase amount by age group × gender × income level |
| 2 | Purchase frequency by discount sensitivity |
| 3 | Purchase intent vs engagement with ads |
| 4 | Most used payment method, by transactions and revenue |
| 5 | Best performing purchase channel |

Sample output (insight 4):

```
  payment_method   transactions   avg_value   total_revenue
0 PayPal                    219      278.38        60964.33
1 Other                     204      283.32        57797.50
2 Debit Card                196      273.22        53552.04
3 Credit Card               194      271.53        52677.54
4 Cash                      187      267.77        50072.47
```

## The finding that matters: none of it is significant

Read the table above and the obvious write-up is "PayPal is the top-performing payment
method". That would be wrong, and the reason is worth more than the ranking itself.

Purchase amount has a standard deviation of **131.53** on a mean of 275.06, with roughly
200 customers per payment method. A 15-unit spread across group means is well inside
sampling noise. `significance_check.py` runs a one-way ANOVA on each grouping:

```
grouping                measure                  groups   spread      F       p
payment_method          purchase_amount               5    15.55   0.42   0.792
purchase_channel        purchase_amount               3     9.05   0.40   0.669
discount_sensitivity    purchase_amount               3    14.66   1.02   0.362
discount_sensitivity    frequency_of_purchase         3     0.27   0.60   0.551
engagement_with_ads     purchase_amount               4    12.95   0.45   0.719
income_level            purchase_amount               2     5.73   0.47   0.491
```

**Not one grouping is significant at α = 0.05**, and the p-values are not marginal, they
run from 0.36 to 0.79. Even "very sensitive" versus "not sensitive" shoppers differ by 0.27
purchases a year.

The dataset's variables appear to have been generated independently of one another, so no
relationship exists to be found. The SQL is correct and the aggregations are right; what
would be wrong is treating the ordering as behaviour. A ranked table always produces a
winner, which is exactly why the significance test has to come before the narrative.

If this were real data, the next step would be effect sizes and confidence intervals rather
than more segmentation.

## Running it

```bash
pip install -r requirements.txt
createdb ecommerce                       # or CREATE DATABASE ecommerce;

jupyter notebook notebooks/data_cleaning.ipynb    # raw -> cleaned CSV
python load_to_postgres.py                        # cleaned CSV -> PostgreSQL
jupyter notebook notebooks/sql_insights.ipynb     # the five queries
python significance_check.py                      # the ANOVA table above
```

Credentials come from the environment; see `.env.example` at the repository root:

| Variable | Default |
|---|---|
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PASSWORD` | *(required)* |
| `ECOMMERCE_DB` | `ecommerce` |

## Two things the original was missing

**No load step.** `Data Cleaning.ipynb` wrote a CSV and `SQL Insights.ipynb` queried
`public.ecommerce_cleaned`, but nothing in the project ever created that table; it only
ran if the CSV had been imported by hand in pgAdmin. `load_to_postgres.py` closes the gap,
and reconciles two mismatches between the two halves: the CSV calls the income band
`Income_Class` while the SQL calls it `income_level`, and PostgreSQL folds unquoted
identifiers to lower case.

**A dialect difference.** The queries use `ROUND(AVG(purchase_amount), 2)`. In MySQL that
works on floats; in PostgreSQL two-argument `round()` is defined only for `numeric`, not
`double precision`, so every insight failed with
`function round(double precision, integer) does not exist`. Rather than edit six queries,
the loader maps float columns to `NUMERIC`, fixing it once at the boundary.

The loader asserts row count, required columns, and that non-ASCII place names survive the
round-trip (197 of the 1,000 locations contain accented characters).

## Notes

Coursework for the Semester 6 final project. The cleaning notebook and the five SQL queries
are the original submission; `load_to_postgres.py` and `significance_check.py` are
additions, kept as separate files so the difference is visible.

The original connected with a hardcoded password; all credentials are now environment
variables.
