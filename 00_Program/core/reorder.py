"""カラム並べ替え — メモリベース純粋関数版

データファイルのカラム順をテンプレートファイルのヘッダ順に揃える。
"""
from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Dict, List, Tuple

from .common import (
    decode_utf8_sig,
    delimiter_label,
    jst_timestamp,
    norm_key,
    resolve_delimiter_for_bytes,
    sanitize_stem,
    summary_dict_to_bytes,
)


def reorder_columns(
    data_bytes: bytes,
    template_bytes: bytes,
    *,
    delimiter_a: str = "auto",
    delimiter_b: str = "auto",
    data_stem: str = "data",
    template_stem: str = "template",
    data_name: str = "",
    template_name: str = "",
) -> Tuple[Dict[str, bytes], Dict[str, Any]]:
    """data_bytes のカラム順を template_bytes のヘッダ順に揃える。"""
    delim_a = resolve_delimiter_for_bytes(delimiter_a, data_bytes)
    delim_b = resolve_delimiter_for_bytes(delimiter_b, template_bytes)

    # template の header を取得
    text_b = decode_utf8_sig(template_bytes)
    reader_b = csv.reader(StringIO(text_b), delimiter=delim_b)
    header_b = next(reader_b, None)
    if header_b is None or len(header_b) == 0:
        raise ValueError("template file has no header")

    # data の header と全行を取得
    text_a = decode_utf8_sig(data_bytes)
    reader_a = csv.DictReader(StringIO(text_a), delimiter=delim_a)
    header_a = list(reader_a.fieldnames or [])
    if not header_a:
        raise ValueError("data file has no header")
    rows_a: List[Dict[str, Any]] = list(reader_a)

    # data の正規化キー → 元の列名マップ
    norm_to_a: Dict[str, str] = {}
    norm_dup_a: List[str] = []
    for col in header_a:
        nk = norm_key(col)
        if nk in norm_to_a:
            norm_dup_a.append(col)
        else:
            norm_to_a[nk] = col

    # template 順にマッチさせる
    matched_columns: List[Tuple[str, str]] = []
    missing_columns: List[str] = []
    matched_a_norms: set = set()

    for tcol in header_b:
        nk = norm_key(tcol)
        if nk in norm_to_a:
            matched_columns.append((tcol, norm_to_a[nk]))
            matched_a_norms.add(nk)
        else:
            missing_columns.append(tcol)

    # data にあって template に無いカラム
    extra_columns: List[str] = []
    for col in header_a:
        nk = norm_key(col)
        if nk not in matched_a_norms:
            extra_columns.append(col)

    # 出力ヘッダ
    out_header: List[str] = []
    for tcol, _acol in matched_columns:
        out_header.append(tcol)
    for tcol in missing_columns:
        out_header.append(tcol)
    for acol in extra_columns:
        out_header.append(acol)

    # 出力行
    out_rows: List[List[str]] = []
    for row in rows_a:
        out_row: List[str] = []
        for _tcol, acol in matched_columns:
            val = row.get(acol)
            out_row.append(val if val is not None else "")
        for _tcol in missing_columns:
            out_row.append("")
        for acol in extra_columns:
            val = row.get(acol)
            out_row.append(val if val is not None else "")
        out_rows.append(out_row)

    data_row_count = len(out_rows)
    a_stem = sanitize_stem(data_stem)
    out_name = f"reordered_{a_stem}_{data_row_count}.csv"
    summary_name = "summary.txt"

    # CSV 書き出し
    buf = StringIO(newline="")
    w = csv.writer(buf, delimiter=delim_a)
    w.writerow(out_header)
    w.writerows(out_rows)
    out_bytes = buf.getvalue().encode("utf-8")

    delim_a_lbl = delimiter_label(delim_a)
    delim_b_lbl = delimiter_label(delim_b)

    summary: Dict[str, Any] = {
        "time(JST)": jst_timestamp(),
        "file_A": data_name or data_stem,
        "file_B": template_name or template_stem,
        "delimiter_A": delim_a_lbl,
        "delimiter_B": delim_b_lbl,
        "columns_in_A": len(header_a),
        "columns_in_B": len(header_b),
        "matched_columns": len(matched_columns),
        "missing_in_A": len(missing_columns),
        "extra_in_A": len(extra_columns),
        "data_rows": data_row_count,
    }
    if norm_dup_a:
        summary["warning_dup"] = f"duplicate_norm_key_in_A (data dropped): {','.join(norm_dup_a)}"
    if missing_columns:
        summary["warning_missing"] = f"missing_in_A (added as empty): {missing_columns}"
    if extra_columns:
        summary["warning_extra"] = f"extra_in_A (appended at end): {extra_columns}"
    summary["_outputs"] = [out_name, summary_name]

    files: Dict[str, bytes] = {out_name: out_bytes}
    files[summary_name] = summary_dict_to_bytes(summary)
    return files, summary
