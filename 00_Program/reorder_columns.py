#!/usr/bin/env python3
"""カラム並べ替え CLI ラッパー — ロジックは core/reorder.py"""
from __future__ import annotations

import argparse

from common import (
    copy_input_files,
    resolve_input_file,
    setup_output_dir,
    write_outputs_and_summary,
)
from core.reorder import reorder_columns


def main():
    ap = argparse.ArgumentParser(description="Reorder CSV/TSV columns to match a header template")
    ap.add_argument("data_file", help="データファイル（IN/ 内 or フルパス）")
    ap.add_argument("template_file", help="ヘッダテンプレートファイル（IN/ 内 or フルパス）")
    ap.add_argument("--delimiter-a", choices=["auto", "tab", "comma", "semicolon"], default="auto")
    ap.add_argument("--delimiter-b", choices=["auto", "tab", "comma", "semicolon"], default="auto")
    args = ap.parse_args()

    file_a = resolve_input_file(args.data_file)
    file_b = resolve_input_file(args.template_file)
    a_bytes = file_a.read_bytes()
    b_bytes = file_b.read_bytes()

    out_dir = setup_output_dir("reorder_columns")
    copy_input_files(out_dir, file_a, file_b)

    try:
        files, summary = reorder_columns(
            a_bytes, b_bytes,
            delimiter_a=args.delimiter_a,
            delimiter_b=args.delimiter_b,
            data_stem=file_a.stem,
            template_stem=file_b.stem,
            data_name=file_a.name,
            template_name=file_b.name,
        )
    except ValueError as e:
        raise SystemExit(f"[ERROR] {e}")

    write_outputs_and_summary(out_dir, files, summary)


if __name__ == "__main__":
    main()
