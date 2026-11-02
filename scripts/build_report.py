# -*- coding: utf-8 -*-
"""Сборка отчёта DOCX по уже сохранённым результатам."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.report_builder import build_report  # noqa: E402


if __name__ == "__main__":
    path = build_report()
    print(f"Отчёт сохранён: {path}")
