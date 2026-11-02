# -*- coding: utf-8 -*-
"""Сборка отчёта по лабораторной работе № 2 в формате DOCX."""

from __future__ import annotations

import json
import math
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from src.config import FIGURES_DIR, REPORT_DIR, RESULTS_DIR

FONT = "Times New Roman"
MONO_FONT = "Consolas"
BODY_SIZE = 14
CAPTION_SIZE = 12
TABLE_SIZE = 10


def _num(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "—"
    try:
        if math.isnan(float(value)):
            return "—"
    except (TypeError, ValueError):
        return str(value)
    return f"{float(value):.{digits}f}".replace(".", ",")


def _pct(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.{digits}f}".replace(".", ",") + " %"


def _set_run_font(run, size: int = BODY_SIZE, bold: bool = False,
                  italic: bool = False, name: str = FONT,
                  color: RGBColor | None = None) -> None:
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def _set_cell(cell, text: str, bold: bool = False, size: int = TABLE_SIZE,
              align=WD_ALIGN_PARAGRAPH.CENTER, shade: str | None = None) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.left_indent = Cm(0)
    paragraph.paragraph_format.right_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    run = paragraph.add_run(text)
    _set_run_font(run, size=size, bold=bold)
    if shade:
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), shade)
        tc_pr.append(shd)


def _add_table(doc, headers: list[str], rows: list[list[str]],
               widths_cm: list[float] | None = None,
               font_size: int = TABLE_SIZE,
               alignments: list | None = None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    for index, header in enumerate(headers):
        _set_cell(table.rows[0].cells[index], header, bold=True, size=font_size,
                  shade="D9E2F3")

    # Повтор шапки на новой странице и запрет разрыва строк
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)

    for row_values in rows:
        row = table.add_row()
        for index, value in enumerate(row_values):
            alignment = (alignments[index] if alignments else WD_ALIGN_PARAGRAPH.CENTER)
            _set_cell(row.cells[index], value, size=font_size, align=alignment)
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)

    if widths_cm:
        for row in table.rows:
            for cell, width in zip(row.cells, widths_cm):
                cell.width = Cm(width)

    # Небольшой отступ после таблицы
    trailing = doc.add_paragraph()
    trailing.paragraph_format.first_line_indent = Cm(0)
    trailing.paragraph_format.space_after = Pt(2)
    trailing.paragraph_format.line_spacing = 1.0
    return table


def _add_caption(doc, text: str, center: bool = True) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.keep_with_next = False
    run = paragraph.add_run(text)
    _set_run_font(run, size=CAPTION_SIZE)


def _add_figure(doc, filename: str, caption: str, width_cm: float = 16.4) -> None:
    path = FIGURES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Не найден рисунок: {path}")
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    _add_caption(doc, caption)


def _add_body(doc, text: str, first_indent: float = 1.25,
              alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, size: int = BODY_SIZE) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = alignment
    paragraph.paragraph_format.first_line_indent = Cm(first_indent)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.5
    run = paragraph.add_run(text)
    _set_run_font(run, size=size)


def _add_heading(doc, text: str, level: int = 1) -> None:
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.left_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(12 if level == 1 else 8)
    paragraph.paragraph_format.space_after = Pt(6 if level == 1 else 4)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run(text)
    _set_run_font(run, size=BODY_SIZE, bold=True, color=RGBColor(0, 0, 0))


def _add_code_block(doc, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.left_indent = Cm(0.7)
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.line_spacing = 1.0
    run = paragraph.add_run(text)
    _set_run_font(run, size=9, name=MONO_FONT)


def _add_page_number_footer(section) -> None:
    footer = section.footer
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    run = paragraph.add_run()
    _set_run_font(run, size=10)
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_separate = OxmlElement("w:fldChar")
    fld_separate.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_separate)
    run._r.append(fld_end)


def _add_toc(doc) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Cm(0)
    run = paragraph.add_run()
    _set_run_font(run, size=BODY_SIZE)

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    fld_separate = OxmlElement("w:fldChar")
    fld_separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "Содержание будет обновлено при открытии документа."
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")

    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_separate)
    run._r.append(text)
    run._r.append(fld_end)


