# listscrub

メール配信リストの加工に使うPythonスクリプト集です。
A collection of Python scripts for processing email distribution lists.

---

## フォルダ構成 / Folder Structure

```
listscrub/
├── 00_Program/          # スクリプト本体 / Scripts
│   ├── common.py        # 共通ユーティリティ / Shared utilities
│   ├── ab_match.py      # 2ファイル突合 / A-B Matching
│   ├── dedup_csv.py     # 重複除去 / Deduplication
│   ├── filter_lines.py  # 行フィルタ / Line Filter
│   └── reorder_columns.py # カラム並べ替え / Column Reorder
├── IN/                  # 入力ファイルをここに置く / Place input files here
└── OUT/                 # 出力先（実行時に自動生成）/ Output (auto-created on run)
```

各スクリプトは `IN/` フォルダから入力を読み込み、`OUT/タイムスタンプ_ツール名/` に結果を出力します。
結果フォルダには `input/` サブフォルダに元ファイルのコピーも含まれます。
Each script reads from `IN/` and writes to `OUT/<timestamp>_<tool>/`, including a copy of the original input files.

---

## ツール一覧 / Tools

### `ab_match.py` — 2ファイル突合 / A-B Matching

2つのCSV/TSVを比較して、共通行・差分行をそれぞれ出力します。
Compares two CSV/TSV files and outputs intersection and differences.

```bash
# 基本（行全体で突合）
python3 00_Program/ab_match.py IN/list_a.csv IN/list_b.csv

# キー列を指定して突合
python3 00_Program/ab_match.py IN/list_a.csv email IN/list_b.csv メールアドレス
```

出力 / Output:
- `in_both_N.csv` — A∩B（両方に存在 / Present in both）
- `only_a_NAME_N.csv` — A\B（Aだけに存在 / Only in A）
- `only_b_NAME_N.csv` — B\A（Bだけに存在 / Only in B）

オプション / Options:
| オプション | 説明 |
|---|---|
| `--header-a`, `--header-b` | ヘッダ有無 `yes`/`no`（default: yes） |
| `--key-index-a`, `--key-index-b` | キー列番号（header=no 時、1始まり） |
| `--delimiter-a`, `--delimiter-b` | 区切り文字 `auto`/`tab`/`comma`/`semicolon` |

---

### `dedup_csv.py` — 重複除去 / Deduplication

CSV/TSVまたはテキストファイルから重複行を除去します。
Removes duplicate rows from CSV/TSV or plain text files.

```bash
# テキストモード（改行区切り）
python3 00_Program/dedup_csv.py IN/list.txt --line

# CSVモード（キー列指定）
python3 00_Program/dedup_csv.py IN/list.csv メールアドレス

# CSVモード（キーなし）
python3 00_Program/dedup_csv.py IN/list.csv
```

出力 / Output:
- `00_dedup_NAME_N.csv` — ユニーク行 / Unique rows
- `01_dedup_dropped_NAME_N.csv` — 重複として除去した行 / Dropped duplicates

オプション / Options:
| オプション | 説明 |
|---|---|
| `--line` | 改行区切りテキストとして処理（`.txt`向け） |
| `--header` | ヘッダ有無 `yes`/`no`（default: no） |
| `--key-index` | キー列番号（header=no 時、1始まり） |
| `--delimiter` | 区切り文字 `auto`/`tab`/`comma`/`semicolon` |

---

### `filter_lines.py` — 行フィルタ / Line Filter

指定文字列を含む行と含まない行に分離します（重複除去なし）。
Splits lines into those containing a specified string and those that don't (no dedup).

```bash
python3 00_Program/filter_lines.py IN/list.txt "@example.com"
```

出力 / Output:
- `00_kept_NAME_N.txt` — 除外文字列を含まない行 / Lines not containing the string
- `01_excluded_NAME_N.txt` — 除外文字列を含む行 / Lines containing the string

---

### `reorder_columns.py` — カラム並べ替え / Column Reorder

CSVのカラム順をテンプレートに合わせて並べ替えます。
Reorders CSV columns to match a header template.

```bash
python3 00_Program/reorder_columns.py IN/data.csv IN/template.csv
```

出力 / Output:
- `reordered_NAME_N.csv` — カラム並べ替え済みデータ / Data with reordered columns

オプション / Options:
| オプション | 説明 |
|---|---|
| `--delimiter-a` | データファイルの区切り文字 `auto`/`tab`/`comma`/`semicolon` |
| `--delimiter-b` | テンプレートファイルの区切り文字 `auto`/`tab`/`comma`/`semicolon` |

---

## 要件 / Requirements

Python 3.8以上 / Python 3.8+（標準ライブラリのみ / standard library only）

---

## ライセンス / License

MIT
