#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any


def jst_timestamp() -> str:
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y-%m-%d_%H-%M-%S")


def sanitize_stem(name: str) -> str:
    name = name.strip()
    name = name.replace(" ", "_")
    name = re.sub(r"[^\w\.\-\+]+", "", name)  # 英数/_/./-/+ 以外を落とす
    name = name.strip("._-")
    return name or "file"


def sniff_delimiter(path: Path) -> str:
    sample = path.read_bytes()[:8192].decode("utf-8-sig", errors="replace")
    candidates = ["\t", ",", ";"]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=candidates)
        return dialect.delimiter
    except Exception:
        return ","


def norm_key(s: Optional[str]) -> str:
    if s is None:
        return ""
    return s.strip().strip('"').strip("'").lower()


def make_row_key_from_dict(row: Dict[str, Any], delimiter: str) -> str:
    # DictReader の row は dict。順序は fieldnames の順で作られる前提で values() を使う。
    vals = []
    for v in row.values():
        if v is None:
            vals.append("")
        else:
            vals.append(str(v).strip())
    return norm_key(delimiter.join(vals))


def make_row_key_from_list(row: List[Any], delimiter: str) -> str:
    vals = []
    for v in row:
        if v is None:
            vals.append("")
        else:
            vals.append(str(v).strip())
    return norm_key(delimiter.join(vals))


def read_csv_dedup_first_row(
    path: Path,
    delimiter: str,
    header: bool,
    key_col: Optional[str],
    key_index_1based: Optional[int],
) -> Tuple[Optional[List[str]], Dict[str, Any], int, int, str]:
    """
    戻り値:
      fieldnames: header=True のとき列名リスト、header=False のとき None
      rows_by_key: key -> row（dict か list）
      total_rows: 入力データ行数（header行は含めない）
      dup_rows: 重複として弾かれた行数（2回目以降）
      key_mode: "column:<name>" / "index:<n>" / "row"
    """
    total_rows = 0
    dup_rows = 0
    rows_by_key: Dict[str, Any] = {}

    if header:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise ValueError(f"{path.name}: header指定やのにヘッダが見つからへん")

            # キー指定あり（ただし 1列なら省略可）
            use_row_key = False
            key_col_use: Optional[str] = None

            if len(fieldnames) == 1:
                # 1列ファイルはキー指定なくてもその列で突合できる
                key_col_use = key_col or fieldnames[0]
                key_mode = "column:{}".format(key_col_use)
            else:
                if key_col:
                    if key_col not in fieldnames:
                        raise ValueError(f"{path.name}: 列 '{key_col}' が無い。列={fieldnames}")
                    key_col_use = key_col
                    key_mode = "column:{}".format(key_col_use)
                else:
                    # ★ キー指定なし → 行全体で突合
                    use_row_key = True
                    key_mode = "row"

            for row in reader:
                total_rows += 1
                if use_row_key:
                    k = make_row_key_from_dict(row, delimiter)
                else:
                    k = norm_key(row.get(key_col_use))  # type: ignore[arg-type]

                if not k:
                    # 空キーは突合キーとして扱えへんのでスキップ
                    continue
                if k in rows_by_key:
                    dup_rows += 1
                    continue
                rows_by_key[k] = row

            return fieldnames, rows_by_key, total_rows, dup_rows, key_mode

    # header=False
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        first = next(reader, None)
        if first is None:
            return None, {}, 0, 0, "row"

        col_count = len(first)

        # キー指定なし → 行全体
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
                raise ValueError(f"{path.name}: --key-index-* が範囲外（指定={key_index_1based}, 列数={col_count}）")
            key_idx0 = key_index_1based - 1
            key_mode = "index:{}".format(key_index_1based)

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


