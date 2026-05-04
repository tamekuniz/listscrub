"""重複除去 — メモリベース純粋関数版

CSV/TSV または改行区切りテキストから重複行を除去する。
"""
from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from .common import (
    decode_utf8_sig,
    delimiter_label,
    jst_timestamp,
    norm_key,
    resolve_delimiter_for_bytes,
    summary_dict_to_bytes,
    write_dict_rows_to_bytes,
    write_lines_to_bytes,
    write_list_rows_to_bytes,
)


def dedup(
    src_bytes: bytes,
    *,
    line_mode: bool = False,
    header: bool = False,
    key_col: Optional[str] = None,
    key_index_1based: Optional[int] = None,
    delimiter: str = "auto",
    src_stem: str = "input",
    src_name: str = "",
) -> Tuple[Dict[str, bytes], Dict[str, Any]]:
    """重複除去を行う。

    line_mode=True のときは改行区切りテキストとして処理。
    そうでないときは CSV/TSV として処理。

    戻り値:
      files: {ファイル名: bytes} 出力ファイル群
      summary: 集計値の dict
    """
    ts = jst_timestamp()
    kept_blank_key_rows = 0
    total_data_rows = 0
    dropped_duplicates = 0

    # ========== LINE MODE ==========
    if line_mode:
        text = decode_utf8_sig(src_bytes)
        seen: set = set()
        kept_lines: List[str] = []
        dropped_lines: List[str] = []

        for line in text.splitlines():
            total_data_rows += 1
            k = norm_key(line)
            if not k:
                kept_blank_key_rows += 1
                kept_lines.append(line)
                continue
            if k in seen:
                dropped_duplicates += 1
                dropped_lines.append(line)
                continue
            seen.add(k)
            kept_lines.append(line)

        unique_keys = len(seen)
        kept_count = len(kept_lines)
        dropped_count = len(dropped_lines)

        out_kept_name = f"00_dedup_{src_stem}_{kept_count}.txt"
        out_dropped_name = f"01_dedup_dropped_{src_stem}_{dropped_count}.txt"
        summary_name = "summary.txt"

        files: Dict[str, bytes] = {
            out_kept_name: write_lines_to_bytes(kept_lines),
            out_dropped_name: write_lines_to_bytes(dropped_lines),
        }

        summary: Dict[str, Any] = {
            "time(JST)": ts,
            "source": src_name or src_stem,
            "mode": "line",
            "key": "line",
            "total_data_rows": total_data_rows,
            "unique_keys": unique_keys,
            "kept_rows": kept_count,
            "dropped_duplicates": dropped_duplicates,
            "kept_blank_key_rows": kept_blank_key_rows,
            "_outputs": [out_kept_name, out_dropped_name, summary_name],
        }
        files[summary_name] = summary_dict_to_bytes(summary)
        return files, summary

    # ========== CSV MODE ==========
    delim = resolve_delimiter_for_bytes(delimiter, src_bytes)
    delim_lbl = delimiter_label(delim)

    text = decode_utf8_sig(src_bytes)
    seen = set()
    kept_rows: List[Any] = []
    dropped_rows: List[Any] = []
    fieldnames: Optional[List[str]] = None
    key_desc = ""

    if header:
        reader = csv.DictReader(StringIO(text), delimiter=delim)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise ValueError("header=yes やのにヘッダが見つからへん")

        if len(fieldnames) == 1 and not key_col:
            key_col_use = fieldnames[0]
        else:
            if not key_col or key_col not in fieldnames:
                raise ValueError(f"--key が不正。列={fieldnames}")
            key_col_use = key_col

        key_desc = key_col_use

        for row in reader:
            total_data_rows += 1
            k = norm_key(row.get(key_col_use))
            if not k:
                kept_blank_key_rows += 1
                kept_rows.append(row)
                continue
            if k in seen:
                dropped_duplicates += 1
                dropped_rows.append(row)
                continue
            seen.add(k)
            kept_rows.append(row)

    else:
        reader = csv.reader(StringIO(text), delimiter=delim)
        first = next(reader, None)
        if first is None:
            raise ValueError("空ファイルや")

        col_count = len(first)
        if col_count == 1 and key_index_1based is None:
            key_idx0 = 0
        else:
            if key_index_1based is None:
                raise ValueError(f"複数列（{col_count}列）なので --key-index が必要や")
            if key_index_1based < 1 or key_index_1based > col_count:
                raise ValueError(
                    f"--key-index 範囲不正（指定={key_index_1based}, 列数={col_count}）"
                )
            key_idx0 = key_index_1based - 1

        key_desc = f"index={key_idx0 + 1}"

        def rows():
            yield first
            for r in reader:
                yield r

        for r in rows():
            total_data_rows += 1
            v = r[key_idx0] if key_idx0 < len(r) else ""
            k = norm_key(v)
            if not k:
                kept_blank_key_rows += 1
                kept_rows.append(r)
                continue
            if k in seen:
                dropped_duplicates += 1
                dropped_rows.append(r)
                continue
            seen.add(k)
            kept_rows.append(r)

    unique_keys = len(seen)
    kept_count = len(kept_rows)
    dropped_count = len(dropped_rows)

    out_kept_name = f"00_dedup_{src_stem}_{kept_count}.csv"
    out_dropped_name = f"01_dedup_dropped_{src_stem}_{dropped_count}.csv"
    summary_name = "summary.txt"

    if header:
        assert fieldnames is not None
        kept_bytes = write_dict_rows_to_bytes(fieldnames, kept_rows, delim)
        dropped_bytes = write_dict_rows_to_bytes(fieldnames, dropped_rows, delim)
    else:
        kept_bytes = write_list_rows_to_bytes(kept_rows, delim)
        dropped_bytes = write_list_rows_to_bytes(dropped_rows, delim)

    files = {
        out_kept_name: kept_bytes,
        out_dropped_name: dropped_bytes,
    }

    summary = {
        "time(JST)": ts,
        "source": src_name or src_stem,
        "mode": "csv",
        "header": header,
        "delimiter": delim_lbl,
        "key": key_desc,
        "total_data_rows": total_data_rows,
        "unique_keys": unique_keys,
        "kept_rows": kept_count,
        "dropped_duplicates": dropped_duplicates,
        "kept_blank_key_rows": kept_blank_key_rows,
        "_outputs": [out_kept_name, out_dropped_name, summary_name],
    }
    files[summary_name] = summary_dict_to_bytes(summary)
    return files, summary
