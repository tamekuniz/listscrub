"""A/B 突合 — メモリベース純粋関数版

2 つのファイルを突合して共通行 (A∩B)、A のみ (A\\B)、B のみ (B\\A) を出力する。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .common import (
    delimiter_label,
    jst_timestamp,
    read_csv_dedup_first_row_from_bytes,
    resolve_delimiter_for_bytes,
    sanitize_stem,
    summary_dict_to_bytes,
    write_dict_rows_to_bytes,
    write_list_rows_to_bytes,
)


def ab_match(
    a_bytes: bytes,
    b_bytes: bytes,
    *,
    header_a: bool = True,
    header_b: bool = True,
    key_a: Optional[str] = None,
    key_b: Optional[str] = None,
    key_index_a: Optional[int] = None,
    key_index_b: Optional[int] = None,
    delimiter_a: str = "auto",
    delimiter_b: str = "auto",
    a_stem: str = "a",
    b_stem: str = "b",
    a_name: str = "",
    b_name: str = "",
) -> Tuple[Dict[str, bytes], Dict[str, Any]]:
    """A/B 突合のコア。

    戻り値:
      files: {ファイル名: bytes} 出力ファイル群（in_both, only_a, only_b, summary）
      summary: 集計値の dict
    """
    delim_a = resolve_delimiter_for_bytes(delimiter_a, a_bytes)
    delim_b = resolve_delimiter_for_bytes(delimiter_b, b_bytes)

    a_fields, a_map, a_total, a_dups, a_key_mode = read_csv_dedup_first_row_from_bytes(
        a_bytes, delim_a, header_a, key_a, key_index_a
    )
    b_fields, b_map, b_total, b_dups, b_key_mode = read_csv_dedup_first_row_from_bytes(
        b_bytes, delim_b, header_b, key_b, key_index_b
    )

    keys_a = set(a_map.keys())
    keys_b = set(b_map.keys())

    in_both_keys = sorted(keys_a & keys_b)
    only_a_keys = sorted(keys_a - keys_b)
    only_b_keys = sorted(keys_b - keys_a)

    a_stem_safe = sanitize_stem(a_stem)
    b_stem_safe = sanitize_stem(b_stem)

    out_in_both_name = f"in_both_{len(in_both_keys)}.csv"
    out_only_a_name = f"only_a_{a_stem_safe}_{len(only_a_keys)}.csv"
    out_only_b_name = f"only_b_{b_stem_safe}_{len(only_b_keys)}.csv"
    summary_name = "summary.txt"

    files: Dict[str, bytes] = {}

    # in_both / only_a は A 側の行を出す
    if header_a:
        assert a_fields is not None
        in_both_rows = [a_map[k] for k in in_both_keys]
        only_a_rows = [a_map[k] for k in only_a_keys]
        files[out_in_both_name] = write_dict_rows_to_bytes(a_fields, in_both_rows, delim_a)
        files[out_only_a_name] = write_dict_rows_to_bytes(a_fields, only_a_rows, delim_a)
    else:
        in_both_rows = [a_map[k] for k in in_both_keys]
        only_a_rows = [a_map[k] for k in only_a_keys]
        files[out_in_both_name] = write_list_rows_to_bytes(in_both_rows, delim_a)
        files[out_only_a_name] = write_list_rows_to_bytes(only_a_rows, delim_a)

    # only_b は B 側の行を出す
    if header_b:
        assert b_fields is not None
        only_b_rows = [b_map[k] for k in only_b_keys]
        files[out_only_b_name] = write_dict_rows_to_bytes(b_fields, only_b_rows, delim_b)
    else:
        only_b_rows = [b_map[k] for k in only_b_keys]
        files[out_only_b_name] = write_list_rows_to_bytes(only_b_rows, delim_b)

    summary: Dict[str, Any] = {
        "time(JST)": jst_timestamp(),
        "file_A": a_name or a_stem,
        "file_B": b_name or b_stem,
        "header_A": header_a,
        "header_B": header_b,
        "delimiter_A": delimiter_label(delim_a),
        "delimiter_B": delimiter_label(delim_b),
        "key_A_mode": a_key_mode,
        "key_B_mode": b_key_mode,
        "A_total_rows": a_total,
        "B_total_rows": b_total,
        "A_unique_keys": f"{len(keys_a)} (dup_dropped={a_dups})",
        "B_unique_keys": f"{len(keys_b)} (dup_dropped={b_dups})",
        "in_both(A∩B)": len(in_both_keys),
        "only_a(A\\B)": len(only_a_keys),
        "only_b(B\\A)": len(only_b_keys),
        "_outputs": [out_in_both_name, out_only_a_name, out_only_b_name, summary_name],
    }
    files[summary_name] = summary_dict_to_bytes(summary)
    return files, summary