def _title_page(doc, variant: int) -> None:
    lines = [
        ("МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ", 12, False),
        ("ФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ БЮДЖЕТНОЕ ОБРАЗОВАТЕЛЬНОЕ УЧРЕЖДЕНИЕ", 12, False),
        ("ВЫСШЕГО ОБРАЗОВАНИЯ", 12, False),
        ("«ДОНСКОЙ ГОСУДАРСТВЕННЫЙ ТЕХНИЧЕСКИЙ УНИВЕРСИТЕТ»", 12, True),
    ]
    for text, size, bold in lines:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.space_after = Pt(2)
        run = paragraph.add_run(text)
        _set_run_font(run, size=size, bold=bold)

    for _ in range(5):
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.line_spacing = 1.0

    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(12)
    paragraph.paragraph_format.space_after = Pt(10)
    run = paragraph.add_run("ЛАБОРАТОРНАЯ РАБОТА № 2")
    _set_run_font(run, size=18, bold=True)

    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.line_spacing = 1.15
    paragraph.paragraph_format.space_after = Pt(10)
    run = paragraph.add_run(
        "на тему «Обучение без учителя. Понижение размерности. "
        "Обнаружение аномалий. Кластеризация.»"
    )
    _set_run_font(run, size=14, bold=True)

    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.space_after = Pt(24)
    run = paragraph.add_run(f"Вариант {variant}")
    _set_run_font(run, size=14, bold=True)

    # Блок исполнителя и проверяющего
    for text in [
        "Выполнил:",
        "студент Подшивалин Р.В.",
        "группа ИПБП41",
        "",
        "Проверил:",
        "Дольников М.Г.",
    ]:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.space_after = Pt(2)
        run = paragraph.add_run(text)
        _set_run_font(run, size=13, bold=(text in {"Выполнил:", "Проверил:"}))

    for _ in range(4):
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.line_spacing = 1.0

    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.line_spacing = 1.0
    run = paragraph.add_run("Ростов-на-Дону\n2026 г.")
    _set_run_font(run, size=13)


