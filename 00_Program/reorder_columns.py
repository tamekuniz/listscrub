#!/usr/bin/env python3
import argparse
import csv
from typing import List, Tuple

from common import (
    jst_timestamp,
    sanitize_stem,
    norm_key,
    resolve_delimiter,
    delimiter_label,
    resolve_input_file,
    setup_output_dir,
    copy_input_files,
)


def main():
    ap = argparse.ArgumentParser(description="Reorder CSV/TSV columns to match a header template")
    ap.add_argument("data_file", help="データファイル（IN/ 内 or フルパス）")
    ap.add_argument("template_file", help="ヘッダテンプレートファイル（IN/ 内 or フルパス）")
    ap.add_argument("--delimiter-a", choices=["auto", "tab", "comma", "semicolon"], default="auto")
    ap.add_argument("--delimiter-b", choices=["auto", "tab", "comma", "semicolon"], default="auto")
    args = ap.parse_args()

    file_a = resolve_input_file(args.data_file)
    file_b = resolve_input_file(args.template_file)

    delim_a = resolve_delimiter(args.delimiter_a, file_a)
    delim_b = resolve_delimiter(args.delimiter_b, file_b)

    out_dir = setup_output_dir("reorder_columns")
    ts = out_dir.name.split("_reorder_columns")[0]

    with file_b.open("r", encoding="utf-8-sig", newline="") as fb:
        reader_b = csv.reader(fb, delimiter=delim_b)
        header_b = next(reader_b, None)
    if header_b is None or len(header_b) == 0:
        raise SystemExit(f"[ERROR] template file has no header: {file_b}")

    with file_a.open("r", encoding="utf-8-sig", newline="") as fa:
        reader_a = csv.DictReader(fa, delimiter=delim_a)
        header_a = reader_a.fieldnames
        if not header_a:
            raise SystemExit(f"[ERROR] data file has no header: {file_a}")
        rows_a: List[dict] = list(reader_a)

    norm_to_a: dict = {}
    norm_dup_a: List[str] = []
    for col in header_a:
        nk = norm_key(col)
        if nk in norm_to_a:
            norm_dup_a.append(col)
        else:
            norm_to_a[nk] = col

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

    extra_columns: List[str] = []
    for col in header_a:
        nk = norm_key(col)
        if nk not in matched_a_norms:
            extra_columns.append(col)

    out_header: List[str] = []
    for tcol, _acol in matched_columns:
        out_header.append(tcol)
    for tcol in missing_columns:
        out_header.append(tcol)
    for acol in extra_columns:
        out_header.append(acol)

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

    a_stem = sanitize_stem(file_a.stem)
    out_reordered = out_dir / f"reordered_{a_stem}_{data_row_count}.csv"
    summary_path = out_dir / "summary.txt"

    with out_reordered.open("w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=delim_a)
        w.writerow(out_header)
        w.writerows(out_rows)

    delim_a_lbl = delimiter_label(delim_a)
    delim_b_lbl = delimiter_label(delim_b)

    warnings: List[str] = []
    if norm_dup_a:
        warnings.append(f"duplicate_norm_key_in_A (data dropped): {','.join(norm_dup_a)}")
    if missing_columns:
        warnings.append(f"missing_in_A (added as empty): {missing_columns}")
    if extra_columns:
        warnings.append(f"extra_in_A (appended at end): {extra_columns}")

    lines = [
        f"time(JST)={ts}",
        f"file_A={file_a.name}",
        f"file_B={file_b.name}",
        f"delimiter_A={delim_a_lbl}",
        f"delimiter_B={delim_b_lbl}",
        f"columns_in_A={len(header_a)}",
        f"columns_in_B={len(header_b)}",
        f"matched_columns={len(matched_columns)}",
        f"missing_in_A={len(missing_columns)}",
        f"extra_in_A={len(extra_columns)}",
        f"data_rows={data_row_count}",
    ]
    for w_msg in warnings:
        lines.append(f"warning={w_msg}")
    lines.append("")
    lines.append("outputs:")
    lines.append(f"  {out_reordered}")
    lines.append(f"  {summary_path}")

    summary_text = "\n".join(lines) + "\n"
    summary_path.write_text(summary_text, encoding="utf-8")
    print(summary_text, end="")

    copy_input_files(out_dir, file_a, file_b)


if __name__ == "__main__":
    main()
