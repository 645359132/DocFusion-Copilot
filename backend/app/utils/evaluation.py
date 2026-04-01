from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from app.models.domain import FactRecord
from app.utils.normalizers import (
    convert_to_canonical_unit,
    extract_numeric_with_unit,
    normalize_entity_name,
    normalize_field_name,
)
from app.utils.spreadsheet import build_cell_ref, load_xlsx
from app.utils.wordprocessing import load_docx_tables


def evaluate_extracted_facts(
    predicted_facts: list[FactRecord],
    expected_items: list[dict[str, object]],
) -> dict[str, object]:
    """评估抽取事实与标注答案的一致性。    Evaluate extracted facts against labeled expectations."""

    expected_labels = [_normalize_expected_fact(item) for item in expected_items]
    predicted_labels = [_normalize_predicted_fact(fact) for fact in predicted_facts]

    matched_predicted_indexes: set[int] = set()
    matched_count = 0
    missing_items: list[dict[str, object]] = []

    for expected in expected_labels:
        matched_index = _find_matching_prediction(expected, predicted_labels, matched_predicted_indexes)
        if matched_index is None:
            missing_items.append(expected)
            continue
        matched_predicted_indexes.add(matched_index)
        matched_count += 1

    unexpected_items = [
        predicted
        for index, predicted in enumerate(predicted_labels)
        if index not in matched_predicted_indexes
    ]

    expected_count = len(expected_labels)
    predicted_count = len(predicted_labels)
    precision = matched_count / predicted_count if predicted_count else 0.0
    recall = matched_count / expected_count if expected_count else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0

    per_field = _summarize_field_metrics(expected_labels, predicted_labels, matched_predicted_indexes)
    mismatches = [
        {"kind": "missing", **item}
        for item in missing_items[:25]
    ] + [
        {"kind": "unexpected", **item}
        for item in unexpected_items[:25]
    ]

    return {
        "expected_count": expected_count,
        "predicted_count": predicted_count,
        "matched_count": matched_count,
        "accuracy": round(recall, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "meets_threshold_0_80": recall >= 0.8,
        "per_field": per_field,
        "mismatches": mismatches,
    }


def compare_filled_templates(
    *,
    template_path: str | Path,
    generated_path: str | Path,
    expected_path: str | Path,
) -> dict[str, object]:
    """比较模板回填结果与期望结果的差异。    Compare a filled template against an expected result."""

    template_file = Path(template_path)
    generated_file = Path(generated_path)
    expected_file = Path(expected_path)
    suffix = expected_file.suffix.lower()
    if suffix != generated_file.suffix.lower() or suffix != template_file.suffix.lower():
        raise ValueError("Template, generated result and expected result must share the same file suffix.")

    if suffix == ".xlsx":
        comparison_rows = _build_xlsx_comparisons(template_file, generated_file, expected_file)
    elif suffix == ".docx":
        comparison_rows = _build_docx_comparisons(template_file, generated_file, expected_file)
    else:
        raise ValueError(f"Unsupported benchmark template type: {suffix}")

    total_cells = len(comparison_rows)
    matched_cells = sum(1 for item in comparison_rows if item["matched"])
    accuracy = matched_cells / total_cells if total_cells else 1.0
    mismatches = [item for item in comparison_rows if not item["matched"]][:50]

    error_counts = _classify_errors(mismatches)

    return {
        "total_compared_cells": total_cells,
        "matched_cells": matched_cells,
        "accuracy": round(accuracy, 4),
        "meets_threshold_0_80": accuracy >= 0.8,
        "error_counts": error_counts,
        "mismatches": mismatches,
    }


def _normalize_expected_fact(item: dict[str, object]) -> dict[str, object]:
    """标准化一条标注事实。    Normalize one labeled fact item."""

    field_name_raw = str(item.get("field_name", "")).strip()
    canonical_field_name = normalize_field_name(field_name_raw) or field_name_raw
    entity_name = normalize_entity_name(str(item.get("entity_name", "")))
    year = _as_optional_int(item.get("year"))
    value_num = _as_optional_float(item.get("value_num"))
    value_text = str(item.get("value_text", "")).strip()
    unit = str(item.get("unit", "")).strip() or None

    if value_num is None and value_text:
        parsed_num, parsed_unit = extract_numeric_with_unit(value_text)
        value_num = parsed_num
        unit = unit or parsed_unit
    if value_num is not None:
        value_num, unit = convert_to_canonical_unit(canonical_field_name, value_num, unit)

    return {
        "entity_name": entity_name,
        "field_name": canonical_field_name,
        "year": year,
        "value_num": value_num,
        "value_text": _normalize_text(value_text),
        "unit": unit,
    }


def _normalize_predicted_fact(fact: FactRecord) -> dict[str, object]:
    """标准化一条预测事实。    Normalize one predicted fact item."""

    return {
        "entity_name": normalize_entity_name(fact.entity_name),
        "field_name": fact.field_name,
        "year": fact.year,
        "value_num": fact.value_num,
        "value_text": _normalize_text(fact.value_text),
        "unit": fact.unit,
    }


def _find_matching_prediction(
    expected: dict[str, object],
    predicted_labels: list[dict[str, object]],
    matched_predicted_indexes: set[int],
) -> int | None:
    """在未匹配预测中寻找与期望事实一致的一条。    Find one unmatched prediction that agrees with the expected fact."""

    for index, predicted in enumerate(predicted_labels):
        if index in matched_predicted_indexes:
            continue
        if predicted["entity_name"] != expected["entity_name"]:
            continue
        if predicted["field_name"] != expected["field_name"]:
            continue
        if expected["year"] is not None and predicted["year"] != expected["year"]:
            continue
        if _fact_values_equal(expected, predicted):
            return index
    return None


def _fact_values_equal(expected: dict[str, object], predicted: dict[str, object]) -> bool:
    """判断两条事实的值是否视为一致。    Return whether two normalized fact values should be treated as equal."""

    if expected["value_num"] is not None:
        predicted_value_num = _as_optional_float(predicted.get("value_num"))
        if predicted_value_num is None:
            return False
        return math.isclose(expected["value_num"], predicted_value_num, rel_tol=1e-4, abs_tol=1e-6)
    return expected["value_text"] == predicted["value_text"]


def _summarize_field_metrics(
    expected_labels: list[dict[str, object]],
    predicted_labels: list[dict[str, object]],
    matched_predicted_indexes: set[int],
) -> dict[str, dict[str, float | int]]:
    """按字段汇总评测指标。    Summarize evaluation metrics per field."""

    field_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"expected": 0, "predicted": 0, "matched": 0})
    for item in expected_labels:
        field_stats[str(item["field_name"])]["expected"] += 1
    for item in predicted_labels:
        field_stats[str(item["field_name"])]["predicted"] += 1
    for index in matched_predicted_indexes:
        field_name = str(predicted_labels[index]["field_name"])
        field_stats[field_name]["matched"] += 1

    return {
        field_name: {
            "expected": stats["expected"],
            "predicted": stats["predicted"],
            "matched": stats["matched"],
            "accuracy": round(stats["matched"] / stats["expected"], 4) if stats["expected"] else 1.0,
            "precision": round(stats["matched"] / stats["predicted"], 4) if stats["predicted"] else 0.0,
        }
        for field_name, stats in sorted(field_stats.items())
    }


