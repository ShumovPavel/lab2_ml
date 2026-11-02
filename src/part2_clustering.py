# -*- coding: utf-8 -*-
"""Часть 2. Кластеризация и обнаружение шумовых наблюдений."""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster import hierarchy
from sklearn.cluster import (
    HDBSCAN,
    OPTICS,
    AffinityPropagation,
    AgglomerativeClustering,
    Birch,
    BisectingKMeans,
    DBSCAN,
    KMeans,
    MeanShift,
    SpectralClustering,
    estimate_bandwidth,
)
from sklearn.metrics import (
    adjusted_rand_score,
    normalized_mutual_info_score,
    silhouette_samples,
    silhouette_score,
)
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from src.config import (
    AP_DAMPING,
    AP_PREFERENCE_PERCENTILE,
    CLUSTERING_DATASET,
    CLUSTERING_FEATURES,
    DBSCAN_EPS,
    DBSCAN_MIN_SAMPLES,
    GMM_N_INIT,
    HDBSCAN_MIN_CLUSTER_SIZE,
    HDBSCAN_MIN_SAMPLES,
    KMEANS_N_INIT,
    MEANSHIFT_QUANTILE,
    N_CLUSTERS,
    OPTICS_MIN_SAMPLES,
    OPTICS_XI,
    RANDOM_STATE,
    RESULTS_DIR,
    SPECTRAL_NEIGHBORS,
    VARIANT,
)
from src.data_loader import dataset_summary, load_variant_dataset
from src.plotting import PALETTE, ru_number, save_figure, style_axes

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class ClusteringResult:
    """Результат работы одного алгоритма."""

    name: str
    labels: np.ndarray
    params: dict = field(default_factory=dict)


def _prepare_data() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    df = load_variant_dataset(CLUSTERING_DATASET, VARIANT, CLUSTERING_FEATURES)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(df[CLUSTERING_FEATURES].to_numpy())
    return df, x_scaled, df["y"].to_numpy()


def _safe_silhouette(x: np.ndarray, labels: np.ndarray) -> float:
    mask = labels != -1
    unique = np.unique(labels[mask])
    if len(unique) < 2 or mask.sum() <= len(unique):
        return float("nan")
    return float(silhouette_score(x[mask], labels[mask]))


def _cluster_metrics(
    x: np.ndarray,
    y_true: np.ndarray,
    name: str,
    labels: np.ndarray,
    params: dict,
) -> dict:
    labels = np.asarray(labels)
    n_noise = int(np.sum(labels == -1))
    n_clusters = int(len(np.unique(labels[labels != -1])))
    return {
        "name": name,
        "params": params,
        "n_clusters": n_clusters,
        "n_noise": n_noise,
        "noise_share": float(n_noise / len(labels)),
        "silhouette": _safe_silhouette(x, labels),
        "ari": float(adjusted_rand_score(y_true, labels)),
        "nmi": float(normalized_mutual_info_score(y_true, labels)),
        "cluster_sizes": {
            int(k): int(v) for k, v in zip(*np.unique(labels[labels != -1], return_counts=True))
        },
    }


def _elbow_and_silhouette(x: np.ndarray) -> dict:
    ks = list(range(1, 11))
    inertia = []
    silhouettes = []
    for k in ks:
        model = KMeans(n_clusters=k, n_init=KMEANS_N_INIT, random_state=RANDOM_STATE)
        labels = model.fit_predict(x)
        inertia.append(float(model.inertia_))
        silhouettes.append(_safe_silhouette(x, labels) if k > 1 else float("nan"))

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6))
    axes[0].plot(ks, inertia, "o-", color="#3b7dd8", linewidth=2)
    axes[0].set_xlabel("Число кластеров k")
    axes[0].set_ylabel("Инерция (сумма квадратов расстояний)")
    axes[0].set_xticks(ks)
    axes[0].set_title("Метод локтя для K-Means")
    axes[0].axvline(N_CLUSTERS, color="#c0392b", linestyle="--", linewidth=1.2,
                    label=f"Выбрано k = {N_CLUSTERS}")
    axes[0].legend()
    style_axes(axes[0])

    valid_ks = np.array(ks[1:])
    valid_sil = np.array(silhouettes[1:], dtype=float)
    axes[1].plot(valid_ks, valid_sil, "o-", color="#2e9e6b", linewidth=2)
    axes[1].set_xlabel("Число кластеров k")
    axes[1].set_ylabel("Средний коэффициент силуэта")
    axes[1].set_xticks(ks)
    axes[1].set_title("Силуэт K-Means в зависимости от k")
    axes[1].axvline(N_CLUSTERS, color="#c0392b", linestyle="--", linewidth=1.2,
                    label=f"Выбрано k = {N_CLUSTERS}")
    axes[1].legend()
    style_axes(axes[1])
    fig.tight_layout()
    save_figure(fig, "fig09_elbow_silhouette.png")

    return {
        "k": ks,
        "inertia": inertia,
        "silhouette": silhouettes,
    }


