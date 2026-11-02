# -*- coding: utf-8 -*-
"""Загрузка данных варианта из книги Excel."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _find_variant_column(first_row: pd.Series, variant: int) -> int:
    """Возвращает индекс первого столбца блока нужного варианта."""
    normalized = first_row.astype(str).str.strip().str.lower()
    target = f"вариант {variant}".lower()
    exact = np.flatnonzero(normalized == target)
    if len(exact):
        return int(exact[0])
    partial = np.flatnonzero(normalized.str.startswith(target))
    if len(partial):
        return int(partial[0])
    raise ValueError(f"В файле не найден блок «Вариант {variant}».")


def load_variant_dataset(
    path: str | Path,
    variant: int,
    features: list[str],
) -> pd.DataFrame:
    """Читает блок варианта.

    В исходных книгах первая строка содержит подписи вариантов, вторая —
    имена признаков и целевой столбец y, начиная с третьей строки идут данные.
    """
    path = Path(path)
    raw = pd.read_excel(path, header=None)
    if raw.shape[0] < 3:
        raise ValueError(f"Файл {path.name} не содержит данных.")

    start = _find_variant_column(raw.iloc[0], variant)
    stop = start + len(features) + 1
    block = raw.iloc[2:, start:stop].copy()
    block.columns = [*features, "y"]
    block = block.apply(pd.to_numeric, errors="coerce").dropna().reset_index(drop=True)

    expected = [*features, "y"]
    if list(block.columns) != expected:
        raise ValueError(f"Не удалось разобрать столбцы файла {path.name}.")
    if block.empty:
        raise ValueError(f"Блок варианта {variant} в файле {path.name} пуст.")

    block["y"] = block["y"].astype(int)
    return block


def dataset_summary(df: pd.DataFrame, features: list[str]) -> dict:
    """Возвращает основные сведения о наборе данных."""
    return {
        "n_samples": int(len(df)),
        "n_features": len(features),
        "features": list(features),
        "class_counts": {int(k): int(v) for k, v in df["y"].value_counts().sort_index().items()},
        "missing_values": int(df.isna().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
    }