def write_dict_rows(path: Path, delimiter: str, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_list_rows(path: Path, delimiter: str, rows: List[List[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=delimiter)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description="Match File A and File B and output intersection/differences")
    ap.add_argument("--a", required=True, help="INフォルダ内のファイルA")
    ap.add_argument("--b", required=True, help="INフォルダ内のファイルB")

    ap.add_argument("--header-a", choices=["yes", "no"], default="yes", help="Aのヘッダ有無（default=yes）")
    ap.add_argument("--header-b", choices=["yes", "no"], default="yes", help="Bのヘッダ有無（default=yes）")

    ap.add_argument("--key-a", help="A（header=yes）のキー列名（省略時は1列ならその列、複数列なら行全体）")
    ap.add_argument("--key-b", help="B（header=yes）のキー列名（省略時は1列ならその列、複数列なら行全体）")

    ap.add_argument("--key-index-a", type=int, help="A（header=no）のキー列番号（省略時は1列なら1、複数列なら行全体）")
    ap.add_argument("--key-index-b", type=int, help="B（header=no）のキー列番号（省略時は1列なら1、複数列なら行全体）")

    ap.add_argument("--delimiter-a", choices=["auto", "tab", "comma", "semicolon"], default="auto")
    ap.add_argument("--delimiter-b", choices=["auto", "tab", "comma", "semicolon"], default="auto")
    args = ap.parse_args()

    prog_name = "ab_match"
    base_dir = Path(__file__).parent
    in_dir = base_dir / "IN"
    out_root = base_dir / "OUT"

    file_a = in_dir / args.a
    file_b = in_dir / args.b
    if not file_a.exists():
        raise SystemExit(f"[ERROR] not found: {file_a}")
    if not file_b.exists():
        raise SystemExit(f"[ERROR] not found: {file_b}")

    if args.delimiter_a == "auto":
        delim_a = sniff_delimiter(file_a)
    elif args.delimiter_a == "tab":
        delim_a = "\t"
    elif args.delimiter_a == "comma":
        delim_a = ","
    else:
        delim_a = ";"

    if args.delimiter_b == "auto":
        delim_b = sniff_delimiter(file_b)
    elif args.delimiter_b == "tab":
        delim_b = "\t"
    elif args.delimiter_b == "comma":
        delim_b = ","
    else:
        delim_b = ";"

    ts = jst_timestamp()
    out_dir = out_root / f"{ts}_{prog_name}"
    out_dir.mkdir(parents=True, exist_ok=False)

    header_a = (args.header_a == "yes")
    header_b = (args.header_b == "yes")

    try:
        a_fields, a_map, a_total, a_dups, a_key_mode = read_csv_dedup_first_row(
            file_a, delim_a, header_a, args.key_a, args.key_index_a
        )
        b_fields, b_map, b_total, b_dups, b_key_mode = read_csv_dedup_first_row(
            file_b, delim_b, header_b, args.key_b, args.key_index_b
        )
    except ValueError as e:
        raise SystemExit(f"[ERROR] {e}")

    keys_a = set(a_map.keys())
    keys_b = set(b_map.keys())

    in_both_keys = sorted(keys_a & keys_b)
    only_a_keys = sorted(keys_a - keys_b)
    only_b_keys = sorted(keys_b - keys_a)

    a_stem = sanitize_stem(Path(args.a).stem)
    b_stem = sanitize_stem(Path(args.b).stem)

    out_in_both = out_dir / f"in_both_{len(in_both_keys)}.csv"
    out_only_a = out_dir / f"only_a_{a_stem}_{len(only_a_keys)}.csv"
    out_only_b = out_dir / f"only_b_{b_stem}_{len(only_b_keys)}.csv"
    summary = out_dir / "summary.txt"

    # in_both / only_a は A側の行を出す
    if header_a:
        assert a_fields is not None
        in_both_rows_a = [a_map[k] for k in in_both_keys]
        only_a_rows = [a_map[k] for k in only_a_keys]
        write_dict_rows(out_in_both, delim_a, a_fields, in_both_rows_a)  # type: ignore[arg-type]
        write_dict_rows(out_only_a, delim_a, a_fields, only_a_rows)      # type: ignore[arg-type]
    else:
        in_both_rows_a = [a_map[k] for k in in_both_keys]
        only_a_rows = [a_map[k] for k in only_a_keys]
        write_list_rows(out_in_both, delim_a, in_both_rows_a)  # type: ignore[arg-type]
        write_list_rows(out_only_a, delim_a, only_a_rows)      # type: ignore[arg-type]

    # only_b は B側の行を出す
    if header_b:
        assert b_fields is not None
        only_b_rows = [b_map[k] for k in only_b_keys]
        write_dict_rows(out_only_b, delim_b, b_fields, only_b_rows)  # type: ignore[arg-type]
    else:
        only_b_rows = [b_map[k] for k in only_b_keys]
        write_list_rows(out_only_b, delim_b, only_b_rows)  # type: ignore[arg-type]

    delim_a_label = "TAB" if delim_a == "\t" else delim_a
    delim_b_label = "TAB" if delim_b == "\t" else delim_b

    summary_text = "\n".join([
        f"time(JST)={ts}",
        f"file_A={file_a.name}",
        f"file_B={file_b.name}",
        f"header_A={header_a}",
        f"header_B={header_b}",
        f"delimiter_A={delim_a_label}",
        f"delimiter_B={delim_b_label}",
        f"key_A_mode={a_key_mode}",
        f"key_B_mode={b_key_mode}",
        f"A_total_rows={a_total}",
        f"B_total_rows={b_total}",
        f"A_unique_keys={len(keys_a)} (dup_dropped={a_dups})",
        f"B_unique_keys={len(keys_b)} (dup_dropped={b_dups})",
        f"in_both(A∩B)={len(in_both_keys)}",
        f"only_a(A\\B)={len(only_a_keys)}",
        f"only_b(B\\A)={len(only_b_keys)}",
        "",
        "outputs:",
        f"  {out_in_both}",
        f"  {out_only_a}",
        f"  {out_only_b}",
        f"  {summary}",
    ]) + "\n"

    summary.write_text(summary_text, encoding="utf-8")
    print(summary_text, end="")


if __name__ == "__main__":
    main()