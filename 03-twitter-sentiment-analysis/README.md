# Twitter Movie Sentiment Analysis

End-to-end NLP pipeline: collect tweets about *Deadpool & Wolverine* from the X/Twitter
API, clean and normalise the text, score sentiment with VADER, train a Naive Bayes
classifier on those labels, and load the results into a data warehouse.

## Pipeline

1. **Collection**: `tweepy` against the X API v2 recent-search endpoint,
   query `#DeadpoolAndWolverine -is:retweet lang:en`
2. **Preprocessing**: strip URLs, mentions, hashtags, digits and punctuation;
   tokenise and lowercase; spell-correct with `pyspellchecker`; remove English stopwords
3. **Sentiment labelling**: VADER compound score, thresholded at ±0.05 into
   positive / neutral / negative
4. **Classification**: `CountVectorizer` bag-of-words into Multinomial Naive Bayes
5. **Visualisation**: separate word clouds for positive and negative tweets
6. **Storage**: load to AWS Redshift and to MySQL via SQLAlchemy

## Dataset

`data/deadpool_wolverine_raw_tweets.csv`, **100 tweets** collected 23 November 2024,
with `created_at`, `text`, `retweets`, `likes`, `author_id`.

VADER labelled them: **13 positive, 6 neutral, 1 negative** in the held-out test split
(20 tweets), with the same skew across the full set.

## Results

Multinomial Naive Bayes, 80/20 split:

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| negative | 0.00 | 0.00 | 0.00 | 1 |
| neutral | 0.86 | 1.00 | 0.92 | 6 |
| positive | 0.92 | 0.92 | 0.92 | 13 |
| **Accuracy** | | | **0.90** | **20** |
| Macro avg | 0.59 | 0.64 | 0.62 | |

**How much to read into this.** The 90% accuracy sits on a 20-tweet test set, which is far
too small to be a stable estimate; one reclassified tweet moves it by five points. The
negative class has a single test instance and is never predicted correctly, so macro F1
(0.62) is the honest summary rather than accuracy.

There is also a structural caveat worth stating: the Naive Bayes model is trained on labels
that VADER produced, so it is learning to imitate a lexicon-based rule, not to predict
human judgement. High agreement with VADER is therefore expected and is not evidence of
real sentiment accuracy. Validating against hand-labelled tweets would be the meaningful
next step, along with collecting enough data to balance the classes.

## Running it

```bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt_tab')"
jupyter notebook notebooks/twitter_sentiment.ipynb
```

The notebook runs from the saved CSV out of the box. Live collection and the warehouse
loads are opt-in and skip cleanly when their credentials are absent:

| Variable | Enables |
|---|---|
| `TWITTER_BEARER_TOKEN` + `LIVE_COLLECTION=1` | fresh tweet collection |
| `REDSHIFT_HOST` / `_USER` / `_PASSWORD` | Redshift load |
| `MYSQL_PASSWORD` | MySQL load |

Live collection now requires a paid X API tier, so the saved dataset is the reproducible
path.

## Notes

Coursework for Metode Sains Data II (Data Science Methods II), Semester 3, final
practical exam (UAP). Individual work.

The original notebook had the X API keys, AWS Redshift credentials and the MySQL password
written inline. All of them have been replaced with environment-variable lookups; no
credential values are present in this repository.
