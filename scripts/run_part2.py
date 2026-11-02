# -*- coding: utf-8 -*-
"""Запуск второй части работы."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.part2_clustering import run_part2  # noqa: E402


if __name__ == "__main__":
    run_part2()
    print("Готово: часть 2. Рисунки: figures/, таблица: results/clustering_metrics.csv")
