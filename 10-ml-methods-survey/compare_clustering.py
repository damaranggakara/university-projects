"""Put the four clustering methods on a common footing.

The notebooks each visualise their own clustering, but only the SOM notebook prints a
quantitative score, and the methods do not agree on the number of clusters: K-Means and
AGNES choose k by a silhouette sweep, DIANA is fixed at 3, and the SOM uses a 10x10 grid.
This script reruns the same preprocessing and scores the three partitional methods at a
common k, so the comparison in the README means something.

Run:  python compare_clustering.py
"""
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import LabelEncoder, StandardScaler

K = 3


def load():
    """Same preprocessing as the notebooks: dropna, encode sex, scale, PCA to 2-D."""
    df = pd.read_csv("data/penguins.csv").dropna().copy()
    df["sex"] = LabelEncoder().fit_transform(df["sex"])
    scaled = StandardScaler().fit_transform(df)
    return PCA(n_components=2).fit_transform(scaled), df


def diana(X, n_clusters):
    """Divisive clustering, as implemented in diana.ipynb, returning flat labels."""
    clusters = [np.asarray(X)]
    while len(clusters) < n_clusters:
        i = int(np.argmax([len(c) for c in clusters]))
        big = clusters.pop(i)
        d = pairwise_distances(big)
        a, b = np.unravel_index(np.argmax(d), d.shape)
        p1, p2 = big[a], big[b]
        left = [p for p in big
                if np.linalg.norm(p - p1) < np.linalg.norm(p - p2)]
        right = [p for p in big
                 if np.linalg.norm(p - p1) >= np.linalg.norm(p - p2)]
        clusters.append(np.array(left))
        clusters.append(np.array(right))
    labels = np.empty(len(X), dtype=int)
    for idx, c in enumerate(clusters):
        for p in c:
            labels[np.where((X == p).all(axis=1))[0]] = idx
    return labels


def best_k_by_silhouette(X, estimator, lo=2, hi=10):
    scores = {k: silhouette_score(X, estimator(k).fit_predict(X)) for k in range(lo, hi + 1)}
    return max(scores, key=scores.get), scores


def main():
    X, df = load()
    print(f"penguins: {len(df)} rows after dropna, "
          f"{df.shape[1]} features, reduced to 2 PCA components\n")

    labels = {
        "K-Means": KMeans(n_clusters=K, random_state=42, n_init=10).fit_predict(X),
        "AGNES (ward)": AgglomerativeClustering(n_clusters=K, linkage="ward").fit_predict(X),
        "DIANA (divisive)": diana(X, K),
    }

    print(f"All three scored at a common k = {K}:\n")
    print(f"{'method':<20}{'silhouette':>12}{'Davies-Bouldin':>16}{'Calinski-Harabasz':>20}")
    print("-" * 68)
    for name, lab in labels.items():
        print(f"{name:<20}{silhouette_score(X, lab):>12.3f}"
              f"{davies_bouldin_score(X, lab):>16.3f}"
              f"{calinski_harabasz_score(X, lab):>20.1f}")

    print("\nHigher silhouette and Calinski-Harabasz are better; lower Davies-Bouldin is better.\n")

    bk, scores = best_k_by_silhouette(X, lambda k: KMeans(n_clusters=k, random_state=42, n_init=10))
    print(f"K-Means silhouette by k: " + ", ".join(f"k={k}:{v:.3f}" for k, v in scores.items()))
    print(f"-> best k by silhouette is {bk} (silhouette {scores[bk]:.3f}), "
          f"not the k={K} the notebooks fix for DIANA.")

    assert all(len(set(l)) == K for l in labels.values()), "a method did not produce K clusters"
    print("\nOK: all methods produced the requested number of clusters.")


if __name__ == "__main__":
    main()
