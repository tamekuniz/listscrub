"""行フィルタ — メモリベース純粋関数版

指定文字列を含む行と含まない行に分離する。重複除去なし。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .common import (
    decode_utf8_sig,
    jst_timestamp,
    summary_dict_to_bytes,
    write_lines_to_bytes,
)


def filter_lines(
    src_bytes: bytes,
    exclude: str,
    *,
    src_stem: str = "input",
    src_name: str = "",
) -> Tuple[Dict[str, bytes], Dict[str, Any]]:
    """src_bytes の各行を `exclude` を含む/含まないで分離する。

    戻り値:
      files: {ファイル名: bytes} 出力ファイル群（kept / excluded / summary）
      summary: 集計値の dict
    """
    text = decode_utf8_sig(src_bytes)
    kept: List[str] = []
    excluded: List[str] = []
    total_rows = 0

    for line in text.splitlines():
        total_rows += 1
        if exclude in line:
            excluded.append(line)
        else:
            kept.append(line)

    kept_count = len(kept)
    excluded_count = len(excluded)

    out_kept_name = f"00_kept_{src_stem}_{kept_count}.txt"
    out_excluded_name = f"01_excluded_{src_stem}_{excluded_count}.txt"
    summary_name = "summary.txt"

    files: Dict[str, bytes] = {
        out_kept_name: write_lines_to_bytes(kept),
        out_excluded_name: write_lines_to_bytes(excluded),
    }

    summary: Dict[str, Any] = {
        "time(JST)": jst_timestamp(),
        "source": src_name or src_stem,
        "mode": "line_filter",
        "exclude_string": exclude,
        "total_rows": total_rows,
        "kept_rows": kept_count,
        "excluded_rows": excluded_count,
        "_outputs": [out_kept_name, out_excluded_name, summary_name],
    }

    files[summary_name] = summary_dict_to_bytes(summary)
    return files, summary
