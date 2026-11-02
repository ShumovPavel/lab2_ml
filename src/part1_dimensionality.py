# -*- coding: utf-8 -*-
"""Часть 1. Снижение размерности: PCA, SVD, ICA."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from sklearn.decomposition import FastICA, PCA
from sklearn.preprocessing import StandardScaler

from src.config import (
    PCA_DATASET,
    PCA_FEATURES,
    RANDOM_STATE,
    RESULTS_DIR,
    VARIANT,
)
from src.data_loader import dataset_summary, load_variant_dataset
from src.plotting import PALETTE, ru_number, ru_percent, save_figure, style_axes

warnings.filterwarnings("ignore", category=UserWarning)


def _prepare_data() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    df = load_variant_dataset(PCA_DATASET, VARIANT, PCA_FEATURES)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(df[PCA_FEATURES].to_numpy())
    return df, x_scaled, df["y"].to_numpy()


def _draw_biplot(
    ax: plt.Axes,
    scores: np.ndarray,
    loadings: np.ndarray,
    feature_names: list[str],
    targets: np.ndarray,
    title: str,
    xlabel: str,
    ylabel: str,
) -> None:
    """Строит двумерную проекцию с векторами признаков."""
    scale_x = 1.0 / (scores[:, 0].max() - scores[:, 0].min())
    scale_y = 1.0 / (scores[:, 1].max() - scores[:, 1].min())

    for class_id in np.unique(targets):
        mask = targets == class_id
        ax.scatter(
            scores[mask, 0] * scale_x,
            scores[mask, 1] * scale_y,
            s=34,
            alpha=0.75,
            edgecolors="white",
            linewidths=0.35,
            color=PALETTE[int(class_id) % len(PALETTE)],
            label=f"класс {int(class_id)}",
            zorder=2,
        )

    # Небольшие смещения не дают подписям почти совпадающих векторов
    # (например, a и c в PCA) накладываться друг на друга.
    label_offsets = {
        "a": (0.09, 0.02),
        "b": (0.05, 0.08),
        "c": (0.10, -0.07),
        "d": (-0.04, 0.08),
        "e": (0.04, -0.09),
    }

    for i, feature in enumerate(feature_names):
        ax.arrow(
            0,
            0,
            loadings[i, 0],
            loadings[i, 1],
            color="#b2182b",
            alpha=0.9,
            head_width=0.035,
            head_length=0.035,
            linewidth=1.5,
            length_includes_head=True,
            zorder=3,
        )
        dx, dy = label_offsets.get(feature, (0.08, 0.05))
        ax.text(
            loadings[i, 0] * 1.14 + dx,
            loadings[i, 1] * 1.14 + dy,
            feature,
            color="#67000d",
            ha="center",
            va="center",
            fontsize=10.5,
            fontweight="bold",
            zorder=4,
        )

    ax.axhline(0, color="grey", linestyle="--", linewidth=0.7)
    ax.axvline(0, color="grey", linestyle="--", linewidth=0.7)
    ax.set_xlim(-1.32, 1.32)
    ax.set_ylim(-1.32, 1.32)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12.5)
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.9)
    style_axes(ax)


def run_part1() -> dict:
    """Выполняет первую часть работы и сохраняет рисунки и метрики."""
    df, x_scaled, y = _prepare_data()
    summary = dataset_summary(df, PCA_FEATURES)

    # 1.1 Корреляционный анализ
    corr = df[PCA_FEATURES].corr()

    fig, ax = plt.subplots(figsize=(7.4, 6.0))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".3f",
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        square=True,
        linewidths=0.6,
        cbar_kws={"label": "Коэффициент корреляции Пирсона"},
        ax=ax,
    )
    ax.set_title("Матрица корреляций признаков (вариант 4)")
    ax.set_xlabel("")
    ax.set_ylabel("")
    save_figure(fig, "fig01_correlation.png")

    # 1.2 Матрица разброса
    fig, axes = plt.subplots(5, 5, figsize=(11.0, 11.0))
    pd.plotting.scatter_matrix(
        df[PCA_FEATURES],
        ax=axes,
        diagonal="hist",
        alpha=0.65,
        figsize=(11.0, 11.0),
        hist_kwds={"bins": 15, "color": "#8fb8d8", "edgecolor": "white"},
        marker="o",
        c=[PALETTE[int(v) % len(PALETTE)] for v in y],
        s=22,
    )
    legend_handles = [
        Line2D([], [], marker="o", linestyle="", markersize=7,
               markerfacecolor=PALETTE[i], markeredgecolor="white", label=f"класс {i}")
        for i in range(len(np.unique(y)))
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        ncol=len(legend_handles),
        frameon=False,
        bbox_to_anchor=(0.5, 1.01),
        title="Эталонные классы",
    )
    fig.suptitle("Матрица разброса пяти признаков", y=1.035, fontsize=14)
    fig.tight_layout()
    save_figure(fig, "fig02_scatter_matrix.png")

    # 1.3 PCA
    pca = PCA(random_state=RANDOM_STATE)
    scores = pca.fit_transform(x_scaled)
    explained = pca.explained_variance_ratio_
    cumulative = np.cumsum(explained)
    n_components_80 = int(np.searchsorted(cumulative, 0.80) + 1)
    n_components_90 = int(np.searchsorted(cumulative, 0.90) + 1)

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    components = np.arange(1, len(explained) + 1)
    bars = ax.bar(components, explained * 100, color="#3b7dd8", alpha=0.85,
                  edgecolor="white", label="Доля компоненты")
    ax.set_xlabel("Номер главной компоненты")
    ax.set_ylabel("Доля объяснённой дисперсии, %")
    ax.set_xticks(components)
    ax.set_ylim(0, 100)
    for bar, value in zip(bars, explained * 100):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.2,
                ru_number(value, 2), ha="center", fontsize=8.5)
    ax2 = ax.twinx()
    ax2.plot(components, cumulative * 100, "o-", color="#c0392b", linewidth=2,
             label="Накопленная доля")
    ax2.set_ylabel("Накопленная доля, %")
    ax2.set_ylim(0, 105)
    ax2.grid(False)
    lines = [bars, ax2.lines[0]]
    ax.legend(lines, [item.get_label() for item in lines], loc="center right")
    ax.set_title("Объяснённая и накопленная дисперсия PCA")
    save_figure(fig, "fig03_pca_variance.png")

    # 1.4 SVD
    u, singular_values, vt = np.linalg.svd(x_scaled, full_matrices=False)
    svd_scores = u * singular_values
    svd_ratios = singular_values ** 2 / np.sum(singular_values ** 2)
    svd_cumulative = np.cumsum(svd_ratios)
    svd_loadings = vt.T

    # Согласуем знаки с PCA для наглядного сравнения
    for j in range(min(2, scores.shape[1])):
        if np.corrcoef(scores[:, j], svd_scores[:, j])[0, 1] < 0:
            svd_scores[:, j] *= -1
            svd_loadings[:, j] *= -1

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    bars = ax.bar(components, svd_ratios * 100, color="#2e9e6b", alpha=0.85,
                  edgecolor="white", label="Доля компоненты")
    ax.set_xlabel("Номер сингулярной компоненты")
    ax.set_ylabel("Доля объяснённой дисперсии, %")
    ax.set_xticks(components)
    ax.set_ylim(0, 100)
    for bar, value in zip(bars, svd_ratios * 100):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.2,
                ru_number(value, 2), ha="center", fontsize=8.5)
    ax2 = ax.twinx()
    ax2.plot(components, svd_cumulative * 100, "o-", color="#c0392b", linewidth=2,
             label="Накопленная доля")
    ax2.set_ylabel("Накопленная доля, %")
    ax2.set_ylim(0, 105)
    ax2.grid(False)
    lines = [bars, ax2.lines[0]]
    ax.legend(lines, [item.get_label() for item in lines], loc="center right")
    ax.set_title("Объяснённая и накопленная дисперсия SVD")
    save_figure(fig, "fig04_svd_variance.png")

    # 1.5 ICA: ошибка восстановления
    ica_components = list(range(1, len(PCA_FEATURES) + 1))
    ica_mse: list[float] = []
    ica_kurtosis: list[list[float]] = []
    ica_iterations: list[int] = []
    for n in ica_components:
        ica = FastICA(
            n_components=n,
            random_state=RANDOM_STATE,
            whiten="unit-variance",
            max_iter=3000,
            tol=1e-4,
        )
        sources = ica.fit_transform(x_scaled)
        reconstructed = ica.inverse_transform(sources)
        ica_mse.append(float(np.mean((x_scaled - reconstructed) ** 2)))
        ica_kurtosis.append([float(v) for v in pd.DataFrame(sources).kurt().to_numpy()])
        ica_iterations.append(int(getattr(ica, "n_iter_", 0)))

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.plot(ica_components, ica_mse, "o-", color="#7b3294", linewidth=2,
            markersize=7, label="MSE восстановления")
    for n, value in zip(ica_components, ica_mse):
        ax.annotate(ru_number(value, 4), (n, value), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=9)
    ax.set_xlabel("Число независимых компонент")
    ax.set_ylabel("Среднеквадратичная ошибка (MSE)")
    ax.set_xticks(ica_components)
    ax.set_ylim(bottom=-0.02)
    ax.set_title("Ошибка восстановления данных методом ICA")
    ax.legend()
    style_axes(ax)
    save_figure(fig, "fig05_ica_reconstruction.png")

    # 1.6 Сопоставление PCA, SVD и ICA
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.8))
    axes[0].plot(components, cumulative * 100, "o-", color="#3b7dd8",
                 linewidth=2, label="PCA")
    axes[0].plot(components, svd_cumulative * 100, "s--", color="#2e9e6b",
                 linewidth=1.8, markersize=5, label="SVD")
    axes[0].set_xlabel("Число компонент")
    axes[0].set_ylabel("Накопленная дисперсия, %")
    axes[0].set_xticks(components)
    axes[0].set_ylim(0, 105)
    axes[0].set_title("Накопленная дисперсия")
    axes[0].legend()
    style_axes(axes[0])

    axes[1].bar(ica_components, ica_mse, color="#9b59b6", alpha=0.85, edgecolor="white")
    axes[1].set_xlabel("Число независимых компонент")
    axes[1].set_ylabel("MSE восстановления")
    axes[1].set_xticks(ica_components)
    axes[1].set_title("Ошибка восстановления ICA")
    for n, value in zip(ica_components, ica_mse):
        axes[1].text(n, value + max(ica_mse) * 0.025, ru_number(value, 4),
                     ha="center", fontsize=8.5)
    style_axes(axes[1])
    fig.suptitle("Сопоставление методов снижения размерности", fontsize=14)
    fig.tight_layout()
    save_figure(fig, "fig06_methods_comparison.png")

    # 1.7 Двумерные проекции и направления признаков
    ica_2d = FastICA(
        n_components=2,
        random_state=RANDOM_STATE,
        whiten="unit-variance",
        max_iter=3000,
        tol=1e-4,
    )
    ica_scores = ica_2d.fit_transform(x_scaled)
    ica_mixing = ica_2d.mixing_.copy()
    ica_mixing /= np.linalg.norm(ica_mixing, axis=0, keepdims=True)

    fig, axes = plt.subplots(1, 3, figsize=(11.6, 5.0))
    _draw_biplot(
        axes[0],
        scores[:, :2],
        pca.components_.T[:, :2],
        PCA_FEATURES,
        y,
        "PCA",
        f"PC1 ({ru_percent(explained[0])})",
        f"PC2 ({ru_percent(explained[1])})",
    )
    _draw_biplot(
        axes[1],
        svd_scores[:, :2],
        svd_loadings[:, :2],
        PCA_FEATURES,
        y,
        "SVD",
        f"SC1 ({ru_percent(svd_ratios[0])})",
        f"SC2 ({ru_percent(svd_ratios[1])})",
    )
    _draw_biplot(
        axes[2],
        ica_scores,
        ica_mixing,
        PCA_FEATURES,
        y,
        "ICA (FastICA)",
        "IC1",
        "IC2",
    )
    fig.suptitle("Двумерные проекции и направления исходных признаков", fontsize=13)
    fig.tight_layout()
    save_figure(fig, "fig07_projections.png")

    # Сохранение метрик
    offdiag_pairs = [
        ((PCA_FEATURES[i], PCA_FEATURES[j]), float(abs(corr.iloc[i, j])))
        for i in range(len(PCA_FEATURES))
        for j in range(i + 1, len(PCA_FEATURES))
    ]
    max_pair, max_value = max(offdiag_pairs, key=lambda item: item[1])

    results = {
        "dataset": summary,
        "correlation": {
            "matrix": corr.round(6).to_dict(),
            "max_offdiag": {
                "pair": list(max_pair),
                "value": max_value,
            },
        },
        "pca": {
            "explained": [float(v) for v in explained],
            "cumulative": [float(v) for v in cumulative],
            "n_components_80": n_components_80,
            "n_components_90": n_components_90,
            # components_.T[i] — вклад i-го признака в каждую компоненту
            "loadings": {
                feature: [float(v) for v in pca.components_.T[i]]
                for i, feature in enumerate(PCA_FEATURES)
            },
        },
        "svd": {
            "singular_values": [float(v) for v in singular_values],
            "explained": [float(v) for v in svd_ratios],
            "cumulative": [float(v) for v in svd_cumulative],
        },
        "ica": {
            "components": ica_components,
            "mse": ica_mse,
            "kurtosis": ica_kurtosis,
            "iterations": ica_iterations,
        },
        "projections": {
            "pca_scores_shape": list(scores[:, :2].shape),
            "svd_scores_shape": list(svd_scores[:, :2].shape),
            "ica_scores_shape": list(ica_scores.shape),
        },
    }
    output_path = RESULTS_DIR / "part1_results.json"
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


if __name__ == "__main__":
    run_part1()
    print("Часть 1 выполнена. Рисунки и метрики сохранены.")
