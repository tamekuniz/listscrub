# listscrub Web 化 — todo (フォN id=20260504-1526-z5r4)

investigation.md を入力に作成。各タスクは bite-sized 詳細を含む。

---

- [ ] **T1: 既存 Python のコア分離リファクタ + CLI 互換維持**

  - **対象ファイル**:
    - `00_Program/core/__init__.py`（新規）
    - `00_Program/core/common.py`（新規、純粋関数だけ抽出）
    - `00_Program/core/ab_match.py`（新規）
    - `00_Program/core/dedup.py`（新規）
    - `00_Program/core/filter_lines.py`（新規）
    - `00_Program/core/reorder.py`（新規）
    - `00_Program/ab_match.py`（既存改修、`main()` を core 呼び出し版に書き換え）
    - `00_Program/dedup_csv.py`（同上）
    - `00_Program/filter_lines.py`（同上）
    - `00_Program/reorder_columns.py`（同上）
    - `00_Program/common.py`（既存、`resolve_input_file/setup_output_dir/copy_input_files` 等は CLI 用として維持）
  - **編集対象**:
    - 新規: 各 `core/<tool>.py` に `def <tool>(a_bytes: bytes, ...) -> tuple[dict[str, bytes], dict]` 関数を実装。引数は CLI の `--header` `--key` `--key-index` `--delimiter` 等と互換。戻り値は `({"ファイル名": bytes}, summary_dict)`
    - 新規: `core/common.py` に `norm_key`, `sniff_delimiter`, `sanitize_stem`, `delimiter_label`, `make_row_key_*`, `read_csv_dedup_first_row`（メモリ版）を移植
    - 改修: 各 CLI スクリプトの `main()` を「argparse → ファイル読み bytes 化 → core 関数呼び出し → 戻り値の dict[name,bytes] を `out_dir/` に書き出し」の流れに変える
  - **期待挙動**:
    - リファクタ前後で `python3 00_Program/<tool>.py <既存サンプル引数>` を実行し、`OUT/` 内の生成ファイルが **完全に同じ**（diff 0）
    - core 関数を Python REPL から `from core.ab_match import ab_match; result, summary = ab_match(open("a.csv","rb").read(), open("b.csv","rb").read())` で呼べる
  - **検証コマンド**:
    ```bash
    # サンプルデータ準備（小規模）
    cd /Users/tamekuniz/GitHub/tamekuniz/listscrub
    mkdir -p IN_test
    printf "email\nfoo@a.com\nbar@a.com\nbaz@a.com\n" > IN_test/a.csv
    printf "email\nbar@a.com\nbaz@a.com\nqux@a.com\n" > IN_test/b.csv

    # リファクタ前にベースライン取得（git stash で元に戻して実行）
    # OR: 各 tool で「ヘッダあり/キー指定/単純実行」の組み合わせを 4-5 パターン用意

    # リファクタ後の実行と diff 確認
    python3 00_Program/ab_match.py IN_test/a.csv email IN_test/b.csv email
    python3 00_Program/dedup_csv.py IN_test/a.csv email
    python3 00_Program/filter_lines.py IN_test/a.csv "@a.com"
    python3 00_Program/reorder_columns.py IN_test/a.csv IN_test/b.csv

    # core 関数の動作確認
    python3 -c "
    import sys; sys.path.insert(0, '00_Program')
    from core.ab_match import ab_match
    a = open('IN_test/a.csv','rb').read()
    b = open('IN_test/b.csv','rb').read()
    files, summary = ab_match(a, b, key_a='email', key_b='email')
    print(list(files.keys()), summary)
    "

    # pytest がある程度書けたら
    pytest 00_Program/tests/ -v
    ```
  - **備考**:
    - core 関数は **ファイル IO を一切しない**（Path も os も使わない）
    - 戻り値の dict のキーは `in_both_<n>.csv` `only_a_<stem>_<n>.csv` 等、既存ファイル名規約と一致させる（CLI 側でその名前のままディスクに書く）
    - キー正規化は既存 `norm_key` をそのまま使う（lower + strip + 引用符除去）
    - `summary` は dict で返し、CLI 側で `summary.txt` のテキストに整形
    - pytest は `00_Program/tests/test_core_*.py` に書く（推奨だが必須ではない、最低限手動 diff で OK）

