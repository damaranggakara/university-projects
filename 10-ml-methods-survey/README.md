# Machine Learning Methods Survey

A systematic comparison of clustering, classification and regression methods, each applied
to a single dataset so the algorithms rather than the data are what differ. Coursework for
Pembelajaran Mesin (Machine Learning), Semester 4.

| Task | Methods | Dataset |
|---|---|---|
| Clustering | K-Means, AGNES, DIANA, Self-Organising Map | Palmer penguins (335 rows) |
| Classification | Decision Tree, KNN, Naive Bayes, SVM, ANN | Lung cancer survey (309 rows) |
| Regression | ANN | Boston housing |

## Clustering

Shared pipeline: drop nulls, label-encode `sex`, standardise, reduce to 2 principal
components, then cluster.

The notebooks each visualise their own result, but only the SOM notebook printed a score,
and the methods did not agree on the number of clusters, K-Means and AGNES choose k by a
silhouette sweep, DIANA is hard-coded to 3, and the SOM uses a 10x10 grid. So there was no
comparison to read. `compare_clustering.py` reruns the same preprocessing and scores the
three partitional methods at a common k = 3:

| Method | Silhouette | Davies-Bouldin | Calinski-Harabasz |
|---|---|---|---|
| **K-Means** | **0.547** | **0.675** | **423.2** |
| AGNES (ward) | 0.546 | 0.676 | 422.6 |
| DIANA (divisive) | 0.326 | 0.855 | 218.7 |

Higher silhouette and Calinski-Harabasz are better; lower Davies-Bouldin is better.

Three things worth drawing out:

**K-Means and AGNES are indistinguishable here**: 0.547 against 0.546 across all three
indices. Ward linkage minimises within-cluster variance, which is K-Means' objective, so on
well-separated roughly spherical groups the two converge on the same partition. That is a
result about the data, not a coincidence.

**DIANA is clearly worse**, and the reason is in its splitting rule. The implementation
divides the largest cluster by finding its two most distant points and assigning every
other point to the nearer one. That is a cruder criterion than Ward's variance reduction:
it is driven by extremes, so a single outlier can define a split. Silhouette drops by 40%.

**k = 3 is not the best choice.** Sweeping K-Means across k = 2..10 puts the silhouette
peak at **k = 4 (0.645)**, well above k = 3 (0.547):

```
k=2:0.472  k=3:0.547  k=4:0.645  k=5:0.592  k=6:0.566
k=7:0.564  k=8:0.552  k=9:0.498  k=10:0.455
```

The penguins data has no species column here, so there is no ground truth to appeal to,
but on internal validity, four clusters fit better than the three the notebooks settle on.

The SOM reaches a silhouette of **0.345** on a 10x10 grid. That is not comparable to the
rows above: 100 map units on 335 points is a different problem from a 3-way partition, and
the figure is reported here only as the notebook produced it.

## Classification

Lung cancer survey, 70/30 split, `random_state=42`. Test set is 93 rows and heavily
imbalanced: 86 positive against 7 negative.

| Method | Accuracy | 95% CI | vs baseline | Macro F1 | Minority recall |
|---|---|---|---|---|---|
| SVM (linear) | 0.968 | [0.909, 0.993] | +0.043 | 0.88 | 0.71 |
| Naive Bayes | 0.957 | [0.894, 0.988] | +0.032 | 0.82 | 0.57 |
| KNN (k=5) | 0.935 | [0.865, 0.976] | +0.011 | 0.77 | 0.57 |
| Decision Tree | 0.914 | [0.838, 0.962] | **−0.011** | 0.69 | 0.43 |
| ANN | runs; see note | | | | |

**The majority-class baseline is 0.925.** Predicting "has lung cancer" for all 93 rows
scores higher than the Decision Tree, and only 1.1 points below KNN. Accuracy on an 86/7
split mostly measures the class balance.

### Does the ranking mean anything?

`compare_classifiers.py` tests it, and the answer has two halves.

**On this test set: no.** All four confidence intervals overlap. McNemar's test, the correct
test here, since every model is evaluated on the *same* 93 rows and so the predictions are
paired, finds no significant difference for any pair:

```
pair                            disagree       p
SVM vs Naive Bayes                     3   1.000
SVM vs KNN                             5   0.375
SVM vs Decision Tree                   9   0.180
Naive Bayes vs KNN                     4   0.625
Naive Bayes vs Decision Tree           6   0.219
KNN vs Decision Tree                  10   0.754
```

The models disagree on 3 to 10 cases out of 93, and how those split is consistent with
chance. A single 93-row test set cannot order these four classifiers, so "SVM wins" is not
a conclusion it supports.

**Across repeated splits: yes, and SVM genuinely leads.** Repeating the stratified 70/30
split 50 times:

| Method | Mean | sd | Min | Max | Ranked 1st |
|---|---|---|---|---|---|
| **SVM** | **0.921** | 0.020 | 0.892 | 0.989 | **43 / 50** |
| Naive Bayes | 0.892 | 0.025 | 0.849 | 0.946 | 4 / 50 |
| KNN | 0.889 | 0.023 | 0.839 | 0.935 | 3 / 50 |
| Decision Tree | 0.870 | 0.030 | 0.774 | 0.925 | 0 / 50 |

SVM ranks first in 43 of 50 splits where chance would give 12, binomial p = 1.8 × 10⁻¹⁹.
That *is* evidence, and it comes from resampling rather than from one lucky split.

**And the reported numbers are optimistic.** `random_state=42` turned out to be a
favourable draw for every model:

| Method | Reported | Mean over 50 splits | Difference |
|---|---|---|---|
| SVM | 0.968 | 0.921 | +0.047 |
| Naive Bayes | 0.957 | 0.892 | +0.065 |
| KNN | 0.935 | 0.889 | +0.046 |
| Decision Tree | 0.914 | 0.870 | +0.044 |

Four to seven points of the headline accuracy is split luck. The per-split standard
deviation (0.020-0.030) is larger than the gaps between adjacent models, which is the
mechanism behind both findings at once.

The practical lesson is the one worth taking from this project: a leaderboard built on a
single split reports split variance as if it were model quality. The ranking happened to be
right, but the evidence given for it was not.

Minority-class recall remains the most honest single column. Even SVM misses 29% of
negative cases, and the Decision Tree misses 57%.

## Regression

A single feedforward network on Boston housing. **Not run**, see below.

## What does not run

The two ANN notebooks (`classification/ann.ipynb`, `regression/ann_regression.ipynb`)
require TensorFlow, which has no release supporting Python 3.14, the only interpreter on
the development machine. They are included unmodified. To run them, install Python 3.12 or
earlier and uncomment `tensorflow` in `requirements.txt`; alternatively they port to
`sklearn.neural_network.MLPClassifier` / `MLPRegressor`, or to PyTorch, with no change to
the method.

Eight of the ten notebooks execute end to end.

## Running it

```bash
pip install -r requirements.txt
python compare_clustering.py        # the clustering table above
jupyter notebook notebooks/
```

Notebooks resolve `data/` by walking up the tree, so they run from any working directory.

## Notes

Individual coursework. The notebooks are preserved as submitted; the comparison script is
an addition, since the original set had no common basis for comparing its own methods.
