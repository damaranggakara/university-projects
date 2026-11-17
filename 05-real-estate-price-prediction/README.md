# Real Estate Price Prediction (Ensemble Learning)

Predicting housing price per unit area from location and property features, comparing
four regression models with hyperparameter tuning.

## Dataset

UCI "Real Estate Valuation" dataset (Sindian District, New Taipei City), 414 transactions,
6 predictors:

| Feature | Description |
|---|---|
| X1 | Transaction date |
| X2 | House age (years) |
| X3 | Distance to nearest MRT station (m) |
| X4 | Number of nearby convenience stores |
| X5 / X6 | Latitude / longitude |
| **Y** | **House price per unit area** (target) |

## Method

1. Drop index column, convert the fractional transaction date to a timestamp
2. EDA: distributions, boxplots, price-over-time trend, correlation heatmap
3. 80/20 train/test split, `StandardScaler` on features
4. Four regressors, with `GridSearchCV` (5-fold, scored on R²) on Random Forest and SVR
5. Compare on MSE and R²

## Results

Test-set performance as the notebook runs it:

| Model | MSE | R² |
|---|---|---|
| Random Forest (tuned) | 32.53 | 0.806 |
| SVR (tuned) | 35.82 | 0.786 |
| **Gradient Boosting** | **31.69** | **0.811** |
| LightGBM | 34.70 | 0.793 |

Gradient Boosting performs best. Distance to the nearest MRT station is the dominant
predictor, which matches the intuition that transit access drives Taipei-area prices.

### What hyperparameter tuning actually bought

Grid search was measured against each model's default settings:

| Model | Default R² | Tuned R² | Change |
|---|---|---|---|
| Random Forest | 0.794 | 0.806 | +1.5% |
| SVR | 0.679 | 0.787 | **+15.9%** |
| Gradient Boosting | 0.811 | 0.790 | −2.6% |
| LightGBM | 0.793 | 0.778 | −1.9% |

Tuning helped SVR substantially and Random Forest marginally, and slightly *hurt* the two
boosting models; on a dataset this small (331 training rows) a 5-fold grid search can
select parameters that do not generalise to the held-out set. The honest conclusion is
that defaults were already competitive for the boosting models.

## Running it

```bash
pip install -r requirements.txt
jupyter notebook notebooks/real_estate_ensemble.ipynb
```

Data path is relative, no configuration needed.

## Notes

Coursework for Analisis Prediksi dan Prognosis (Prediction & Prognosis Analysis),
Semester 4. Individual work. Verified to run end-to-end on Python 3.14 with the pinned
dependencies above.
