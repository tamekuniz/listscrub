# listscrub Web 化 — 要件 (フォN id=20260504-1526-z5r4)

Step 0 でズンジーと握った内容の正本。後続 Step（小人ちゃんへの委任、Step 8 検証依頼）はこの文書を参照する。

## Goal

1. listscrub の 4 ツール（`ab_match` / `dedup_csv` / `filter_lines` / `reorder_columns`）を Web ブラウザから使えるようにする。
2. 自宅サーバ mmini4（32GB Mac mini M4）に prd / dev 両環境をデプロイし、`316006.com/listscrub/` と `dev.316006.com/listscrub/` で配信する。
3. 将来のワークフロー機能（複数ツールを連鎖、中間結果を持ち回って「重複除去 → 突合 → 特定レコード削除」のようなパイプラインを組む）に拡張可能な React コンポーネント設計を Phase 1 から仕込む。

## Constraints

1. **サーバーにファイルを残さない**: 完全インメモリ処理。`tempfile` も `logfile` も使わない。リクエスト処理はメモリ上のみで完結し、リクエスト終了で GC により痕跡ゼロ。アクセスログにファイル名・キー列名等の個人情報を含めない。
2. **スタック**: Next.js（フロント）+ FastAPI（バック、既存 `00_Program/` の Python ロジックを流用）。Caddy で path 振り分け（`/listscrub/api/*` → FastAPI、`/listscrub/*` → Next.js）。
3. **認証**: 当面は Caddy `basic_auth` ディレクティブで保護（既存 `jonji` ユーザー、bcrypt ハッシュ流用）。将来 Uniikey（CIAM）に移行する前提のため、**アプリ層（Next.js / FastAPI）に認証関心を一切持ち込まない**。ユーザー識別子もセッションも使わない。Uniikey 移行時は Caddy 設定差し替えのみでアプリ無修正。
4. **インフラ**: 既存 `~/server/compose.yaml` + `~/server/caddy/Caddyfile` の freeder / hbextra パターンに完全準拠。
   - Cloudflare Tunnel が TLS 終端、Caddy は :80 HTTP only、`auto_https off`
   - prd/dev コンテナを別 service として並列稼働（`listscrub-front` / `listscrub-front-dev`、`listscrub-api` / `listscrub-api-dev`）
   - リポジトリは `~/server/repos/listscrub-prd` / `~/server/repos/listscrub-dev` のサブディレクトリにビルドコンテキストとして配置
5. **データ規模**: 150 万件 × 30 万件の `ab_match` 突合が処理可能であること。実効ピークメモリ 2〜3GB 想定（32GB あるので余裕、ストリーム処理で複雑化しない、雑にメモリロード OK）。
6. **MVP スコープ**: 単発 4 ツール独立画面のみ。ワークフロー UI は Phase 2。ただし設計レベルで Phase 2 移行が容易なよう、各ツールを `<ToolStep input={Blob|null} onResult={(Blob) => void}>` 互換シグネチャの React コンポーネントとして組む。
7. **既存資産**: `00_Program/` の 5 ファイル（`ab_match.py` 310 行 / `dedup_csv.py` 235 行 / `reorder_columns.py` 146 行 / `common.py` 77 行 / `filter_lines.py` 62 行、合計 830 行）を FastAPI 側で `import` して再利用する。CLI argparse 部分は薄いラッパー化が必要だがロジック本体は無修正で動かす。

## Acceptance criteria

1. `316006.com/listscrub/` と `dev.316006.com/listscrub/` に Caddy `basic_auth` 越しでアクセスでき、ログイン後に 4 ツール（ab_match / dedup_csv / filter_lines / reorder_columns）の画面に遷移して、それぞれファイルアップロード → 処理 → 結果ダウンロードが動作する。
2. 150 万件と 30 万件のサンプル CSV（メールアドレスを含むリスト想定）で `ab_match` を実行し、処理完了 → `in_both`, `only_a`, `only_b` の 3 ファイル（または ZIP）がブラウザに DL される。タイムアウトせず完走する。
3. `ab_match` 実行直後に mmini4 上で以下を確認し、listscrub 由来の痕跡が **残っていない**:
   - `/tmp` 以下に listscrub 関連のファイルなし
   - Docker コンテナ内 `/tmp` も同様
   - Caddy / Docker / FastAPI のログにファイル名やキー列の個人情報が記録されていない（アクセスログは URL のみ）
4. `cd ~/server && docker compose up -d` で `listscrub-front` `listscrub-front-dev` `listscrub-api` `listscrub-api-dev` の 4 コンテナが起動し、`caddy reload` で `316006.com/listscrub/` `dev.316006.com/listscrub/` への routing が反映される。
5. 各ツール画面の React コンポーネントが `<ToolStep input={Blob|null} onResult={(Blob) => void}>` 互換シグネチャを持つ（Phase 2 のワークフロー UI から `input` を流し込んで連鎖可能、`input=null` 時は単発画面としてファイル選択 UI を出す）。