def _build_xlsx_comparisons(
    template_path: Path,
    generated_path: Path,
    expected_path: Path,
) -> list[dict[str, object]]:
    """构建 XLSX 模板回填对比项。    Build comparison rows for an XLSX template benchmark."""

    template_doc = load_xlsx(template_path)
    generated_doc = load_xlsx(generated_path)
    expected_doc = load_xlsx(expected_path)

    template_cells = _xlsx_cell_map(template_doc)
    generated_cells = _xlsx_cell_map(generated_doc)
    expected_cells = _xlsx_cell_map(expected_doc)

    target_keys = sorted(
        key
        for key in set(template_cells) | set(expected_cells)
        if _normalize_text(expected_cells.get(key, "")) != _normalize_text(template_cells.get(key, ""))
    )
    return [
        _build_cell_comparison(
            location=f"{key[0]}!{key[1]}",
            expected_value=expected_cells.get(key, ""),
            actual_value=generated_cells.get(key, ""),
        )
        for key in target_keys
    ]


def _build_docx_comparisons(
    template_path: Path,
    generated_path: Path,
    expected_path: Path,
) -> list[dict[str, object]]:
    """构建 DOCX 模板回填对比项。    Build comparison rows for a DOCX template benchmark."""

    template_doc = load_docx_tables(template_path)
    generated_doc = load_docx_tables(generated_path)
    expected_doc = load_docx_tables(expected_path)

    template_cells = _docx_cell_map(template_doc)
    generated_cells = _docx_cell_map(generated_doc)
    expected_cells = _docx_cell_map(expected_doc)

    target_keys = sorted(
        key
        for key in set(template_cells) | set(expected_cells)
        if _normalize_text(expected_cells.get(key, "")) != _normalize_text(template_cells.get(key, ""))
    )
    return [
        _build_cell_comparison(
            location=f"{key[0]}!R{key[1]}C{key[2]}",
            expected_value=expected_cells.get(key, ""),
            actual_value=generated_cells.get(key, ""),
        )
        for key in target_keys
    ]


