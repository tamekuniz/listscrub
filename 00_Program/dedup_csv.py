#!/usr/bin/env python3
"""CSV/TSV または行ベーステキストの重複排除"""
import argparse
import csv
from pathlib import Path
from typing import List

from common import (
    jst_timestamp,
    norm_key,
    resolve_delimiter,
    delimiter_label,
    resolve_input_file,
    setup_output_dir,
    copy_input_files,
)


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

    # --- positional args ---
    file_arg = args.args[0]
    positional_key = args.args[1] if len(args.args) >= 2 else None

    # positional key implies --header yes and --key
    if positional_key is not None:
        args.header = "yes"
        args.key = positional_key

    # --- resolve input / output ---
    src = resolve_input_file(file_arg)
    out_dir = setup_output_dir("dedup_csv")
    ts = jst_timestamp()

    kept_blank_key_rows = 0
    total_data_rows = 0
    dropped_duplicates = 0
    unique_keys = 0

    # ========== LINE MODE ==========
    if args.line:
        seen = set()
        kept_lines: List[str] = []
        dropped_lines: List[str] = []

        with src.open("r", encoding="utf-8-sig", newline="") as f:
            for raw in f:
                line = raw.rstrip("\r\n")
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

        out_kept = out_dir / f"00_dedup_{src.stem}_{kept_count}.txt"
        out_dropped = out_dir / f"01_dedup_dropped_{src.stem}_{dropped_count}.txt"
        summary = out_dir / "summary.txt"

        out_kept.write_text("\n".join(kept_lines) + ("\n" if kept_lines else ""), encoding="utf-8")
        out_dropped.write_text("\n".join(dropped_lines) + ("\n" if dropped_lines else ""), encoding="utf-8")

        summary_text = "\n".join([
            f"time(JST)={ts}",
            f"source={src.name}",
            "mode=line",
            "key=line",
            f"total_data_rows={total_data_rows}",
            f"unique_keys={unique_keys}",
            f"kept_rows={kept_count}",
            f"dropped_duplicates={dropped_duplicates}",
            f"kept_blank_key_rows={kept_blank_key_rows}",
            "",
            "outputs:",
            f"  {out_kept}",
            f"  {out_dropped}",
            f"  {summary}",
        ]) + "\n"

        summary.write_text(summary_text, encoding="utf-8")
        copy_input_files(out_dir, src)
        print(summary_text, end="")
        return

    # ========== CSV MODE ==========
    delim = resolve_delimiter(args.delimiter, src)
    delim_lbl = delimiter_label(delim)

    header = (args.header == "yes")
    seen = set()

    kept_rows = []
    dropped_rows = []
    fieldnames = None
    key_desc = ""

    with src.open("r", encoding="utf-8-sig", newline="") as f:
        if header:
            reader = csv.DictReader(f, delimiter=delim)
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise SystemExit("[ERROR] header=yes やのにヘッダが見つからへん")

            if len(fieldnames) == 1 and not args.key:
                key_col = fieldnames[0]
            else:
                if not args.key or args.key not in fieldnames:
                    raise SystemExit(f"[ERROR] --key が不正。列={fieldnames}")
                key_col = args.key

            key_desc = key_col

            for row in reader:
                total_data_rows += 1
                k = norm_key(row.get(key_col))
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
            reader = csv.reader(f, delimiter=delim)
            first = next(reader, None)
            if first is None:
                raise SystemExit("[ERROR] 空ファイルや")

            col_count = len(first)
            if col_count == 1 and args.key_index is None:
                key_idx0 = 0
            else:
                if args.key_index is None:
                    raise SystemExit(f"[ERROR] 複数列（{col_count}列）なので --key-index が必要や")
                if args.key_index < 1 or args.key_index > col_count:
                    raise SystemExit(f"[ERROR] --key-index 範囲不正（指定={args.key_index}, 列数={col_count}）")
                key_idx0 = args.key_index - 1

            key_desc = "index={}".format(key_idx0 + 1)

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

    out_kept = out_dir / f"00_dedup_{src.stem}_{kept_count}.csv"
    out_dropped = out_dir / f"01_dedup_dropped_{src.stem}_{dropped_count}.csv"
    summary = out_dir / "summary.txt"

    if header:
        with out_kept.open("w", encoding="utf-8", newline="") as fo:
            w = csv.DictWriter(fo, fieldnames=fieldnames, delimiter=delim)
            w.writeheader()
            w.writerows(kept_rows)
        with out_dropped.open("w", encoding="utf-8", newline="") as fo:
            w = csv.DictWriter(fo, fieldnames=fieldnames, delimiter=delim)
            w.writeheader()
            w.writerows(dropped_rows)
    else:
        with out_kept.open("w", encoding="utf-8", newline="") as fo:
            w = csv.writer(fo, delimiter=delim)
            w.writerows(kept_rows)
        with out_dropped.open("w", encoding="utf-8", newline="") as fo:
            w = csv.writer(fo, delimiter=delim)
            w.writerows(dropped_rows)

    summary_text = "\n".join([
        f"time(JST)={ts}",
        f"source={src.name}",
        "mode=csv",
        f"header={header}",
        f"delimiter={delim_lbl}",
        f"key={key_desc}",
        f"total_data_rows={total_data_rows}",
        f"unique_keys={unique_keys}",
        f"kept_rows={kept_count}",
        f"dropped_duplicates={dropped_duplicates}",
        f"kept_blank_key_rows={kept_blank_key_rows}",
        "",
        "outputs:",
        f"  {out_kept}",
        f"  {out_dropped}",
        f"  {summary}",
    ]) + "\n"

    summary.write_text(summary_text, encoding="utf-8")
    copy_input_files(out_dir, src)
    print(summary_text, end="")


if __name__ == "__main__":
    main()
