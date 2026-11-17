# Clinical Risk Prediction

Two supervised-learning studies on clinical datasets: staging liver disease from blood
panels, and screening diabetes risk from a large health-survey dataset.

## 1. Hepatitis C Staging (ensemble methods)

**Dataset**: UCI HCV data, 615 patients. Features are age, sex and 10 serum markers
(ALB, ALP, ALT, AST, BIL, CHE, CHOL, CREA, GGT, PROT). Target is a 5-class diagnosis:
blood donor, suspect donor, hepatitis, fibrosis, cirrhosis.

**Method**: preprocessing and imputation, then Logistic Regression, Random Forest, SVC
and XGBoost as base learners, combined three ways: hard voting, soft voting, and a
stacking classifier.

**Results**

| Ensemble | Accuracy | Precision | Recall | F1 | ROC AUC |
|---|---|---|---|---|---|
| Hard voting | 0.886 | 0.871 | 0.886 | 0.859 | n/a |
| **Soft voting** | **0.903** | 0.894 | 0.903 | 0.890 | **0.970** |
| Stacking | 0.892 | 0.877 | 0.892 | 0.874 | 0.961 |

**Reading these numbers honestly.** The headline 90% accuracy is inflated by severe class
imbalance. The test set is 153 blood donors against 3, 10, 8 and 11 cases in the four
disease classes, so a classifier that mostly predicts "healthy" scores well on accuracy
while being clinically useless. The per-class breakdown shows this plainly:

- Class 0 (blood donor): F1 = 0.96
- Class 1 (suspect donor): F1 = **0.00**, never correctly predicted, only 3 test cases
- Class 2 (hepatitis): F1 = 0.43
- Class 3 (fibrosis): F1 = 0.35
- Class 4 (cirrhosis): F1 = 0.71

Macro-average F1 is 0.49-0.56 depending on the ensemble, against a weighted average of
0.87-0.89. Macro average is the figure that matters here. The rarest class has only 4
instances in the entire dataset, which is fewer than the 5 cross-validation folds, so its
estimates are not meaningful at all.

The appropriate next step would be stratified resampling (SMOTE or class weights) and
reporting per-class recall as the primary metric, since missing a cirrhosis case costs far
more than a false positive.

## 2. Diabetes Risk Classification

**Dataset**: CDC BRFSS 2015 health indicators, ~253,000 respondents, 21 features
(BMI, blood pressure, cholesterol, smoking, physical activity, general health self-rating
and demographics). Target is a 3-class diabetes indicator.

**Method**: class 1 (pre-diabetes) is dropped, leaving a binary problem. Random Forest
tuned with `GridSearchCV` over `n_estimators`, `max_depth`, `min_samples_split`,
`min_samples_leaf` and `bootstrap`.

**Data**: the repository commits a **stratified 20% sample** (50,736 rows, 4.6 MB) that
preserves the class distribution exactly (84.2 / 1.8 / 13.9). The full 253,680-row file is
22 MB of publicly available CDC data, so it is fetched rather than stored:
`python fetch_data.py`. The notebook prefers the full file when present and falls back to
the sample, so it runs on a fresh clone either way.

Sampling is also what made this notebook finish at all. The grid is 216 parameter
combinations at 5-fold cross-validation, **1,080 Random Forest fits**, which on the full
dataset exceeded a 20-minute cell timeout and was abandoned. On the sample it completes.

**Results**

```
Best params: bootstrap=True, max_depth=30, min_samples_leaf=2,
             min_samples_split=10, n_estimators=300
Best CV score: 0.866
Test accuracy: 0.862

              precision  recall  f1-score  support
   non-diabetic    0.88    0.98      0.92     8548
   diabetic        0.55    0.16      0.25     1414
   accuracy                          0.86     9962
   macro avg       0.71    0.57      0.59     9962
```

**What 86% accuracy is worth here: almost nothing.**

| | Accuracy |
|---|---|
| Always predict "non-diabetic" | **85.81%** |
| Tuned Random Forest | **86.20%** |
| Difference | **+0.39 pp** |

1,080 Random Forest fits bought 0.39 percentage points over a one-line constant predictor.
And the model identifies **227 of 1,414 diabetics, 16.1%**. As a screening tool that is
not useful: it misses five out of six cases.

Macro F1 (0.59) and minority recall (0.16) are the figures that describe this model;
accuracy describes the class balance. The confusion matrix shows the mechanism plainly: 188
false positives against 1,187 false negatives, because nothing in the training objective
penalises missing a diabetic more than flagging a healthy person.

What would actually help, in rough order of expected value: class weighting or SMOTE so the
loss reflects the cost asymmetry; optimising for recall or average precision instead of
accuracy; tuning the decision threshold on a precision-recall curve rather than leaving it
at 0.5; and reporting PR-AUC, which unlike accuracy is not inflated by an 84% majority.

## Running it

```bash
pip install -r requirements.txt
jupyter notebook notebooks/
```

Both notebooks resolve their data relatively from `data/`.

## Notes

- The Hepatitis C study was a **group assignment** (Tugas Kelompok P14, Analisis Prediksi
  dan Prognosis, Semester 4). The diabetes study was individual coursework for
  Kecerdasan Buatan (Artificial Intelligence), Semester 5.
- `scikit-learn` is pinned below 1.11 because the notebooks use `SVC(probability=True)`,
  deprecated in 1.9 and scheduled for removal in 1.11. The modern equivalent is
  `CalibratedClassifierCV(SVC(), ensemble=False)`.
- The full diabetes dataset is fetched by `fetch_data.py` rather than committed, and is
  listed in `.gitignore` so it cannot be added back by accident.
