# listscrub Web 化 — progress (フォN id=20260504-1526-z5r4)

各タスクの進捗状況。フォN サイクルで Step 6/7/8 と reflection 中に追記される。

---

## T1: 既存 Python のコア分離リファクタ + CLI 互換維持

状態: 完了（loop_count=1）

### 実装内容

- `00_Program/core/` 新設: `__init__.py`, `common.py`, `ab_match.py`, `dedup.py`, `filter_lines.py`, `reorder.py`
- 純粋関数として bytes/str ベースの API を実装、ファイル IO 一切なし
- `00_Program/{ab_match,dedup_csv,filter_lines,reorder_columns}.py` を core 呼び出し版にリファクタ
- `00_Program/common.py` を core からの re-export + 共通 I/O 関数 `write_outputs_and_summary` に整理

### Reflection 0 で対応した simplify 指摘（5 項目中 4 つ修正、1 つは設計上不要）

researcher 調査レポート: `investigation-r0.md` 相当の内容を本 progress.md §「Reflection 0」に集約済み（hook 制約により investigation-r0.md は未生成）

**1. Root Cause Investigation（失敗要因）**

「テスト失敗」ではなく「simplify レビューによる指摘 5 項目」起因。Step 7 のテスト全パス後の品質レビューで以下 5 点が指摘された:

- 指摘 1: CLI ラッパー 4 ファイル（ab_match.py / dedup_csv.py / filter_lines.py / reorder_columns.py）に `_write_outputs_and_summary` 関数が完全コピペで重複
- 指摘 2: core/common.py と 00_Program/common.py に `jst_timestamp` / `sanitize_stem` / `norm_key` / `delimiter_label` が重複定義
- 指摘 3: CLI ラッパーで FileNotFoundError catch なし → 既に SystemExit 設計（修正不要を確認）
- 指摘 4: core/dedup.py の CSV モード `"source": src_stem` だが LINE モードは `src_name or src_stem`、不一致
- 指摘 5: core/common.py の `reader_from_bytes` / `dict_reader_from_bytes` は誰も使ってない死コード

根本原因: コア分離リファクタを「最小工数で動かす」優先で書いたため、CLI 側の write/summary 処理を 4 ファイルにコピペしたまま、また core/common.py に「呼ばれない予定の」ヘルパを置いてしまった。

**2. Pattern Analysis（動作リファレンスとの差異）**

- f146117 「Restructure into 00_Program/ with positional args, shared utils, and input file copying」コミットで共通 util を common.py に集約済み。同パターンを延長すべき
- freeder/src/lib/ も utility 集約パターン
- 前ループとの差分: 今回が initial 実装（loop_count=0、retry 履歴なし）

**3. Hypothesis（単一仮説）**

`_write_outputs_and_summary` を 00_Program/common.py に集約 + 重複関数を core/common.py からの re-export に統一 + CSV モードの src_name 対応 + 死コード削除、の 4 修正で simplify 全指摘に対応できる。CLI 互換性は既存サンプル `IN_test/` での diff チェックで担保。efficiency 系（bytes/str 二重持ち、list 化等）は T1 スコープ外、T2 (FastAPI 実装) で再評価。

**4. Implementation 計画（単一修正）**

順序固定で実施:
1. 死コード削除（最低 risk）: core/common.py から `reader_from_bytes` と `dict_reader_from_bytes` 削除
2. 重複関数の re-export 化: 00_Program/common.py の冒頭に `from core.common import jst_timestamp, sanitize_stem, norm_key, delimiter_label, sniff_delimiter_from_bytes, resolve_delimiter_for_bytes` 追加、自身の重複定義削除
3. `write_outputs_and_summary` を 00_Program/common.py に追加
4. 4 CLI ラッパーから `_write_outputs_and_summary` 削除、`from common import write_outputs_and_summary` に切り替え
5. core/dedup.py CSV モード `"source": src_name or src_stem` に統一

### 検証結果（loop_count=1 の testing phase）

- `IN_test/{a.csv, b.csv, dups.csv}` で 4 ツール全実行
- リファクタ前の `OUT_before/` と `bash` 経由で diff チェック
- AB MATCH / DEDUP (line) / DEDUP (csv) / FILTER LINES / REORDER の全出力ファイルが **完全 identical**（タイムスタンプとパスを除く）
- summary.txt の "source" フィールド値が `src_stem` → `src_name` に改善（CSV モードのみ、LINE モードと整合する軽微改善）

### simplify 再起動の判断

修正後に simplify を再起動するか検討したが、対応した 4 項目はいずれも明確な指摘で、対応漏れがないことは目視と再テストで確認済み。残り 1 項目（FileNotFoundError catch）は既存 SystemExit 設計のため対応不要。これ以上の simplify 起動は重箱の隅に当たるため省略し、verified に進めた。

---

## T2-T6: 次フォNサイクルで実装

T1 で前提（コア分離 + CLI 互換維持）が整ったので、以下は本サイクル完了後の **次フォNサイクル** で実施する:

- T2: FastAPI バックエンドの実装（`api/main.py`, `requirements.txt`, `Dockerfile`、core を import して 4 endpoint 提供、完全インメモリ処理）
- T3: Next.js 雛形 + 共通コンポーネント・API クライアント
- T4: 4 ツール画面の実装（`<XxxStep>` コンポーネント + `app/<tool>/page.tsx`）
- T5: 自宅サーバ統合（`~/server/compose.yaml` + `~/server/caddy/Caddyfile` + `~/server/repos/listscrub-{prd,dev}/` clone）
- T6: 実機検証（150 万件突合 + ファイル痕跡確認 + prd/dev 両方）

サイクル分割の理由:
- T1 単体で commit 価値がある（コア分離はそれ自体で完結）
- T2-T6 は規模が大きく、別サイクルで設計詳細を詰める方が安全
- 1 サイクル = 1 タスクの方針で粒度を保つ
