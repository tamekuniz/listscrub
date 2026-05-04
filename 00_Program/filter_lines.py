#!/usr/bin/env python3
"""行フィルタ CLI ラッパー — ロジックは core/filter_lines.py"""
from __future__ import annotations

import argparse

from common import (
    copy_input_files,
    resolve_input_file,
    setup_output_dir,
    write_outputs_and_summary,
)
from core.filter_lines import filter_lines


def main():
    ap = argparse.ArgumentParser(description="Split lines by exclude string (no dedup)")
    ap.add_argument("file", help="対象ファイル（IN/ 内 or フルパス）")
    ap.add_argument("exclude", help="この文字列を含む行を excluded に分離")
    args = ap.parse_args()

    src = resolve_input_file(args.file)
    src_bytes = src.read_bytes()

    out_dir = setup_output_dir("filter_lines")
    copy_input_files(out_dir, src)

    files, summary = filter_lines(
        src_bytes, args.exclude,
        src_stem=src.stem, src_name=src.name,
    )

    write_outputs_and_summary(out_dir, files, summary)


if __name__ == "__main__":
    main()
