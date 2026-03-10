# listscrub

メール配信リストの加工に使うPythonスクリプト集です。
A collection of Python scripts for processing email distribution lists.

---

## ツール一覧 / Tools

### `ab_match.py` — 2ファイル突合 / A-B Matching

2つのCSV/TSVを比較して、共通行・差分行をそれぞれ出力します。
Compares two CSV/TSV files and outputs intersection and differences.

```
python ab_match.py --a list_a.csv --b list_b.csv
```

出力 / Output:
- `in_both_N.csv` — A∩B（両方に存在 / Present in both）
- `only_a_NAME_N.csv` — A\B（Aだけに存在 / Only in A）
- `only_b_NAME_N.csv` — B\A（Bだけに存在 / Only in B）

主なオプション / Options:
| オプション | 説明 |
|---|---|
| `--header-a`, `--header-b` | ヘッダ有無 `yes`/`no`（default: yes） |
| `--key-a`, `--key-b` | キー列名（header=yes 時） |
| `--key-index-a`, `--key-index-b` | キー列番号（header=no 時、1始まり） |
| `--delimiter-a`, `--delimiter-b` | 区切り文字 `auto`/`tab`/`comma`/`semicolon` |

---

### `dedup_csv.py` — 重複除去 / Deduplication

CSV/TSVまたはテキストファイルから重複行を除去します。
Removes duplicate rows from CSV/TSV or plain text files.

```
python dedup_csv.py --file list.csv
python dedup_csv.py --file list.txt --line
```

出力 / Output:
- `00_dedup_NAME_N.csv` — ユニーク行 / Unique rows
- `01_dedup_dropped_NAME_N.csv` — 重複として除去した行 / Dropped duplicates

主なオプション / Options:
| オプション | 説明 |
|---|---|
| `--line` | 改行区切りテキストとして処理（`.txt`向け） |
| `--header` | ヘッダ有無 `yes`/`no`（default: no） |
| `--key` | キー列名（header=yes 時） |
| `--key-index` | キー列番号（header=no 時、1始まり） |
| `--delimiter` | 区切り文字 `auto`/`tab`/`comma`/`semicolon` |

---

### `filter_lines.py` — 行フィルタ / Line Filter

指定文字列を含む行と含まない行に分離します（重複除去なし）。
Splits lines into those containing a specified string and those that don't (no dedup).

```
python filter_lines.py --file list.txt --exclude "@example.com"
```

出力 / Output:
- `00_kept_NAME_N.txt` — 除外文字列を含まない行 / Lines not containing the string
- `01_excluded_NAME_N.txt` — 除外文字列を含む行 / Lines containing the string

---

## フォルダ構成 / Folder Structure

```
listscrub/
├── IN/              # 入力ファイルをここに置く / Place input files here
├── OUT/             # 出力先（実行時に自動生成）/ Output (auto-created on run)
├── ab_match.py
├── dedup_csv.py
└── filter_lines.py
```

各スクリプトは `IN/` フォルダから入力を読み込み、`OUT/タイムスタンプ_ツール名/` に結果を出力します。
Each script reads from the `IN/` folder and writes results to `OUT/<timestamp>_<tool>/`.

---

## 要件 / Requirements

Python 3.8以上 / Python 3.8+（標準ライブラリのみ / standard library only）

---

## ライセンス / License

MIT
