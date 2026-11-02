# -*- coding: utf-8 -*-
"""Запуск первой части работы."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.part1_dimensionality import run_part1  # noqa: E402


if __name__ == "__main__":
    run_part1()
    print("Готово: часть 1. Рисунки: figures/, метрики: results/part1_results.json")