def _silhouette_plot(x: np.ndarray, labels: np.ndarray) -> dict:
    values = silhouette_samples(x, labels)
    mean_value = float(values.mean())
    n_clusters = len(np.unique(labels))

    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    lower = 10
    per_cluster = {}
    for cluster_id in range(n_clusters):
        cluster_values = np.sort(values[labels == cluster_id])
        upper = lower + len(cluster_values)
        color = PALETTE[cluster_id % len(PALETTE)]
        ax.fill_betweenx(
            np.arange(lower, upper),
            0,
            cluster_values,
            facecolor=color,
            edgecolor=color,
            alpha=0.8,
        )
        ax.text(-0.06, lower + 0.5 * len(cluster_values), str(cluster_id),
                fontsize=9, va="center", ha="right")
        per_cluster[int(cluster_id)] = float(cluster_values.mean())
        lower = upper + 10

    ax.axvline(mean_value, color="#c0392b", linestyle="--", linewidth=1.5,
               label=f"Среднее значение: {ru_number(mean_value, 3)}")
    ax.set_xlabel("Коэффициент силуэта")
    ax.set_ylabel("Наблюдения, упорядоченные по кластерам")
    ax.set_yticks([])
    ax.set_xlim(-0.25, 1.0)
    ax.set_title("Силуэтный анализ K-Means при k = 4")
    ax.legend(loc="lower right")
    style_axes(ax)
    save_figure(fig, "fig10_silhouette.png")

    return {
        "mean": mean_value,
        "per_cluster": per_cluster,
        "cluster_sizes": {
            int(k): int(v) for k, v in zip(*np.unique(labels, return_counts=True))
        },
    }


def _initial_data_plot(df: pd.DataFrame, y: np.ndarray) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.9))
    axes[0].scatter(df["a"], df["b"], s=28, color="#4c78a8", alpha=0.8,
                    edgecolors="white", linewidths=0.4)
    axes[0].set_xlabel("Признак a")
    axes[0].set_ylabel("Признак b")
    axes[0].set_title("Исходные наблюдения без меток")
    style_axes(axes[0])

    for class_id in np.unique(y):
        mask = y == class_id
        axes[1].scatter(df.loc[mask, "a"], df.loc[mask, "b"], s=30,
                        color=PALETTE[int(class_id) % len(PALETTE)], alpha=0.85,
                        edgecolors="white", linewidths=0.4,
                        label=f"класс {int(class_id)}")
    axes[1].set_xlabel("Признак a")
    axes[1].set_ylabel("Признак b")
    axes[1].set_title("Эталонные классы")
    axes[1].legend(title="Класс", fontsize=8)
    style_axes(axes[1])
    fig.tight_layout()
    save_figure(fig, "fig08_initial_data.png")


