# Diamond Price Prediction (Artificial Neural Network)

A feedforward neural network predicting diamond price from physical attributes, with
K-Means used beforehand to explore how price segments against each predictor.

## Dataset

`data/diamonds.csv`, 53,940 diamonds, semicolon-delimited.

| Column | Meaning |
|---|---|
| carat | weight |
| depth | total depth percentage |
| table | width of top relative to widest point |
| quality | cut grade (Fair / Good / Very Good / Premium / Ideal) |
| **price** | **target, USD** |

`quality` is lowercased and mapped to an ordinal `quality_numeric` (fair=1 … premium=5),
giving four numeric predictors.

## Method

1. Ordinal-encode `quality`, check for nulls
2. K-Means (k=5) on price against each predictor in turn, to visualise segmentation
3. 80/20 split, `StandardScaler` on predictors
4. Feedforward network: **64 → 32 → 16 → 8 → 1**, ReLU throughout, linear output
5. Adam optimiser, MSE loss, MAE tracked, with a validation split

## Results

| Metric | Model | Predict-the-mean baseline |
|---|---|---|
| MAE | **$780** | $3,032 |
| RMSE | **$1,366** | $3,989 |

**R² = 0.883**: the network explains 88% of price variance from four features, and cuts
mean absolute error to roughly a quarter of the naive baseline.

Context for the $780: mean diamond price is $3,933 (sd $3,989, range $326-$18,823), so
average error is about **20% of the mean price**. That is a solid result for four
predictors, but it is worth being precise about rather than calling it "high accuracy",
the figure a reader can check is R² 0.883, and the error is proportionally largest on
cheap stones.

The obvious improvement is features rather than architecture: this copy of the dataset
omits the standard `cut`, `color`, `clarity` and `x/y/z` dimensions, and clarity in
particular is a strong price driver. A gradient-boosting model on the full feature set
would very likely beat this network.

## Running it

```bash
pip install -r requirements.txt
jupyter notebook notebooks/diamond_price_ann.ipynb
```

**Needs Python 3.12 or earlier.** TensorFlow has no release supporting Python 3.13 or 3.14.

## Notes

Coursework for Metode Sains Data I (Data Science Methods I), Semester 2. Individual work.
Verified end to end on Python 3.12.10 with TensorFlow 2.18.
