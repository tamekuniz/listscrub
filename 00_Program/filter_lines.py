#!/usr/bin/env python3
import argparse

from common import jst_timestamp, resolve_input_file, setup_output_dir, copy_input_files


def main():
    ap = argparse.ArgumentParser(description="Split lines by exclude string (no dedup)")
    ap.add_argument("file", help="対象ファイル（IN/ 内 or フルパス）")
    ap.add_argument("exclude", help="この文字列を含む行を excluded に分離")
    args = ap.parse_args()

    src = resolve_input_file(args.file)
    out_dir = setup_output_dir("filter_lines")
    ts = out_dir.name.split("_filter_lines")[0]

    kept = []
    excluded = []
    total_rows = 0

    with src.open("r", encoding="utf-8-sig", newline="") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            total_rows += 1
            if args.exclude in line:
                excluded.append(line)
            else:
                kept.append(line)

    kept_count = len(kept)
    excluded_count = len(excluded)

    out_kept = out_dir / f"00_kept_{src.stem}_{kept_count}.txt"
    out_excluded = out_dir / f"01_excluded_{src.stem}_{excluded_count}.txt"
    summary = out_dir / "summary.txt"

    out_kept.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    out_excluded.write_text("\n".join(excluded) + ("\n" if excluded else ""), encoding="utf-8")

    summary_text = "\n".join([
        f"time(JST)={ts}",
        f"source={src.name}",
        "mode=line_filter",
        f"exclude_string={args.exclude}",
        f"total_rows={total_rows}",
        f"kept_rows={kept_count}",
        f"excluded_rows={excluded_count}",
        "",
        "outputs:",
        f"  {out_kept}",
        f"  {out_excluded}",
        f"  {summary}",
    ]) + "\n"

    summary.write_text(summary_text, encoding="utf-8")
    print(summary_text, end="")

    copy_input_files(out_dir, src)


if __name__ == "__main__":
    main()
