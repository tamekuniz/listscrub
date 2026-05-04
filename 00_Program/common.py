"""listscrub CLI 用共通ユーティリティ

メモリベース純粋関数（jst_timestamp, sanitize_stem, norm_key, delimiter_label 等）は
core/common.py を正本とし、ここでは re-export して CLI から直接 import できるようにする。

このモジュール本体が持つのは「ファイル/ディレクトリを扱う I/O 系関数」のみ。
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict

from core.common import (
    delimiter_label,
    jst_timestamp,
    norm_key,
    resolve_delimiter_for_bytes,
    sanitize_stem,
    sniff_delimiter_from_bytes,
)


def sniff_delimiter(path: Path) -> str:
    return sniff_delimiter_from_bytes(path.read_bytes())


def resolve_delimiter(arg_value: str, path: Path) -> str:
    if arg_value == "auto":
        return sniff_delimiter(path)
    return {"tab": "\t", "comma": ",", "semicolon": ";"}[arg_value]


def base_dir() -> Path:
    return Path(__file__).parent.parent


def resolve_input_file(arg: str) -> Path:
    """ファイルパスを解決する（フルパス or 相対パス → 無ければ IN/ 配下を探す）。"""
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


def write_outputs_and_summary(
    out_dir: Path, files: Dict[str, bytes], summary: Dict[str, Any]
) -> None:
    """core 関数の戻り値（files dict, summary dict）を OUT/ に書き出し、
    summary.txt をフルパス版に整形して上書きする。

    4 つの CLI ラッパー（ab_match / dedup_csv / filter_lines / reorder_columns）から共用。
    """
    paths: Dict[str, Path] = {}
    for name, content in files.items():
        if name == "summary.txt":
            continue
        p = out_dir / name
        p.write_bytes(content)
        paths[name] = p

    summary_path = out_dir / "summary.txt"
    lines = []
    for k, v in summary.items():
        if k == "_outputs":
            continue
        if k.startswith("warning_"):
            lines.append(f"warning={v}")
            continue
        lines.append(f"{k}={v}")
    lines.append("")
    lines.append("outputs:")
    for name in summary["_outputs"]:
        if name == "summary.txt":
            lines.append(f"  {summary_path}")
        else:
            lines.append(f"  {paths[name]}")
    text = "\n".join(lines) + "\n"
    summary_path.write_text(text, encoding="utf-8")
    print(text, end="")
