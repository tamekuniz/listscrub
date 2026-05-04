#!/usr/bin/env python3
"""AB Match: 2つのファイルを突合して共通/差分を出力する（CLI ラッパー）

ロジック本体は core/ab_match.py（メモリベース純粋関数）にある。
"""
from __future__ import annotations

import argparse
from typing import List, Optional, Tuple

from common import (
    copy_input_files,
    resolve_input_file,
    setup_output_dir,
    write_outputs_and_summary,
)
from core.ab_match import ab_match


def parse_positional_args(pos_args: List[str]) -> Tuple[str, Optional[str], str, Optional[str]]:
    """位置引数をパースする。

    2個: fileA fileB              (キーなし)
    4個: fileA keyA fileB keyB    (キーあり)
    """
    n = len(pos_args)
    if n == 2:
        return pos_args[0], None, pos_args[1], None
    if n == 4:
        return pos_args[0], pos_args[1], pos_args[2], pos_args[3]
    raise SystemExit(
        "[ERROR] 位置引数は 2個 (fileA fileB) か 4個 (fileA keyA fileB keyB) で指定してな\n"
        f"  受け取った数: {n}  値: {pos_args}"
    )


def main():
    ap = argparse.ArgumentParser(
        description="2つのファイルを突合して共通/差分を出力する",
        usage="%(prog)s fileA [keyA] fileB [keyB] [options]",
    )
    ap.add_argument(
        "args", nargs="*", metavar="ARG",
        help="fileA [keyA] fileB [keyB] — 2個ならキーなし突合、4個ならキー指定突合",
    )
    ap.add_argument("--header-a", choices=["yes", "no"], default="yes",
                     help="Aのヘッダ有無（default=yes）")
    ap.add_argument("--header-b", choices=["yes", "no"], default="yes",
                     help="Bのヘッダ有無（default=yes）")
    ap.add_argument("--key-a", help="A（header=yes）のキー列名（位置引数keyAで上書き可）")
    ap.add_argument("--key-b", help="B（header=yes）のキー列名（位置引数keyBで上書き可）")
    ap.add_argument("--key-index-a", type=int, help="A（header=no）のキー列番号（1始まり）")
    ap.add_argument("--key-index-b", type=int, help="B（header=no）のキー列番号（1始まり）")
    ap.add_argument("--delimiter-a", choices=["auto", "tab", "comma", "semicolon"], default="auto")
    ap.add_argument("--delimiter-b", choices=["auto", "tab", "comma", "semicolon"], default="auto")
    args = ap.parse_args()

    if not args.args:
        ap.print_help()
        raise SystemExit(1)

    file_a_arg, pos_key_a, file_b_arg, pos_key_b = parse_positional_args(args.args)
    key_a = pos_key_a if pos_key_a is not None else args.key_a
    key_b = pos_key_b if pos_key_b is not None else args.key_b

    file_a = resolve_input_file(file_a_arg)
    file_b = resolve_input_file(file_b_arg)
    a_bytes = file_a.read_bytes()
    b_bytes = file_b.read_bytes()

    out_dir = setup_output_dir("ab_match")
    copy_input_files(out_dir, file_a, file_b)

    try:
        files, summary = ab_match(
            a_bytes, b_bytes,
            header_a=(args.header_a == "yes"),
            header_b=(args.header_b == "yes"),
            key_a=key_a, key_b=key_b,
            key_index_a=args.key_index_a, key_index_b=args.key_index_b,
            delimiter_a=args.delimiter_a, delimiter_b=args.delimiter_b,
            a_stem=file_a.stem, b_stem=file_b.stem,
            a_name=file_a.name, b_name=file_b.name,
        )
    except ValueError as e:
        raise SystemExit(f"[ERROR] {e}")

    write_outputs_and_summary(out_dir, files, summary)


if __name__ == "__main__":
    main()
