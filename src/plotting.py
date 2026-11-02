# -*- coding: utf-8 -*-
"""Вспомогательные функции оформления графиков."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import FIGURE_DPI, FIGURES_DIR, RUSSIAN_FONT

plt.rcParams.update(
    {
        "font.family": RUSSIAN_FONT,
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
    }
)

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
           "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]


def save_figure(fig: plt.Figure, filename: str) -> Path:
    """Сохраняет рисунок в каталог figures и закрывает его."""
    path = FIGURES_DIR / filename
    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def ru_number(value: float, digits: int = 3) -> str:
    """Форматирует число с запятой в качестве десятичного разделителя."""
    return f"{value:.{digits}f}".replace(".", ",")


def ru_percent(value: float, digits: int = 2) -> str:
    """Форматирует долю как проценты."""
    return f"{value * 100:.{digits}f}".replace(".", ",") + " %"


def style_axes(ax: plt.Axes) -> None:
    """Единый стиль осей."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, linestyle=":", alpha=0.55)