---

- [ ] **T2: FastAPI バックエンドの実装**

  - **対象ファイル**:
    - `api/main.py`（新規）
    - `api/requirements.txt`（新規）
    - `api/Dockerfile`（新規）
    - `api/__init__.py`（必要なら）
  - **編集対象**:
    - `api/main.py`: FastAPI app 1 つ、4 endpoints (`POST /ab_match`, `POST /dedup`, `POST /filter_lines`, `POST /reorder_columns`)
    - 各 endpoint は `Request.body()` 又は `Request.stream()` でバイトを受け、`00_Program.core.<tool>` を呼び、生成された `dict[name, bytes]` を **ZIP に詰めて** `StreamingResponse` で返す
    - `UploadFile` は使わない（`SpooledTemporaryFile` でディスクに書くのを避けるため）
    - 代わりに `python-multipart` の low-level API か、あるいは fastapi の `Form` + `File(spool_max_size=10**12)` で **メモリ上限を実質無制限**にする
    - アクセスログは `--access-log` を **無効化** する起動オプション
  - **期待挙動**:
    - `curl -X POST -F "file_a=@a.csv" -F "file_b=@b.csv" -F "key_a=email" -F "key_b=email" http://localhost:8000/ab_match -o result.zip` で ZIP が返る
    - ZIP を unzip すると `in_both_*.csv` `only_a_*.csv` `only_b_*.csv` `summary.txt` が含まれる
    - 処理後 `/tmp` に新規ファイルなし（テスト中に `os.listdir('/tmp')` を before/after 比較）
  - **検証コマンド**:
    ```bash
    # ローカル起動
    cd /Users/tamekuniz/GitHub/tamekuniz/listscrub
    python3 -m venv api/.venv && source api/.venv/bin/activate
    pip install -r api/requirements.txt

    # PYTHONPATH に 00_Program/ を含めて起動
    PYTHONPATH=00_Program uvicorn api.main:app --host 0.0.0.0 --port 8000 --no-access-log

    # 別ターミナルで疎通確認
    curl -v -X POST \
      -F "file_a=@IN_test/a.csv" \
      -F "file_b=@IN_test/b.csv" \
      -F "key_a=email" -F "key_b=email" \
      http://localhost:8000/ab_match -o /tmp/result.zip
    unzip -l /tmp/result.zip

    # 痕跡確認
    ls /tmp/ | grep -i listscrub  # 何も出ないこと

    # Docker ビルド
    docker build -f api/Dockerfile -t listscrub-api:test .
    docker run --rm -p 8000:8000 listscrub-api:test
    ```
  - **備考**:
    - `requirements.txt` は `fastapi`, `uvicorn[standard]`, `python-multipart` の 3 つ（バージョンピン推奨）
    - Dockerfile のビルドコンテキストは **リポルート**（`00_Program/` を `COPY` するため、`api/` 配下では足りない）
    - `Dockerfile` 内で `WORKDIR /app`、`COPY 00_Program /app/00_Program`、`COPY api /app/api`、`ENV PYTHONPATH=/app/00_Program`
    - 起動コマンド: `uvicorn api.main:app --host 0.0.0.0 --port 8000 --no-access-log --timeout-keep-alive 600`
    - エラーレスポンスのボディに **入力ファイル名や列名を含めない**（個人情報漏洩対策、汎用エラーメッセージのみ）

---

