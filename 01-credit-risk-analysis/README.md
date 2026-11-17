# Credit Risk Analysis

Classification and survival analysis on a credit-behaviour survey of 2,700 borrowers across
five Indonesian banks. Coursework for Manajemen Risiko (Risk Management), Semester 5.

This is the largest piece of analysis in the portfolio, and it is also the one whose
reported results hold up least well. The README leads with that, because the gap between
"97% accuracy" and what the models actually do is the whole lesson.

## Data

`data/credit_risk_survey.xlsx`, **2,700 respondents × 204 columns**, no missing values.
Four sheets: the responses, an indicator dictionary, a coding key and a scale reference.

The target is `Z (cat)`, the five-level Indonesian loan classification:

| Level | Meaning | Count |
|---|---|---|
| 1 | Lancar (current) | 2,267 |
| 2 | Dalam Perhatian Khusus (special mention) | 400 |
| 3 | Kurang Lancar (substandard) | 15 |
| 4 | Diragukan (doubtful) | 10 |
| 5 | Macet (loss) | 8 |

Levels 1-2 are **performing** (2,667) and 3-5 are **non-performing** (33). So the positive
class is **1.2% of the data**, and where the split is drawn matters enormously: cutting at
level 2 instead would give 433 positives and a far easier problem.

## 1. Classification: what the models actually do

The notebook trains Logistic Regression, Random Forest, SVM, XGBoost and KNN with SMOTE
oversampling, and reports 97-99% accuracy.

**A model that predicts "everyone repays" scores 98.70%.**

`test_baselines.py` measures what the models do about the 1.2% that matters, on a stratified
split of 540 test rows containing 7 non-performing loans:

| Model | Accuracy | vs constant | NPL recall | NPL F1 | ROC AUC | PR AUC |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.9852 | **−0.0019** | 0.00 | 0.00 | 0.608 | 0.020 |
| Random Forest | 0.9870 | +0.0000 | 0.00 | 0.00 | 0.552 | 0.019 |
| SVM | 0.9870 | +0.0000 | 0.00 | 0.00 | 0.644 | 0.032 |
| XGBoost | 0.9870 | +0.0000 | 0.00 | 0.00 | **0.432** | 0.025 |

**All four identify 0 of 7 defaults.**

```
             predicted PL   predicted NPL
  actual PL          532               1
  actual NPL           7               0
```

Three things follow:

- **Logistic Regression scores below a constant predictor.** It is worse than a single line
  of code that ignores the features entirely.
- **The other three *are* the constant predictor.** They reach 98.70% by predicting
  "performing" for every row, which is exactly the base rate.
- **XGBoost's ROC AUC is 0.432**, below 0.5, so its ranking of risk is slightly worse than
  random on this split.

The notebook's own SMOTE run does marginally better, with Logistic Regression and XGBoost
each catching **1 of 7** at 10% precision. That is the honest ceiling here, not 97%.

PR AUC is the figure to quote for a problem like this: at 0.019-0.032 it sits essentially at
the 1.2% base rate, meaning the models carry almost no ranking information about who
defaults.

### Why

33 positive cases is too few to learn from across 198 predictors. SMOTE synthesises
neighbours of 26 training examples, which manufactures density without adding information,
and accuracy as the selection criterion actively rewards ignoring them. A usable model would
need cost-sensitive learning with an explicit penalty for missed defaults, threshold tuning
on a precision-recall curve rather than 0.5, PR AUC as the selection metric, and realistically
far more NPL cases, pooling across banks or years.

## 2. Survival analysis

`notebooks/survival_analysis.ipynb`, Kaplan-Meier estimation and a Cox proportional hazards
model over `Z (day)`, time to the status outcome.

This half is better suited to the data. Survival analysis handles censoring directly: a
borrower who has not defaulted *yet* is informative rather than simply negative, which is
exactly the structure classification throws away by collapsing time into a binary label.
With 33 events it remains underpowered, but the framing is right where the classification
framing is not.

## Running it

```bash
pip install -r requirements.txt
python test_baselines.py                  # the comparison above
jupyter notebook notebooks/
```

| Notebook | Contents |
|---|---|
| `classification_models.ipynb` | five classifiers, SMOTE, confusion matrices (33 cells) |
| `survival_analysis.ipynb` | Kaplan-Meier curves and Cox regression (18 cells) |
| `group_submission.ipynb` | the group's logistic-regression submission |

All three execute end to end.

## Notes on the data

**It is anonymised at source**, which is worth stating because the filename says otherwise.
The original is `Data RMRM (confidential).xlsx`, and an earlier reading of this project
assumed its `Nama` column held customer names; *nama* is Indonesian for "name". It does
not:

| Column | Contents |
|---|---|
| `IDR` | sequential respondent id, 1-2700 |
| `IDR1` | respondent index within bank, 1-100 |
| `No Bank` | branch number, 1-27 |
| `Nama` | the **bank's** pseudonym, `Bank XA` … `Bank XE` |

No names, addresses or contact details appear in any of the 204 columns; the remainder are
coded questionnaire items. The five institutions are pseudonymous.

The file came from a third party and is labelled confidential, so redistribution is a
permissions question rather than a privacy one; see [`../DATA.md`](../DATA.md).

Group coursework. The classification and survival notebooks are the original submission;
`test_baselines.py` is an addition.

## On the CV

This project is worth claiming: a 204-variable survey, five institutions, survival analysis
alongside classification. But the claim should be about the analysis, not the accuracy.
"97% accuracy" describes a dataset that is 98.7% one class; what the work actually shows is
that **the models cannot identify defaulters at this event rate, and demonstrating that is
the finding.**
