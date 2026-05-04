"""listscrub コア共通ユーティリティ（メモリベース、純粋関数）

CLI 用の I/O 関数（ファイルパス前提のもの）は ../common.py に残す。
ここに置くのは bytes / str / 標準データ構造だけを扱う関数群。
"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone, timedelta
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple


def jst_timestamp() -> str:
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y-%m-%d_%H-%M-%S")


def sanitize_stem(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^\w\.\-\+]+", "", name)
    name = name.strip("._-")
    return name or "file"


def norm_key(s: Optional[str]) -> str:
    if s is None:
        return ""
    return s.strip().strip('"').strip("'").lower()


def sniff_delimiter_from_bytes(data: bytes) -> str:
    sample = data[:8192].decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=["\t", ",", ";"])
        return dialect.delimiter
    except Exception:
        return ","


def resolve_delimiter_for_bytes(arg_value: str, data: bytes) -> str:
    if arg_value == "auto":
        return sniff_delimiter_from_bytes(data)
    return {"tab": "\t", "comma": ",", "semicolon": ";"}[arg_value]


def delimiter_label(delim: str) -> str:
    return "TAB" if delim == "\t" else delim


def decode_utf8_sig(data: bytes) -> str:
    """utf-8-sig（BOM 対応）でデコード。"""
    return data.decode("utf-8-sig", errors="replace")


def make_row_key_from_dict(row: Dict[str, Any], delimiter: str) -> str:
    vals: List[str] = []
    for v in row.values():
        if v is None:
            vals.append("")
        else:
            vals.append(str(v).strip())
    return norm_key(delimiter.join(vals))


def make_row_key_from_list(row: List[Any], delimiter: str) -> str:
    vals: List[str] = []
    for v in row:
        if v is None:
            vals.append("")
        else:
            vals.append(str(v).strip())
    return norm_key(delimiter.join(vals))


def write_dict_rows_to_bytes(
    fieldnames: List[str], rows: List[Dict[str, Any]], delimiter: str
) -> bytes:
    buf = StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fieldnames, delimiter=delimiter)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


def write_list_rows_to_bytes(rows: List[List[Any]], delimiter: str) -> bytes:
    buf = StringIO(newline="")
    w = csv.writer(buf, delimiter=delimiter)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def write_lines_to_bytes(lines: List[str]) -> bytes:
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def summary_dict_to_bytes(summary: Dict[str, Any]) -> bytes:
    """summary dict をテキスト形式に整形して bytes で返す。
    既存 CLI の summary.txt と同じ整形ルール（key=value, 1行1項目、出力一覧は末尾）。
    """
    lines: List[str] = []
    output_names: List[str] = summary.get("_outputs", [])
    for k, v in summary.items():
        if k == "_outputs":
            continue
        if k.startswith("warning_"):
            # warnings は "warning=..." 形式で書き出す
            lines.append(f"warning={v}")
            continue
        lines.append(f"{k}={v}")
    if output_names:
        lines.append("")
        lines.append("outputs:")
        for name in output_names:
            lines.append(f"  {name}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def read_csv_dedup_first_row_from_bytes(
    data: bytes,
    delimiter: str,
    header: bool,
    key_col: Optional[str],
    key_index_1based: Optional[int],
) -> Tuple[Optional[List[str]], Dict[str, Any], int, int, str]:
    """ab_match の read_csv_dedup_first_row のメモリ版。
    戻り値:
      fieldnames: header=True のとき列名リスト、header=False のとき None
      rows_by_key: key -> row（dict か list）
      total_rows: 入力データ行数（header 行は含めない）
      dup_rows: 重複として弾かれた行数（2回目以降）
      key_mode: "column:<name>" / "index:<n>" / "row"
    """
    total_rows = 0
    dup_rows = 0
    rows_by_key: Dict[str, Any] = {}

    text = decode_utf8_sig(data)

    if header:
        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError("header指定やのにヘッダが見つからへん")

        use_row_key = False
        key_col_use: Optional[str] = None

        if len(fieldnames) == 1:
            key_col_use = key_col or fieldnames[0]
            key_mode = f"column:{key_col_use}"
        else:
            if key_col:
                if key_col not in fieldnames:
                    raise ValueError(f"列 '{key_col}' が無い。列={fieldnames}")
                key_col_use = key_col
                key_mode = f"column:{key_col_use}"
            else:
                use_row_key = True
                key_mode = "row"

        for row in reader:
            total_rows += 1
            if use_row_key:
                k = make_row_key_from_dict(row, delimiter)
            else:
                k = norm_key(row.get(key_col_use))  # type: ignore[arg-type]

            if not k:
                continue
            if k in rows_by_key:
                dup_rows += 1
                continue
            rows_by_key[k] = row

        return list(fieldnames), rows_by_key, total_rows, dup_rows, key_mode

    # header=False
    reader = csv.reader(StringIO(text), delimiter=delimiter)
    first = next(reader, None)
    if first is None:
        return None, {}, 0, 0, "row"

    col_count = len(first)
    use_row_key = False
    key_idx0: Optional[int] = None

    if key_index_1based is None:
        if col_count == 1:
            key_idx0 = 0
            key_mode = "index:1"
        else:
            use_row_key = True
            key_mode = "row"
    else:
        if key_index_1based < 1 or key_index_1based > col_count:
            raise ValueError(
                f"--key-index-* が範囲外（指定={key_index_1based}, 列数={col_count}）"
            )
        key_idx0 = key_index_1based - 1
        key_mode = f"index:{key_index_1based}"

    def rows():
        yield first
        for r in reader:
            yield r

    for r in rows():
        total_rows += 1
        if use_row_key:
            k = make_row_key_from_list(r, delimiter)
        else:
            v = r[key_idx0] if key_idx0 is not None and key_idx0 < len(r) else ""
            k = norm_key(v)

        if not k:
            continue
        if k in rows_by_key:
            dup_rows += 1
            continue
        rows_by_key[k] = r

    return None, rows_by_key, total_rows, dup_rows, key_mode