- [ ] **T3: Next.js 雛形 + 共通コンポーネント・API クライアント**

  - **対象ファイル**:
    - `web/package.json`（新規、freeder を参考）
    - `web/next.config.ts`（新規、basePath 環境変数化）
    - `web/tsconfig.json`（新規）
    - `web/postcss.config.mjs`（新規、Tailwind）
    - `web/Dockerfile`（新規、freeder のコピー）
    - `web/.dockerignore`（新規）
    - `web/.gitignore`（新規）
    - `web/src/app/layout.tsx`（新規）
    - `web/src/app/page.tsx`（新規、4 ツールへのリンク一覧）
    - `web/src/app/globals.css`（新規、Tailwind 読み込み）
    - `web/src/components/ToolStep.tsx`（新規、共通インターフェース型）
    - `web/src/components/FilePicker.tsx`（新規、ドラッグ&ドロップ対応のファイル入力）
    - `web/src/components/DownloadButton.tsx`（新規、Blob を `<a download>` で DL）
    - `web/src/lib/api.ts`（新規、`/listscrub/api/*` を呼ぶクライアント関数）
  - **編集対象**:
    - `next.config.ts`: freeder と同じ `basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? ""`
    - `Dockerfile`: freeder の Dockerfile をベースに `ARG NEXT_PUBLIC_BASE_PATH=/listscrub`
    - `package.json`: 依存は最小限（next, react, react-dom, tailwindcss, @tailwindcss/postcss, typescript, eslint, eslint-config-next）。**freeder の DB/auth 系（better-sqlite3, iron-session, rss-parser）は不要**
    - `lib/api.ts`: `const API_BASE = (process.env.NEXT_PUBLIC_BASE_PATH ?? "") + "/api"`、`async function callTool(tool: 'ab_match'|'dedup'|..., formData: FormData): Promise<Blob>` を実装
    - `components/ToolStep.tsx`: TypeScript の型 `interface ToolStepProps { input: Blob | null; onResult: (result: Blob) => void; }` を定義（実装は子で）
    - `app/page.tsx`: 4 ツールへの Next.js `<Link>` を並べただけのトップ
  - **期待挙動**:
    - `npm run dev` で `http://localhost:3000/listscrub/` にアクセスすると 4 ツールへのリンクが表示
    - basePath が反映され、css/js の asset URL も `/listscrub/...` で配信
    - `Tailwind` クラスが効く
  - **検証コマンド**:
    ```bash
    cd /Users/tamekuniz/GitHub/tamekuniz/listscrub/web
    npm install
    NEXT_PUBLIC_BASE_PATH=/listscrub npm run dev
    # ブラウザで http://localhost:3000/listscrub/ にアクセス
    # DevTools で asset URL に /listscrub/_next/... が含まれること

    # Docker ビルド確認
    docker build -f web/Dockerfile -t listscrub-front:test --build-arg NEXT_PUBLIC_BASE_PATH=/listscrub web/
    docker run --rm -p 3000:3000 listscrub-front:test
    ```
  - **備考**:
    - 認証コードは一切入れない（middleware.ts も作らない）
    - 現状 `iron-session` 等は不要（Caddy basic_auth で完結）
    - ESLint config は freeder のをそのままコピーで OK
    - Tailwind は v4 を使用（freeder と揃える）
    - フロントの状態管理は React の `useState` で十分（ワークフロー Phase 2 で必要なら Zustand 等に移行）

---

