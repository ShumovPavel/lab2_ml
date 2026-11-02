# -*- coding: utf-8 -*-
"""Полный цикл: анализ данных, кластеризация и сборка отчёта."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.part1_dimensionality import run_part1  # noqa: E402
from src.part2_clustering import run_part2  # noqa: E402
from src.report_builder import build_report  # noqa: E402


if __name__ == "__main__":
    print("Шаг 1/3: снижение размерности (PCA, SVD, ICA)...")
    run_part1()
    print("Шаг 2/3: кластеризация и оценка качества...")
    run_part2()
    print("Шаг 3/3: сборка отчёта DOCX...")
    report_path = build_report()
    print(f"Готово. Отчёт: {report_path}")