def _xlsx_cell_map(document) -> dict[tuple[str, str], str]:
    """将 XLSX 文档转换为单元格映射。    Convert an XLSX document into a cell-value map."""

    cell_map: dict[tuple[str, str], str] = {}
    for sheet in document.sheets:
        for row in sheet.rows:
            for column_index, value in enumerate(row.values, start=1):
                if value == "":
                    continue
                cell_map[(sheet.name, build_cell_ref(row.row_index, column_index))] = str(value)
    return cell_map


def _docx_cell_map(document) -> dict[tuple[str, int, int], str]:
    """将 DOCX 表格文档转换为单元格映射。    Convert a DOCX table document into a cell-value map."""

    cell_map: dict[tuple[str, int, int], str] = {}
    for table in document.tables:
        for row in table.rows:
            for column_index, value in enumerate(row.values, start=1):
                if value == "":
                    continue
                cell_map[(table.name, row.row_index, column_index)] = str(value)
    return cell_map


def _build_cell_comparison(location: str, expected_value: object, actual_value: object) -> dict[str, object]:
    """构建单个单元格对比结果。    Build one cell-comparison result item."""

    matched = _values_equal(expected_value, actual_value)
    error_type = _classify_cell_error(expected_value, actual_value) if not matched else None
    result: dict[str, object] = {
        "location": location,
        "expected_value": str(expected_value),
        "actual_value": str(actual_value),
        "matched": matched,
    }
    if error_type:
        result["error_type"] = error_type
    return result


def _values_equal(expected_value: object, actual_value: object) -> bool:
    """比较两个单元格值是否等价。    Compare two cell values for semantic equivalence."""

    expected_num = _as_optional_float(expected_value)
    actual_num = _as_optional_float(actual_value)
    if expected_num is not None and actual_num is not None:
        return math.isclose(expected_num, actual_num, rel_tol=1e-4, abs_tol=1e-6)
    return _normalize_text(str(expected_value)) == _normalize_text(str(actual_value))


def _normalize_text(value: str) -> str:
    """规范化文本值。    Normalize a textual value for comparison."""

    return " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip()


def _as_optional_float(value: object) -> float | None:
    """尝试将值转换为浮点数。    Try converting a value into a float."""

    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    candidate = str(value).strip().replace(",", "")
    if not candidate:
        return None
    try:
        return float(candidate)
    except ValueError:
        return None


def _as_optional_int(value: object) -> int | None:
    """尝试将值转换为整数。    Try converting a value into an integer."""

    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    candidate = str(value).strip()
    if not candidate:
        return None
    try:
        return int(candidate)
    except ValueError:
        return None


# ---------- Error classification ----------

_UNIT_FACTORS = {
    (1e4, "万"): True,
    (1e8, "亿"): True,
    (1e12, "万亿"): True,
    (1e2, "%"): True,
}


def _classify_cell_error(expected_value: object, actual_value: object) -> str:
    """将单元格不匹配归类为具体错误类型。    Classify a cell mismatch into a specific error type."""

    actual_text = _normalize_text(str(actual_value))
    if not actual_text:
        return "empty_actual"

    expected_num = _as_optional_float(expected_value)
    actual_num = _as_optional_float(actual_value)

    if expected_num is not None and actual_num is not None:
        if expected_num != 0:
            ratio = actual_num / expected_num
            for factor, _ in _UNIT_FACTORS:
                if math.isclose(ratio, factor, rel_tol=1e-3) or math.isclose(ratio, 1.0 / factor, rel_tol=1e-3):
                    return "unit_conversion_error"
        return "numeric_mismatch"

    return "text_mismatch"