- [ ] **T4: 4 ツール画面の実装（共通コンポーネント `<XxxStep>` + page.tsx）**

  - **対象ファイル**:
    - `web/src/app/ab-match/page.tsx`（新規）
    - `web/src/app/dedup/page.tsx`（新規）
    - `web/src/app/filter-lines/page.tsx`（新規）
    - `web/src/app/reorder/page.tsx`（新規）
    - `web/src/components/AbMatchStep.tsx`（新規）
    - `web/src/components/DedupStep.tsx`（新規）
    - `web/src/components/FilterLinesStep.tsx`（新規）
    - `web/src/components/ReorderStep.tsx`（新規）
  - **編集対象**:
    - 各 `<XxxStep>` コンポーネント: `interface XxxStepProps extends ToolStepProps {}` を実装。`input={Blob|null}` が `null` のときは `<FilePicker>` を表示、`Blob` が渡されればその Blob を入力として使う（Phase 2 のワークフロー連鎖で再利用可能）
    - 各 `<XxxStep>` 内で必要な追加入力（キー列名、デリミタ等）の UI を持つ
    - 処理ボタン押下で `lib/api.ts` の `callTool` を呼び、戻り値 `Blob` を `onResult` で親に渡す
    - 各 `app/<tool>/page.tsx`: `<XxxStep input={null} onResult={(result) => downloadBlob(result, '<tool>_result.zip')}>` で wrap
  - **期待挙動**:
    - `http://localhost:3000/listscrub/ab-match/` にアクセス → ファイル A/B 選択 + キー列入力 → 「実行」→ 処理中スピナー → 完了後に DL ボタン押下で ZIP 取得
    - 4 ツール全部が同じパターンで動く
    - 各コンポーネントが props 経由で input Blob を受けても動作する（Phase 2 互換性、TypeScript 型でチェック）
  - **検証コマンド**:
    ```bash
    cd /Users/tamekuniz/GitHub/tamekuniz/listscrub/web
    NEXT_PUBLIC_BASE_PATH=/listscrub npm run dev

    # 各画面で小サンプル動作確認
    # http://localhost:3000/listscrub/ab-match/  - 100 行の a.csv b.csv で動作
    # http://localhost:3000/listscrub/dedup/      - 100 行の a.csv で動作
    # http://localhost:3000/listscrub/filter-lines/
    # http://localhost:3000/listscrub/reorder/

    # 別ターミナルで FastAPI 起動
    PYTHONPATH=00_Program uvicorn api.main:app --port 8000 --no-access-log

    # 上記の dev で fetch URL は /listscrub/api/... になるが、開発時は dev server が prefix なし
    # → next.config.ts に rewrites を入れるか、もしくは npm run dev 時は API_BASE をローカル :8000 に向ける環境変数で切り替える
    # 推奨: web/.env.local に NEXT_PUBLIC_API_BASE_OVERRIDE=http://localhost:8000 を入れて dev だけ直接 :8000 へ
    ```
  - **備考**:
    - dev 時の API 接続は CORS 問題が出るので、`NEXT_PUBLIC_API_BASE_OVERRIDE` 環境変数で切り替え可能にしておく
    - 進捗 UI: 大ファイル（150 万件）のアップロードは `XMLHttpRequest` の `progress` イベントを使うか、シンプルに「処理中…」表示で済ませる（MVP では後者で十分）
    - 結果が複数ファイルあるツール（ab_match）は ZIP で返すので、フロントは単一 Blob として扱う
    - エラー表示は汎用メッセージ（個人情報漏洩防止）

---

- [ ] **T5: 自宅サーバ統合（compose.yaml + Caddyfile + repos clone）**

  - **対象ファイル**:
    - `~/server/compose.yaml`（既存改修）
    - `~/server/caddy/Caddyfile`（既存改修）
    - `~/server/repos/listscrub-prd/`（新規 clone）
    - `~/server/repos/listscrub-dev/`（新規 clone）
  - **編集対象**:
    - `compose.yaml`: 4 services 追加（`listscrub-front`, `listscrub-front-dev`, `listscrub-api`, `listscrub-api-dev`）。既存 freeder/hbextra と同じパターンで `restart: always` `expose` `build.context` `build.args` `container_name`
    - `compose.yaml` の `caddy.depends_on` に新 4 services を追加
    - `Caddyfile`:
      - `host_prod` 内の `@protected_prod path` に `/listscrub /listscrub/*` を追加
      - `host_prod` 内に `@listscrub_api_prod path /listscrub/api/*` + `handle_path /listscrub/api/* { reverse_proxy listscrub-api:8000 }` を追加（path 順序: api を先に書く）
      - `host_prod` 内に `@listscrub_prod path /listscrub /listscrub/*` + `handle @listscrub_prod { reverse_proxy listscrub-front:3000 }` を追加
      - `host_dev` も同パターンで `-dev` 付き service 向けに追加
    - `~/server/repos/listscrub-prd` を `git clone https://github.com/tamekuniz/listscrub.git ~/server/repos/listscrub-prd`、dev も同様
  - **期待挙動**:
    - `docker compose up -d --build listscrub-front listscrub-front-dev listscrub-api listscrub-api-dev` で 4 コンテナ起動
    - `docker exec caddy caddy reload --config /etc/caddy/Caddyfile` で Caddyfile 反映
    - `docker compose ps` で全コンテナ healthy
  - **検証コマンド**:
    ```bash
    cd ~/server

    # repos clone
    git clone https://github.com/tamekuniz/listscrub.git repos/listscrub-prd
    git clone https://github.com/tamekuniz/listscrub.git repos/listscrub-dev

    # Caddyfile 構文チェック
    docker exec caddy caddy validate --config /etc/caddy/Caddyfile

    # ビルド + 起動
    docker compose up -d --build listscrub-front listscrub-front-dev listscrub-api listscrub-api-dev

    # Caddy reload
    docker exec caddy caddy reload --config /etc/caddy/Caddyfile

    # コンテナ起動確認
    docker compose ps | grep listscrub

    # ローカルから疎通確認（basic_auth 込み）
    curl -u jonji:<password> -I http://localhost/listscrub/
    curl -u jonji:<password> http://localhost/listscrub/api/  # 404 でもいい、200 系応答が来れば疎通 OK
    ```
  - **備考**:
    - **Caddyfile の path 順序が重要**: `/listscrub/api/*` を `/listscrub/*` より先に書く（マッチが先勝ち）
    - 既存 jonji の bcrypt ハッシュは流用、新規 user は作らない
    - `~/server/repos/listscrub-prd` で `git pull` したら `docker compose build listscrub-front listscrub-api && caddy reload` でデプロイ
    - prd と dev は別 clone なので、dev でブランチを切り替えれば prd 影響なくテスト可能