def _format_parameters(params: dict) -> str:
    parts = []
    for key, value in params.items():
        if isinstance(value, float):
            parts.append(f"{key}={_num(value, 3)}")
        elif isinstance(value, bool):
            parts.append(f"{key}={str(value).lower()}")
        else:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def build_report() -> Path:
    """Формирует итоговый DOCX-отчёт."""
    part1_path = RESULTS_DIR / "part1_results.json"
    part2_path = RESULTS_DIR / "part2_results.json"
    if not part1_path.exists() or not part2_path.exists():
        raise FileNotFoundError(
            "Сначала выполните scripts/run_all.py — не найдены файлы результатов."
        )

    p1 = json.loads(part1_path.read_text(encoding="utf-8"))
    p2 = json.loads(part2_path.read_text(encoding="utf-8"))
    pca = p1["pca"]
    svd = p1["svd"]
    ica = p1["ica"]
    corr = p1["correlation"]
    algorithms = p2["algorithms"]
    best = p2["best_metrics"]
    alg = {item["name"]: item for item in algorithms}

    explained = pca["explained"]
    cumulative = pca["cumulative"]
    ica_mse = ica["mse"]
    max_pair = corr["max_offdiag"]["pair"]
    max_corr = corr["max_offdiag"]["value"]
    c_ac = corr["matrix"]["a"]["c"]

    doc = Document()

    # Параметры страницы и базовые стили
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.different_first_page_header_footer = True

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(BODY_SIZE)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.first_line_indent = Cm(1.25)

    for level in (1, 2):
        style = doc.styles[f"Heading {level}"]
        style.font.name = FONT
        style.font.size = Pt(BODY_SIZE)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.first_line_indent = Cm(0)
        style.paragraph_format.space_before = Pt(12 if level == 1 else 8)
        style.paragraph_format.space_after = Pt(6 if level == 1 else 4)
        style.paragraph_format.keep_with_next = True

    _add_page_number_footer(section)

    doc.core_properties.title = "Лабораторная работа № 2. Вариант 4"
    doc.core_properties.subject = "Обучение без учителя. Понижение размерности. Кластеризация."
    doc.core_properties.author = "Подшивалин Р.В."

    # Титульный лист
    _title_page(doc, 4)
    doc.add_page_break()

    # Содержание (не включается в сам TOC)
    contents_title = doc.add_paragraph()
    contents_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    contents_title.paragraph_format.first_line_indent = Cm(0)
    contents_title.paragraph_format.space_before = Pt(12)
    contents_title.paragraph_format.space_after = Pt(6)
    contents_title.paragraph_format.line_spacing = 1.0
    contents_title.paragraph_format.keep_with_next = True
    contents_run = contents_title.add_run("СОДЕРЖАНИЕ")
    _set_run_font(contents_run, size=BODY_SIZE, bold=True, color=RGBColor(0, 0, 0))
    _add_toc(doc)
    doc.add_page_break()

    # Цели и задачи
    _add_heading(doc, "ЦЕЛИ И ЗАДАЧИ РАБОТЫ", level=1)
    _add_body(
        doc,
        "Цель работы — исследовать методы снижения размерности многомерных данных "
        "и сравнить алгоритмы кластеризации на данных варианта 4, определив наиболее "
        "подходящие методы по результатам визуального анализа и количественной оценки.",
    )
    _add_body(
        doc,
        "Для достижения цели были поставлены следующие задачи: изучить исходные данные "
        "и оценить корреляционные зависимости; построить матрицу разброса; применить метод "
        "главных компонент (PCA — Principal Component Analysis), сингулярное разложение "
        "(SVD — Singular Value Decomposition) и анализ независимых компонент "
        "(ICA — Independent Component Analysis); оценить вклад компонент и построить "
        "двумерные проекции; исследовать 12 алгоритмов кластеризации; подобрать параметры "
        "и выявить шумовые наблюдения; сравнить полученные кластеры с эталонными метками "
        "и обосновать выбор лучшего метода.",
    )
    _add_body(
        doc,
        f"В первой части были проанализированы {p1['dataset']['n_samples']} наблюдений "
        f"с пятью числовыми признаками a, b, c, d, e. Во второй части были исследованы "
        f"{p2['dataset']['n_samples']} наблюдений по признакам a и b. Эталонные метки y "
        "использовались только для визуализации и проверки результатов и не включались "
        "в обучение моделей. Работа выполнена на языке Python 3.12 в среде Visual Studio Code "
        "с использованием библиотек pandas, NumPy, SciPy, scikit-learn, Matplotlib и seaborn.",
    )

    # Раздел 1
    _add_heading(doc, "1 ИССЛЕДОВАНИЕ МЕТОДОВ СНИЖЕНИЯ РАЗМЕРНОСТИ", level=1)
    _add_heading(doc, "1.1 Исходные данные и корреляционный анализ", level=2)
    _add_body(
        doc,
        f"В первой части используется таблица Lab2_Dataset_PCA.xlsx. После выделения "
        f"блока варианта 4 получено {p1['dataset']['n_samples']} наблюдений и пять "
        f"признаков; целевая переменная y принимает два значения: "
        f"{p1['dataset']['class_counts']['0']} наблюдений класса 0 и "
        f"{p1['dataset']['class_counts']['1']} наблюдений класса 1. Пропусков и полных "
        "дубликатов не обнаружено.",
    )
    _add_body(
        doc,
        "Сначала была вычислена матрица коэффициентов линейной корреляции Пирсона для "
        "пяти признаков. Коэффициенты принимают значения от −1 до +1 и характеризуют "
        "направление и тесноту линейной связи между парами переменных.",
    )
    _add_figure(doc, "fig01_correlation.png",
                "Рисунок 1 — Матрица корреляций признаков варианта 4", width_cm=12.6)
    _add_body(
        doc,
        f"Матрица получена функцией corr() библиотеки pandas и визуализирована тепловой "
        f"картой. Наибольшая внедиагональная корреляция наблюдается между признаками "
        f"{max_pair[0]} и {max_pair[1]} ({_num(max_corr, 3)}); следующая по модулю связь "
        f"b–d составляет всего {_num(abs(corr['matrix']['b']['d']), 3)}, остальные "
        "коэффициенты не превышают 0,09 по модулю. Таким образом, выраженной "
        "мультиколлинеарности нет, однако пара a–c образует умеренно связанный блок. "
        "Исключать признаки только по корреляции нецелесообразно.",
    )

    _add_heading(doc, "1.2 Анализ попарных распределений", level=2)
    _add_body(
        doc,
        "Для визуальной оценки совместных распределений была построена матрица разброса "
        "функцией pd.plotting.scatter_matrix(): вне диагонали представлены диаграммы "
        "рассеяния пар признаков, на диагонали — гистограммы. Точки окрашены по эталонным "
        "классам, чтобы оценить, насколько классы различимы в исходном пространстве.",
    )
    _add_figure(doc, "fig02_scatter_matrix.png",
                "Рисунок 2 — Матрица разброса пяти признаков", width_cm=14.4)
    _add_body(
        doc,
        "Облака точек имеют преимущественно эллиптическую форму. Наиболее заметная "
        "линейная зависимость соответствует паре a–c: при увеличении a растёт c. Класс 1 "
        "в среднем смещён в область положительных значений a и c, однако области классов "
        "существенно перекрываются. Для остальных пар признаков выраженных нелинейных "
        "зависимостей не обнаружено; признак d ведёт себя близко к шумовому. Матрица "
        "разброса подтверждает, что исходные признаки лишь частично разделяют классы, "
        "поэтому для визуализации и последующего анализа оправдано применение методов "
        "снижения размерности.",
    )

    _add_heading(doc, "1.3 Метод главных компонент", level=2)
    _add_body(
        doc,
        "Перед применением PCA признаки были стандартизированы: из каждого значения "
        "вычтено среднее и результат разделён на стандартное отклонение. Это необходимо, "
        "чтобы признаки с разным масштабом не доминировали в ковариационной матрице. "
        "Метод главных компонент строит взаимно ортогональные направления, упорядоченные "
        "по убыванию объяснённой дисперсии.",
    )
    _add_figure(doc, "fig03_pca_variance.png",
                "Рисунок 3 — Объяснённая и накопленная дисперсия PCA", width_cm=14.2)

    table1_rows = []
    for index in range(5):
        table1_rows.append([
            str(index + 1),
            _pct(explained[index]),
            _pct(cumulative[index]),
            _pct(svd["explained"][index]),
            _pct(svd["cumulative"][index]),
        ])
    _add_caption(doc, "Таблица 1 — Объяснённая дисперсия компонент PCA и SVD")
    _add_table(
        doc,
        ["Компонента", "PCA, доля", "PCA, накопленная", "SVD, доля", "SVD, накопленная"],
        table1_rows,
        widths_cm=[2.4, 3.2, 3.8, 3.2, 3.8],
    )

    _add_body(
        doc,
        f"Первые две компоненты объясняют {_pct(explained[0] + explained[1])} дисперсии, "
        f"три — {_pct(cumulative[2])}, четыре — {_pct(cumulative[3])}. Для сохранения "
        f"не менее 80 % дисперсии требуются {pca['n_components_80']} компоненты; порог "
        f"90 % также достигается только при {pca['n_components_90']} компонентах. "
        "Следовательно, снижение размерности до двух измерений сопровождается потерей "
        "около 46 % дисперсии и может использоваться прежде всего для визуализации, "
        "а не как полноценная замена исходного пространства.",
    )
    _add_body(
        doc,
        "Анализ нагрузок показывает, что первая компонента является осью a–c: вклады "
        "признаков a и c равны 0,704 и 0,704 соответственно. Вторая компонента "
        "противопоставляет признаки b и d признаку e: нагрузки b = 0,598, d = 0,534, "
        "e = −0,589. Третья компонента связана с парой d–e (0,683 и 0,688), четвёртая — "
        "с признаком b (0,794), пятая — с контрастом a–c (−0,686 и 0,687). Такая структура "
        "согласуется с корреляционной матрицей: именно пара a–c даёт наибольшую связь.",
    )

    _add_heading(doc, "1.4 Сингулярное разложение", level=2)
    _add_body(
        doc,
        "SVD было выполнено над той же стандартизированной матрицей X: X = UΣVᵀ. "
        "Доли дисперсии рассчитывались по квадратам сингулярных чисел, нормированным "
        "на их сумму. Сингулярные числа равны 17,332; 14,922; 13,681; 13,319 и 9,077.",
    )
    _add_figure(doc, "fig04_svd_variance.png",
                "Рисунок 4 — Объяснённая и накопленная дисперсия SVD", width_cm=14.2)
    _add_body(
        doc,
        "Доли объяснённой дисперсии SVD полностью совпали с PCA: 30,97; 22,95; 19,30; "
        "18,29 и 8,49 %. Это ожидаемо, поскольку оба метода применяются к одной и той же "
        "центрированной матрице признаков, а собственные числа ковариационной матрицы "
        "равны квадратам сингулярных чисел, делённым на число наблюдений. Оценки UΣ "
        "совпадают с оценками PCA с точностью до знака; после согласования знаков "
        "двумерные проекции практически неразличимы. Преимущество SVD состоит не в другой "
        "доле дисперсии, а в вычислительной устойчивости: метод не требует явного "
        "построения ковариационной матрицы.",
    )

    _add_heading(doc, "1.5 Анализ независимых компонент", level=2)
    _add_body(
        doc,
        "Для поиска статистически независимых скрытых источников был применён ICA "
        "с реализацией FastICA. Количество компонент последовательно изменялось от одной "
        "до пяти, после чего данные восстанавливались обратным преобразованием и "
        "рассчитывалась среднеквадратичная ошибка (MSE — Mean Squared Error).",
    )
    _add_figure(doc, "fig05_ica_reconstruction.png",
                "Рисунок 5 — Ошибка восстановления данных методом ICA", width_cm=13.8)
    _add_body(
        doc,
        f"Ошибка восстановления уменьшается с {_num(ica_mse[0], 4)} при одной компоненте "
        f"до {_num(ica_mse[1], 4)} при двух, {_num(ica_mse[2], 4)} при трёх, "
        f"{_num(ica_mse[3], 4)} при четырёх и практически до нуля при пяти. При пяти "
        "компонентах преобразование является полным, поэтому исходная матрица "
        "восстанавливается точно; этот результат не означает, что пять компонент "
        "необходимы для содержательного анализа. Компоненты ICA не упорядочены по "
        "объяснённой дисперсии, а их порядок зависит от начального приближения.",
    )
    _add_body(
        doc,
        "Важно отметить, что значения MSE ICA совпадают с остаточной дисперсией PCA той же "
        "размерности. FastICA выполняет предварительное сокращение размерности и "
        "отбеливание, поэтому при n компонентах сохраняется то же линейное подпространство, "
        "что и у первых n главных компонент. Следовательно, кривая ошибки ICA "
        "характеризует качество сжатия, а не степень независимости источников. "
        "Все запуски завершились сходимостью; число итераций составило "
        f"{', '.join(str(v) for v in ica['iterations'])}.",
    )

    _add_heading(doc, "1.6 Сопоставление методов", level=2)
    _add_figure(doc, "fig06_methods_comparison.png",
                "Рисунок 6 — Сопоставление показателей PCA, SVD и ICA", width_cm=16.2)
    _add_body(
        doc,
        "На одном рисунке объединены показатели PCA, SVD и ICA. PCA и SVD демонстрируют "
        "одинаковые доли дисперсии, а ICA — снижение ошибки восстановления. Эти показатели "
        "имеют разный смысл, поэтому их численное сравнение в качестве одной метрики "
        "не проводилось. Для сжатия данных и двумерной визуализации оптимальны PCA и SVD: "
        "они максимизируют сохранённую дисперсию при заданном числе компонент. ICA "
        "целесообразно рассматривать как дополнительный метод поиска независимых "
        "источников, а не как замену PCA.",
    )

    _add_heading(doc, "1.7 Двумерные проекции и направления признаков", level=2)
    _add_body(
        doc,
        "Были построены проекции наблюдений на первые две рассчитанные компоненты и "
        "добавлены нормированные направления исходных признаков в виде красных стрелок. "
        "Эталонные метки использовались исключительно для окрашивания точек.",
    )
    _add_figure(doc, "fig07_projections.png",
                "Рисунок 7 — Двумерные проекции и векторы признаков для PCA, SVD и ICA",
                width_cm=16.4)
    _add_body(
        doc,
        f"Проекции PCA и SVD после согласования знаков практически совпали. Векторы a и c "
        f"направлены почти одинаково, что соответствует корреляции {_num(c_ac, 3)}. "
        "Проекция ICA отличается поворотом и порядком осей. На всех трёх панелях классы "
        "существенно перекрываются: первые две компоненты объясняют лишь "
        f"{_pct(explained[0] + explained[1])} дисперсии, поэтому двумерное представление "
        "не обеспечивает полного разделения классов. Для ICA оси не имеют смысла "
        "объяснённой дисперсии, а порядок компонент произволен.",
    )

    # Раздел 2
    _add_heading(doc, "2 ИССЛЕДОВАНИЕ АЛГОРИТМОВ КЛАСТЕРИЗАЦИИ", level=1)
    _add_heading(doc, "2.1 Исходные данные и эталонная структура", level=2)
    counts = p2["dataset"]["class_counts"]
    _add_body(
        doc,
        f"Во второй части используются {p2['dataset']['n_samples']} наблюдений по двум "
        f"признакам a и b. Эталонные метки образуют четыре класса численностью "
        f"{counts['0']}, {counts['1']}, {counts['2']} и {counts['3']}. Пропусков и "
        "дубликатов нет. Перед обучением моделей признаки были стандартизированы, чтобы "
        "различие масштабов не искажало расстояния.",
    )
    _add_figure(doc, "fig08_initial_data.png",
                "Рисунок 8 — Исходное распределение и эталонные классы", width_cm=16.2)
    _add_body(
        doc,
        "Слева изображены наблюдения без меток, справа — те же точки с цветами эталонных "
        "классов. Данные образуют несколько вытянутых диагональных групп, которые "
        "пересекаются и не являются компактными сферическими облаками. Внутри классов "
        "коэффициенты корреляции a и b равны −0,991; 0,859; 0,980 и 0,436, то есть классы "
        "представляют собой почти линейные вытянутые структуры. Это объясняет, почему "
        "алгоритмы, ориентированные на компактные сферические кластеры, могут показывать "
        "слабое согласие с эталоном, а модель гауссовской смеси с полной ковариационной "
        "матрицей имеет преимущество.",
    )

    _add_heading(doc, "2.2 Выбор числа кластеров и параметров", level=2)
    elbow = p2["elbow"]
    inertia = elbow["inertia"]
    _add_body(
        doc,
        "Для K-Means последовательно задавалось число кластеров от 1 до 10 и "
        "рассчитывалась инерция — сумма квадратов расстояний до центров кластеров. "
        f"Инерция уменьшилась с {_num(inertia[0], 1)} при k = 1 до {_num(inertia[1], 1)} "
        f"при k = 2, {_num(inertia[2], 1)} при k = 3, {_num(inertia[3], 1)} при k = 4 и "
        f"{_num(inertia[4], 1)} при k = 5. Наибольшие снижения приходятся на переходы "
        "1 → 2 и 2 → 3, после k = 4 кривая выполаживается. Это служит аргументом в пользу "
        "четырёх групп.",
    )
    _add_body(
        doc,
        f"Средний коэффициент силуэта при k = 4 равен "
        f"{_num(p2['kmeans_silhouette']['mean'], 3)}; максимум по сетке достигается при "
        f"k = 7 ({_num(elbow['silhouette'][6], 3)}). Силуэт склонен дробить вытянутые "
        "группы на более мелкие компактные фрагменты, поэтому формальный максимум не "
        "обязательно соответствует содержательному числу классов. С учётом метода локтя "
        "и наличия четырёх эталонных классов для всех алгоритмов, требующих число "
        "кластеров, было принято k = 4; это также обеспечивает сопоставимость результатов.",
    )
    _add_figure(doc, "fig09_elbow_silhouette.png",
                "Рисунок 9 — Метод локтя и зависимость силуэта K-Means от числа кластеров",
                width_cm=16.2)
    _add_body(
        doc,
        f"Для выбранного k = 4 размеры кластеров K-Means составили "
        f"{', '.join(str(v) for v in p2['kmeans_silhouette']['cluster_sizes'].values())} "
        f"наблюдений, а средние силуэты по кластерам — "
        f"{', '.join(_num(v, 3) for v in p2['kmeans_silhouette']['per_cluster'].values())}. "
        "У части объектов коэффициенты близки к нулю или отрицательны, что указывает на "
        "пересечение групп и неоднозначную принадлежность.",
    )
    _add_figure(doc, "fig10_silhouette.png",
                "Рисунок 10 — Силуэтный анализ K-Means при k = 4", width_cm=13.6)

    doc.add_page_break()
    _add_caption(doc, "Таблица 2 — Параметры алгоритмов кластеризации")
    param_rows = [[item["name"], _format_parameters(item["params"])] for item in algorithms]
    _add_table(
        doc,
        ["Алгоритм", "Параметры (нотация scikit-learn)"],
        param_rows,
        widths_cm=[5.2, 11.0],
        font_size=9,
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
    )
    _add_body(
        doc,
        "Параметры подбирались по предварительной сетке с использованием только внутренних "
        "метрик (силуэт, доля шумовых точек, устойчивость результата); эталонные метки "
        "в подборе не участвовали. Для методов, требующих число кластеров, задано k = 4. "
        "Для Affinity Propagation выбрано предпочтение, равное 5-му процентилю матрицы "
        "сходства, для Mean Shift — ширина окна, оценённая по квантили 0,1. Параметры "
        "плотностных алгоритмов выбирались компромиссно: требовалось получить от двух до "
        "восьми кластеров при доле шума не более примерно 25 %. Для Gaussian Mixture "
        "использована полная ковариационная матрица как наиболее гибкая модель, "
        "соответствующая вытянутой форме групп.",
    )

    _add_heading(doc, "2.3 Сравнение двенадцати алгоритмов", level=2)
    _add_body(
        doc,
        "Были исследованы 12 алгоритмов: K-Means, Affinity Propagation, Mean Shift, "
        "Spectral Clustering, Ward, Agglomerative Clustering, DBSCAN, HDBSCAN, OPTICS, "
        "Gaussian Mixture, BIRCH и Bisecting K-Means. Для каждого алгоритма модель "
        "обучалась на одних и тех же стандартизированных признаках. Цветом показаны "
        "найденные кластеры, чёрными крестами — шумовые точки. Для читаемости результаты "
        "разделены на две панели по шесть алгоритмов.",
    )
    _add_figure(
        doc,
        "fig11_algorithms_part1.png",
        "Рисунок 11 — Результаты кластеризации: K-Means, Affinity Propagation, "
        "Mean Shift, Spectral Clustering, Ward и Agglomerative",
        width_cm=16.2,
    )
    _add_figure(
        doc,
        "fig12_algorithms_part2.png",
        "Рисунок 12 — Результаты кластеризации: DBSCAN, HDBSCAN, OPTICS, "
        "Gaussian Mixture, BIRCH и Bisecting K-Means",
        width_cm=16.2,
    )
    gmm = alg["Gaussian Mixture"]
    _add_body(
        doc,
        "K-Means, Ward, Agglomerative, BIRCH и Bisecting K-Means выделили по четыре "
        "компактные группы, однако границы этих групп не совпадают с вытянутыми "
        "эталонными классами: алгоритмы разрезают диагональные структуры поперёк. "
        "Их ARI находится в диапазоне от 0,167 до 0,224. Spectral Clustering, "
        "учитывающий локальные связи, показал лучшее согласие (ARI = 0,272). "
        "Affinity Propagation и Mean Shift с выбранными параметрами сформировали по девять "
        "кластеров, то есть переоценили число групп; при этом их силуэт выше (0,461 и "
        "0,455), поскольку мелкие кластеры компактны, но с эталоном они согласуются слабо. "
        "Плотностные методы отметили часть точек как шум и не восстановили четыре класса.",
    )
    _add_body(
        doc,
        f"Наилучшее совпадение с эталонной разметкой показала Gaussian Mixture: "
        f"ARI = {_num(gmm['ari'], 3)}, NMI = {_num(gmm['nmi'], 3)}, четыре кластера, "
        f"шумовых точек нет. Размеры её кластеров — "
        f"{', '.join(str(v) for v in gmm['cluster_sizes'].values())}. Модель с полной "
        "ковариационной матрицей описывает вытянутые эллиптические компоненты, поэтому "
        "лучше соответствует геометрии данных, чем центроидные методы.",
    )

    _add_heading(doc, "2.4 Иерархическая кластеризация", level=2)
    _add_figure(doc, "fig13_dendrogram.png",
                "Рисунок 13 — Дендрограмма метода Ward", width_cm=15.6)
    _add_body(
        doc,
        "Дендрограмма построена по критерию Ward; для читаемости показаны последние "
        "20 объединений, высота ветвей отражает расстояние слияния групп. Последние "
        "объединения происходят на расстояниях примерно 9,3; 11,5 и 13,4, то есть "
        "четыре крупные ветви можно выделить до окончательного слияния. Вместе с тем "
        "внутренняя структура ветвей неоднородна, а классы пересекаются, поэтому "
        "дендрограмма использовалась как вспомогательное средство проверки, а не как "
        "основной способ выбора числа кластеров. Ward показал ARI = 0,172 и NMI = 0,325.",
    )

    _add_heading(doc, "2.5 Выявление шума и выбросов", level=2)
    _add_figure(doc, "fig14_noise.png",
                "Рисунок 14 — Кластеры и шум по результатам DBSCAN, HDBSCAN и OPTICS",
                width_cm=16.2)
    dbscan = alg["DBSCAN"]
    hdbscan = alg["HDBSCAN"]
    optics = alg["OPTICS"]
    _add_body(
        doc,
        f"Были сопоставлены результаты трёх плотностных алгоритмов. Метка −1 изображена "
        f"чёрными крестами как кандидат в выбросы, а не как доказанная ошибка измерения. "
        f"При выбранных параметрах DBSCAN отметил {dbscan['n_noise']} шумовых точек "
        f"({_pct(dbscan['noise_share'], 1)}), HDBSCAN — {hdbscan['n_noise']} "
        f"({_pct(hdbscan['noise_share'], 1)}), OPTICS — {optics['n_noise']} "
        f"({_pct(optics['noise_share'], 1)}). Шумовые точки расположены преимущественно "
        "на периферии облака и между группами. Результат сильно зависит от параметров "
        "локальной плотности: при увеличении допустимого радиуса доля шума падает, но "
        "кластеры сливаются. Поэтому методы пригодны для предварительного отбора "
        "подозрительных наблюдений, но не заменяют содержательной проверки.",
    )

    _add_heading(doc, "2.6 Количественная оценка качества", level=2)
    _add_body(
        doc,
        "Для проверки соответствия эталонным классам были рассчитаны скорректированный "
        "индекс Рэнда (ARI — Adjusted Rand Index) и нормализованная взаимная информация "
        "(NMI — Normalized Mutual Information). Для внутренней оценки разделения "
        "использовался коэффициент силуэта (Silhouette Score). В таблице также указаны "
        "количество кластеров и число шумовых наблюдений.",
    )
    doc.add_page_break()
    _add_caption(doc, "Таблица 3 — Результаты кластеризации варианта 4")
    metric_rows = []
    for item in algorithms:
        metric_rows.append([
            item["name"],
            str(item["n_clusters"]),
            str(item["n_noise"]),
            _num(item["silhouette"], 3),
            _num(item["ari"], 3),
            _num(item["nmi"], 3),
        ])
    _add_table(
        doc,
        ["Алгоритм", "Кластеров", "Шум", "Silhouette", "ARI", "NMI"],
        metric_rows,
        widths_cm=[5.0, 2.3, 1.8, 2.6, 2.3, 2.3],
        font_size=9.5,
        alignments=[WD_ALIGN_PARAGRAPH.LEFT] + [WD_ALIGN_PARAGRAPH.CENTER] * 5,
    )
    _add_body(
        doc,
        f"По таблице установлено, что Gaussian Mixture получил наибольшие значения "
        f"ARI = {_num(best['ari'], 3)} и NMI = {_num(best['nmi'], 3)}, выделив четыре "
        f"кластера без шумовых меток. Следом расположились Spectral Clustering "
        f"(ARI = {_num(alg['Spectral Clustering']['ari'], 3)}), Agglomerative "
        f"(ARI = {_num(alg['Agglomerative']['ari'], 3)}) и Mean Shift "
        f"(ARI = {_num(alg['Mean Shift']['ari'], 3)}). Хотя OPTICS имеет высокий "
        f"коэффициент силуэта ({_num(optics['silhouette'], 3)}), он рассчитан только по "
        f"{optics['n_clusters']} компактным ядрам, а {_pct(optics['noise_share'], 1)} "
        "наблюдений объявлены шумом, поэтому напрямую сравнивать этот силуэт с остальными "
        "некорректно. Аналогично высокий силуэт Affinity Propagation и Mean Shift "
        "обусловлен переоценкой числа кластеров, а не лучшим соответствием эталону.",
    )
    _add_body(
        doc,
        f"Низкий силуэт Gaussian Mixture ({_num(gmm['silhouette'], 3)}) объясняется тем, "
        "что компоненты вытянуты и перекрываются: метрика штрафует такую геометрию, хотя "
        "именно она соответствует данным. Поэтому для данной задачи решающими являются "
        "внешние метрики ARI и NMI, по которым Gaussian Mixture уверенно опережает "
        "остальные алгоритмы. Согласие ARI ≈ 0,54 является умеренным, а не идеальным: "
        "классы частично пересекаются, и полное восстановление эталонной разметки "
        "в пространстве двух признаков невозможно.",
    )

    # Вывод
    _add_heading(doc, "ВЫВОД", level=1)
    _add_body(
        doc,
        f"В ходе выполнения лабораторной работы была достигнута поставленная цель: "
        f"исследованы методы снижения размерности и сравнены 12 алгоритмов кластеризации "
        f"на данных варианта 4. В первой части проанализированы "
        f"{p1['dataset']['n_samples']} наблюдений с пятью признаками. Матрица корреляций "
        f"показала умеренную связь только между a и c ({_num(c_ac, 3)}); остальные "
        "линейные связи слабые. Матрица разброса подтвердила частичное перекрытие классов "
        "и отсутствие выраженных нелинейных зависимостей.",
    )
    _add_body(
        doc,
        f"Методы PCA и SVD дали одинаковые доли объяснённой дисперсии: первые две "
        f"компоненты сохраняют {_pct(explained[0] + explained[1])}, три — "
        f"{_pct(cumulative[2])}, четыре — {_pct(cumulative[3])}. Для превышения порога "
        f"80 % необходимы {pca['n_components_80']} компоненты, поэтому сжатие до двух "
        "измерений пригодно главным образом для визуализации. В ICA ошибка восстановления "
        "уменьшалась с ростом числа компонент до нуля при полном базисе; при этом она "
        "совпала с остаточной дисперсией PCA, поскольку FastICA выполняет предварительное "
        "отбеливание. Это показывает, что ICA не даёт выигрыша в сжатии и должна "
        "рассматриваться как дополнительный метод поиска независимых источников.",
    )
    _add_body(
        doc,
        f"Во второй части исследованы {p2['dataset']['n_samples']} наблюдений по двум "
        "признакам. Эталонные классы оказались вытянутыми и пересекающимися, с сильной "
        "внутриклассовой корреляцией. Метод локтя и содержательная интерпретация "
        "указали на четыре кластера; силуэт K-Means при k = 4 составил "
        f"{_num(p2['kmeans_silhouette']['mean'], 3)}. Сравнение 12 алгоритмов показало, "
        f"что наилучшее соответствие эталону обеспечивает Gaussian Mixture с полной "
        f"ковариационной матрицей: ARI = {_num(best['ari'], 3)}, "
        f"NMI = {_num(best['nmi'], 3)}, четыре кластера и отсутствие шумовых меток. "
        "Spectral Clustering занял второе место, а центроидные и плотностные методы "
        "показали более слабое согласие.",
    )
    _add_body(
        doc,
        "Плотностные алгоритмы DBSCAN, HDBSCAN и OPTICS позволяют выделить кандидатов "
        "в выбросы, однако их результат сильно зависит от параметров и доли шума. "
        "Для данной задачи они могут использоваться как вспомогательный инструмент "
        "контроля качества, но не как основной метод кластеризации. Практическая "
        "рекомендация по результатам работы — применять Gaussian Mixture с полной "
        "ковариационной матрицей, а PCA или SVD — для предварительной визуализации. "
        "Таким образом, все поставленные задачи выполнены, цель работы достигнута.",
    )

    # Список источников
    _add_heading(doc, "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", level=1)
    sources = [
        "1. Воронцов К. В. Математические методы обучения по прецедентам (теория обучения машин). — М.: МФТИ, 2011. — 141 с.",
        "2. Джеймс Г., Уиттон Д., Хасти Т., Тибширани Р. Введение в статистическое обучение с примерами на языке R. — М.: ДМК Пресс, 2016. — 450 с.",
        "3. Scikit-learn: Machine Learning in Python. User Guide. — URL: https://scikit-learn.org/stable/user_guide.html (дата обращения: 02.11.2026).",
        "4. Pandas: Python Data Analysis Library. User Guide. — URL: https://pandas.pydata.org/docs/user_guide/ (дата обращения: 02.11.2026).",
        "5. Hyndman R. J., Athanasopoulos G. Forecasting: Principles and Practice. — 3rd ed. — Melbourne: OTexts, 2021.",
    ]
    for source in sources:
        _add_body(doc, source, first_indent=0.0)

    # Приложение
    _add_heading(doc, "ПРИЛОЖЕНИЕ А. СТРУКТУРА И ЗАПУСК ПРОЕКТА", level=1)
    _add_body(
        doc,
        "Проект оформлен в виде набора модулей Python и открывается в Visual Studio Code "
        "как обычная папка. Все пути вычисляются относительно корня проекта, поэтому "
        "запуск не зависит от текущего каталога.",
    )
    _add_code_block(
        doc,
        "lab2_ml/\n"
        "├── data/                 исходные книги Excel\n"
        "├── src/                  модули анализа и сборки отчёта\n"
        "│   ├── config.py         вариант, пути, параметры\n"
        "│   ├── data_loader.py    чтение блока варианта 4\n"
        "│   ├── part1_dimensionality.py\n"
        "│   ├── part2_clustering.py\n"
        "│   └── report_builder.py\n"
        "├── scripts/              точки запуска\n"
        "│   ├── run_part1.py\n"
        "│   ├── run_part2.py\n"
        "│   ├── run_all.py\n"
        "│   └── build_report.py\n"
        "├── figures/              сохранённые рисунки\n"
        "├── results/              JSON и CSV с метриками\n"
        "├── report/               итоговый отчёт DOCX\n"
        "└── requirements.txt",
    )
    _add_body(
        doc,
        "Порядок запуска в терминале Visual Studio Code (PowerShell):",
    )
    _add_code_block(
        doc,
        "python -m venv .venv\n"
        ".venv\\Scripts\\Activate.ps1\n"
        "pip install -r requirements.txt\n"
        "python scripts/run_all.py",
    )
    _add_body(
        doc,
        "Скрипт run_all.py выполняет обе части работы: сохраняет рисунки в figures, "
        "метрики — в results и формирует отчёт в каталоге report. В стохастических "
        "алгоритмах зафиксирован random_state = 42; части можно запускать отдельно "
        "скриптами run_part1.py и run_part2.py.",
    )

    output_path = REPORT_DIR / "Лабораторная_работа_2_Вариант_4.docx"
    doc.save(output_path)
    return output_path


if __name__ == "__main__":
    path = build_report()
    print(f"Отчёт сохранён: {path}")
