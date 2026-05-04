#!/usr/bin/env python3
"""CSV/TSV または行ベーステキストの重複排除（CLI ラッパー）

ロジック本体は core/dedup.py にある。
"""
from __future__ import annotations

import argparse

from common import (
    copy_input_files,
    resolve_input_file,
    setup_output_dir,
    write_outputs_and_summary,
)
from core.dedup import dedup


def main():
    ap = argparse.ArgumentParser(
        description="Deduplicate CSV/TSV or line-based text and export kept/dropped",
    )
    ap.add_argument("args", nargs="+", help="file [keyColumn]")
    ap.add_argument("--line", action="store_true", help="改行区切りリストとして扱う")
    ap.add_argument("--header", choices=["yes", "no"], default="no", help="ヘッダ有無（default=no）")
    ap.add_argument("--key", help="（header=yes）キー列名")
    ap.add_argument("--key-index", type=int, help="（header=no）キー列番号（1始まり）")
    ap.add_argument("--delimiter", choices=["auto", "tab", "comma", "semicolon"], default="auto")
    args = ap.parse_args()

    file_arg = args.args[0]
    positional_key = args.args[1] if len(args.args) >= 2 else None

    if positional_key is not None:
        args.header = "yes"
        args.key = positional_key

    src = resolve_input_file(file_arg)
    src_bytes = src.read_bytes()

    out_dir = setup_output_dir("dedup_csv")
    copy_input_files(out_dir, src)

    try:
        files, summary = dedup(
            src_bytes,
            line_mode=args.line,
            header=(args.header == "yes"),
            key_col=args.key,
            key_index_1based=args.key_index,
            delimiter=args.delimiter,
            src_stem=src.stem,
            src_name=src.name,
        )
    except ValueError as e:
        raise SystemExit(f"[ERROR] {e}")

    write_outputs_and_summary(out_dir, files, summary)


if __name__ == "__main__":
    main()