---

- [ ] **T6: 実機検証（150 万件突合 + ファイル痕跡確認 + prd/dev 両方）**

  - **対象ファイル**: 検証のみ、コード変更なし
  - **編集対象**: なし
  - **期待挙動**:
    - `https://dev.316006.com/listscrub/` を Cloudflare Tunnel 経由で開く → basic_auth プロンプト → 4 ツール画面表示
    - 150 万件 × 30 万件のサンプル CSV で `ab_match` を実行 → 数十秒〜数分で完走 → ZIP DL
    - mmini4 の `/tmp` および `docker exec listscrub-api ls /tmp/` で痕跡なし
    - Caddy / Docker ログにファイル名・列名・キー値が **記録されていない**
    - `https://316006.com/listscrub/` (prd) でも同等の動作
  - **検証コマンド**:
    ```bash
    # 大規模サンプル準備（mmini4 上で実施）
    # 既存の業務サンプルを使う or python で疑似生成
    python3 -c "
    import random
    with open('/tmp/big_a.csv', 'w') as f:
        f.write('email,name\n')
        for i in range(1500000):
            f.write(f'user{i}@a.com,name{i}\n')
    with open('/tmp/big_b.csv', 'w') as f:
        f.write('email,name\n')
        for i in range(300000):
            f.write(f'user{i*5}@a.com,name{i*5}\n')
    "

    # ブラウザで dev.316006.com/listscrub/ab-match/ にアクセスし、上記 2 ファイルをアップロード
    # キー列: email、ヘッダ: あり、デリミタ: auto

    # 処理中、別ターミナルで監視
    docker stats listscrub-api  # CPU/MEM 確認
    watch 'docker exec listscrub-api ls -la /tmp/'

    # 完了後、痕跡確認
    docker exec listscrub-api ls /tmp/
    ls /tmp/ | grep -i 'big_a\|big_b\|listscrub' || echo "no traces"

    # ログにファイル名が無いこと
    docker logs listscrub-api 2>&1 | grep -E 'big_a|big_b' || echo "no leak in api log"
    docker logs caddy 2>&1 | tail -50 | grep -E 'big_a|big_b' || echo "no leak in caddy log"

    # prd でも同様
    # ブラウザで 316006.com/listscrub/ab-match/ → 同 2 ファイル → 結果取得
    ```
  - **備考**:
    - Cloudflare Tunnel 設定変更が必要なら Step 7 reflection 経由で対応
    - もし OOM や timeout が発生したら reflection で Pattern Analysis（hbextra 等の運用との比較）→ 修正
    - 痕跡が見つかったら `UploadFile` の経路を再確認（reflection 経由）
    - 検証完了後、サンプル CSV `/tmp/big_a.csv` `/tmp/big_b.csv` を **手動で削除**（mmini4 内）