def _build_algorithms(x: np.ndarray) -> list[ClusteringResult]:
    similarity = -euclidean_distances(x)
    preference = float(np.percentile(similarity, AP_PREFERENCE_PERCENTILE))
    bandwidth = float(
        estimate_bandwidth(x, quantile=MEANSHIFT_QUANTILE, n_samples=len(x),
                           random_state=RANDOM_STATE)
    )

    models: list[tuple[str, object, dict]] = [
        (
            "K-Means",
            KMeans(n_clusters=N_CLUSTERS, n_init=KMEANS_N_INIT, random_state=RANDOM_STATE),
            {"n_clusters": N_CLUSTERS, "n_init": KMEANS_N_INIT},
        ),
        (
            "Affinity Propagation",
            AffinityPropagation(
                damping=AP_DAMPING,
                preference=preference,
                random_state=RANDOM_STATE,
            ),
            {"damping": AP_DAMPING, "preference": preference,
             "preference_percentile": AP_PREFERENCE_PERCENTILE},
        ),
        (
            "Mean Shift",
            MeanShift(bandwidth=bandwidth, bin_seeding=True),
            {"bandwidth": bandwidth, "quantile": MEANSHIFT_QUANTILE},
        ),
        (
            "Spectral Clustering",
            SpectralClustering(
                n_clusters=N_CLUSTERS,
                affinity="nearest_neighbors",
                n_neighbors=SPECTRAL_NEIGHBORS,
                assign_labels="kmeans",
                random_state=RANDOM_STATE,
            ),
            {"n_clusters": N_CLUSTERS, "affinity": "nearest_neighbors",
             "n_neighbors": SPECTRAL_NEIGHBORS},
        ),
        (
            "Ward",
            AgglomerativeClustering(n_clusters=N_CLUSTERS, linkage="ward"),
            {"n_clusters": N_CLUSTERS, "linkage": "ward"},
        ),
        (
            "Agglomerative",
            AgglomerativeClustering(n_clusters=N_CLUSTERS, linkage="complete"),
            {"n_clusters": N_CLUSTERS, "linkage": "complete"},
        ),
        (
            "DBSCAN",
            DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES),
            {"eps": DBSCAN_EPS, "min_samples": DBSCAN_MIN_SAMPLES},
        ),
        (
            "HDBSCAN",
            HDBSCAN(
                min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE,
                min_samples=HDBSCAN_MIN_SAMPLES,
            ),
            {"min_cluster_size": HDBSCAN_MIN_CLUSTER_SIZE,
             "min_samples": HDBSCAN_MIN_SAMPLES},
        ),
        (
            "OPTICS",
            OPTICS(
                min_samples=OPTICS_MIN_SAMPLES,
                xi=OPTICS_XI,
                cluster_method="xi",
            ),
            {"min_samples": OPTICS_MIN_SAMPLES, "xi": OPTICS_XI,
             "cluster_method": "xi"},
        ),
        (
            "Gaussian Mixture",
            GaussianMixture(
                n_components=N_CLUSTERS,
                covariance_type="full",
                n_init=GMM_N_INIT,
                random_state=RANDOM_STATE,
            ),
            {"n_components": N_CLUSTERS, "covariance_type": "full",
             "n_init": GMM_N_INIT},
        ),
        (
            "BIRCH",
            Birch(n_clusters=N_CLUSTERS),
            {"n_clusters": N_CLUSTERS},
        ),
        (
            "Bisecting K-Means",
            BisectingKMeans(
                n_clusters=N_CLUSTERS,
                n_init=10,
                random_state=RANDOM_STATE,
            ),
            {"n_clusters": N_CLUSTERS, "n_init": 10},
        ),
    ]

    results: list[ClusteringResult] = []
    for name, model, params in models:
        labels = np.asarray(model.fit_predict(x))
        results.append(ClusteringResult(name=name, labels=labels, params=params))
    return results


def _plot_algorithms(
    x: np.ndarray,
    results: list[ClusteringResult],
    metrics: list[dict],
) -> None:
    """Строит две страницы по шесть панелей для читаемости подписей."""
    groups = [results[:6], results[6:]]
    metric_groups = [metrics[:6], metrics[6:]]
    titles = [
        "Результаты кластеризации: часть 1",
        "Результаты кластеризации: часть 2",
    ]
    filenames = ["fig11_algorithms_part1.png", "fig12_algorithms_part2.png"]

    for group, group_metrics, title, filename in zip(
        groups, metric_groups, titles, filenames
    ):
        fig, axes = plt.subplots(3, 2, figsize=(9.6, 11.4))
        for ax, result, metric in zip(axes.ravel(), group, group_metrics):
            labels = result.labels
            for cluster_id in np.unique(labels[labels != -1]):
                mask = labels == cluster_id
                ax.scatter(
                    x[mask, 0],
                    x[mask, 1],
                    s=26,
                    color=PALETTE[int(cluster_id) % len(PALETTE)],
                    alpha=0.85,
                    edgecolors="none",
                )
            noise = labels == -1
            if np.any(noise):
                ax.scatter(
                    x[noise, 0],
                    x[noise, 1],
                    s=40,
                    marker="x",
                    color="black",
                    linewidths=1.15,
                    label="шум",
                )
            ax.set_title(
                f"{result.name}\n"
                f"кластеров: {metric['n_clusters']}, шум: {metric['n_noise']}, "
                f"ARI = {ru_number(metric['ari'], 3)}",
                fontsize=10.5,
            )
            ax.set_xlabel("a (z-оценка)", fontsize=9.5)
            ax.set_ylabel("b (z-оценка)", fontsize=9.5)
            ax.tick_params(axis="both", labelsize=8.5)
            style_axes(ax)
        fig.suptitle(title, fontsize=13)
        fig.tight_layout()
        save_figure(fig, filename)