def _classify_errors(mismatches: list[dict[str, object]]) -> dict[str, int]:
    """统计各错误类型数量。    Count occurrences of each error type."""

    counts: dict[str, int] = {}
    for item in mismatches:
        error_type = str(item.get("error_type", "unknown"))
        counts[error_type] = counts.get(error_type, 0) + 1
    return counts


# ---------- Markdown report generation ----------


def generate_benchmark_markdown(report: dict[str, object]) -> str:
    """将 benchmark JSON 报告转换为 Markdown 格式。    Convert a benchmark JSON report into Markdown format."""

    lines: list[str] = []
    task_type = str(report.get("task_type", "unknown"))
    lines.append(f"# 评测报告 — {task_type}")
    lines.append("")
    lines.append(f"- **任务 ID**: `{report.get('task_id', 'N/A')}`")
    lines.append(f"- **耗时**: {report.get('elapsed_seconds', 'N/A')} 秒")

    if task_type == "evaluate_facts":
        lines.append(f"- **期望事实数**: {report.get('expected_count', 0)}")
        lines.append(f"- **预测事实数**: {report.get('predicted_count', 0)}")
        lines.append(f"- **匹配数**: {report.get('matched_count', 0)}")
        lines.append(f"- **准确率**: {report.get('accuracy', 0)}")
        lines.append(f"- **精确率**: {report.get('precision', 0)}")
        lines.append(f"- **召回率**: {report.get('recall', 0)}")
        lines.append(f"- **F1**: {report.get('f1', 0)}")
        lines.append(f"- **达标 (≥0.80)**: {'✅' if report.get('meets_threshold_0_80') else '❌'}")
        per_field = report.get("per_field")
        if isinstance(per_field, dict) and per_field:
            lines.append("")
            lines.append("## 按字段统计")
            lines.append("")
            lines.append("| 字段 | 期望 | 预测 | 匹配 | 准确率 | 精确率 |")
            lines.append("|------|------|------|------|--------|--------|")
            for field_name, stats in per_field.items():
                if isinstance(stats, dict):
                    lines.append(
                        f"| {field_name} | {stats.get('expected', 0)} | {stats.get('predicted', 0)} "
                        f"| {stats.get('matched', 0)} | {stats.get('accuracy', 0)} | {stats.get('precision', 0)} |"
                    )
    elif task_type == "benchmark_template_fill":
        lines.append(f"- **模板**: {report.get('template_name', 'N/A')}")
        lines.append(f"- **比较单元格数**: {report.get('total_compared_cells', 0)}")
        lines.append(f"- **匹配单元格数**: {report.get('matched_cells', 0)}")
        lines.append(f"- **准确率**: {report.get('accuracy', 0)}")
        lines.append(f"- **达标 (≥0.80)**: {'✅' if report.get('meets_threshold_0_80') else '❌'}")
        error_counts = report.get("error_counts")
        if isinstance(error_counts, dict) and error_counts:
            lines.append("")
            lines.append("## 误差分类")
            lines.append("")
            lines.append("| 错误类型 | 数量 |")
            lines.append("|----------|------|")
            _ERROR_TYPE_LABELS = {
                "empty_actual": "未填写 (空值)",
                "numeric_mismatch": "数值错误",
                "unit_conversion_error": "单位换算错误",
                "text_mismatch": "文本不匹配",
                "unknown": "未知",
            }
            for etype, count in error_counts.items():
                label = _ERROR_TYPE_LABELS.get(etype, etype)
                lines.append(f"| {label} | {count} |")

    mismatches = report.get("mismatches")
    if isinstance(mismatches, list) and mismatches:
        lines.append("")
        lines.append("## 不匹配明细（前 50 条）")
        lines.append("")
        lines.append("| 位置 | 期望值 | 实际值 | 类型 |")
        lines.append("|------|--------|--------|------|")
        for item in mismatches[:50]:
            if isinstance(item, dict):
                loc = item.get("location", item.get("kind", ""))
                expected = str(item.get("expected_value", item.get("value_text", "")))[:40]
                actual = str(item.get("actual_value", ""))[:40]
                etype = item.get("error_type", item.get("kind", ""))
                lines.append(f"| {loc} | {expected} | {actual} | {etype} |")

    lines.append("")
    return "\n".join(lines)
