# -*- coding: utf-8 -*-
"""Общие настройки проекта лабораторной работы № 2."""

from pathlib import Path

# Корневые каталоги проекта
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FIGURES_DIR = ROOT / "figures"
RESULTS_DIR = ROOT / "results"
REPORT_DIR = ROOT / "report"

for _directory in (FIGURES_DIR, RESULTS_DIR, REPORT_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

# Вариант задания
VARIANT = 4
RANDOM_STATE = 42

# Исходные файлы
PCA_DATASET = DATA_DIR / "Lab2_Dataset_PCA.xlsx"
CLUSTERING_DATASET = DATA_DIR / "Lab2_Dataset_Clustering.xlsx"

# Признаки
PCA_FEATURES = ["a", "b", "c", "d", "e"]
CLUSTERING_FEATURES = ["a", "b"]

# Параметры кластеризации
N_CLUSTERS = 4          # число классов в эталонной разметке варианта 4
KMEANS_N_INIT = 20
GMM_N_INIT = 20

# Параметры, подобранные по внутренним метрикам (без использования y)
AP_PREFERENCE_PERCENTILE = 5
AP_DAMPING = 0.9
MEANSHIFT_QUANTILE = 0.10
SPECTRAL_NEIGHBORS = 10
DBSCAN_EPS = 0.30
DBSCAN_MIN_SAMPLES = 5
HDBSCAN_MIN_CLUSTER_SIZE = 5
HDBSCAN_MIN_SAMPLES = 5
OPTICS_MIN_SAMPLES = 10
OPTICS_XI = 0.05

# Оформление
FIGURE_DPI = 160
RUSSIAN_FONT = "DejaVu Sans"
