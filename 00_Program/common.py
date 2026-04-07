#!/usr/bin/env python3
"""BENRI ツール共通ユーティリティ"""
import csv
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List


def jst_timestamp() -> str:
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y-%m-%d_%H-%M-%S")


def sanitize_stem(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^\w\.\-\+]+", "", name)
    name = name.strip("._-")
    return name or "file"


def sniff_delimiter(path: Path) -> str:
    sample = path.read_bytes()[:8192].decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=["\t", ",", ";"])
        return dialect.delimiter
    except Exception:
        return ","


def norm_key(s: Optional[str]) -> str:
    if s is None:
        return ""
    return s.strip().strip('"').strip("'").lower()


def resolve_delimiter(arg_value: str, path: Path) -> str:
    if arg_value == "auto":
        return sniff_delimiter(path)
    return {"tab": "\t", "comma": ",", "semicolon": ";"}[arg_value]


def delimiter_label(delim: str) -> str:
    return "TAB" if delim == "\t" else delim


def base_dir() -> Path:
    return Path(__file__).parent.parent


def resolve_input_file(arg: str) -> Path:
    """ファイルパスを解決する。
    - フルパス or 相対パスが存在すればそのまま使う
    - なければ IN/ フォルダから探す（従来互換）
    """
    p = Path(arg)
    if p.exists():
        return p.resolve()
    in_path = base_dir() / "IN" / arg
    if in_path.exists():
        return in_path.resolve()
    raise SystemExit(f"[ERROR] ファイルが見つからへん: {arg}\n  IN/ にも無い: {in_path}")


def setup_output_dir(prog_name: str) -> Path:
    ts = jst_timestamp()
    out_dir = base_dir() / "OUT" / f"{ts}_{prog_name}"
    out_dir.mkdir(parents=True, exist_ok=False)
    return out_dir


def copy_input_files(out_dir: Path, *paths: Path) -> None:
    input_dir = out_dir / "input"
    input_dir.mkdir(exist_ok=True)
    for p in paths:
        shutil.copy2(p, input_dir / p.name)