def _plot_dendrogram(x: np.ndarray) -> dict:
    linkage_matrix = hierarchy.linkage(x, method="ward")
    fig, ax = plt.subplots(figsize=(12.0, 5.2))
    hierarchy.dendrogram(
        linkage_matrix,
        truncate_mode="lastp",
        p=20,
        show_leaf_counts=True,
        leaf_rotation=45,
        leaf_font_size=9,
        color_threshold=0,
        above_threshold_color="#4c78a8",
        ax=ax,
    )
    ax.set_title("Дендрограмма метода Ward (последние 20 объединений)")
    ax.set_xlabel("Номер кластера или размер объединённой группы")
    ax.set_ylabel("Расстояние объединения")
    style_axes(ax)
    save_figure(fig, "fig13_dendrogram.png")

    last_merges = linkage_matrix[-10:, 2].tolist()
    return {
        "method": "ward",
        "last_merges": [float(v) for v in last_merges],
        "max_distance": float(linkage_matrix[-1, 2]),
    }


def _plot_noise(
    x: np.ndarray,
    results: list[ClusteringResult],
    metrics: list[dict],
) -> None:
    names = ["DBSCAN", "HDBSCAN", "OPTICS"]
    by_name = {result.name: result for result in results}
    metric_by_name = {metric["name"]: metric for metric in metrics}

    fig, axes = plt.subplots(1, 3, figsize=(11.6, 4.5))
    for ax, name in zip(axes, names):
        labels = by_name[name].labels
        for cluster_id in np.unique(labels[labels != -1]):
            mask = labels == cluster_id
            ax.scatter(
                x[mask, 0],
                x[mask, 1],
                s=24,
                color=PALETTE[int(cluster_id) % len(PALETTE)],
                alpha=0.8,
                edgecolors="none",
            )
        noise = labels == -1
        if np.any(noise):
            ax.scatter(
                x[noise, 0],
                x[noise, 1],
                s=42,
                marker="x",
                color="black",
                linewidths=1.2,
                label="шум (−1)",
            )
        metric = metric_by_name[name]
        ax.set_title(
            f"{name}: шум {metric['n_noise']} из {len(labels)} "
            f"({ru_number(metric['noise_share'] * 100, 1)} %)",
            fontsize=10,
        )
        ax.set_xlabel("a (z-оценка)", fontsize=9.5)
        ax.set_ylabel("b (z-оценка)", fontsize=9.5)
        ax.tick_params(axis="both", labelsize=8.5)
        if np.any(noise):
            ax.legend(loc="upper right", fontsize=7.5)
        style_axes(ax)
    fig.suptitle("Кластеры и шумовые наблюдения плотностных алгоритмов", fontsize=12)
    fig.tight_layout()
    save_figure(fig, "fig14_noise.png")


def run_part2() -> dict:
    """Выполняет вторую часть работы и сохраняет рисунки и таблицы."""
    df, x_scaled, y = _prepare_data()
    summary = dataset_summary(df, CLUSTERING_FEATURES)
    _initial_data_plot(df, y)

    elbow = _elbow_and_silhouette(x_scaled)

    kmeans = KMeans(n_clusters=N_CLUSTERS, n_init=KMEANS_N_INIT,
                    random_state=RANDOM_STATE)
    kmeans_labels = kmeans.fit_predict(x_scaled)
    silhouette_info = _silhouette_plot(x_scaled, kmeans_labels)

    results = _build_algorithms(x_scaled)
    metrics = [
        _cluster_metrics(x_scaled, y, result.name, result.labels, result.params)
        for result in results
    ]
    _plot_algorithms(x_scaled, results, metrics)
    dendrogram_info = _plot_dendrogram(x_scaled)
    _plot_noise(x_scaled, results, metrics)

    metrics_df = pd.DataFrame(metrics).sort_values(
        ["ari", "nmi"], ascending=False
    ).reset_index(drop=True)
    metrics_df.to_csv(RESULTS_DIR / "clustering_metrics.csv", index=False,
                      encoding="utf-8-sig")

    labels_df = pd.DataFrame({"y": y})
    for result in results:
        labels_df[result.name] = result.labels
    labels_df.to_csv(RESULTS_DIR / "clustering_labels.csv", index=False,
                     encoding="utf-8-sig")

    best = metrics_df.iloc[0].to_dict()
    results_json = {
        "dataset": summary,
        "elbow": elbow,
        "kmeans_silhouette": silhouette_info,
        "dendrogram": dendrogram_info,
        "algorithms": metrics_df.to_dict(orient="records"),
        "best_by_ari": best["name"],
        "best_metrics": {
            "name": best["name"],
            "ari": float(best["ari"]),
            "nmi": float(best["nmi"]),
            "silhouette": float(best["silhouette"]),
            "n_clusters": int(best["n_clusters"]),
            "n_noise": int(best["n_noise"]),
        },
    }
    (RESULTS_DIR / "part2_results.json").write_text(
        json.dumps(results_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results_json


if __name__ == "__main__":
    run_part2()
    print("Часть 2 выполнена. Рисунки и метрики сохранены.")
