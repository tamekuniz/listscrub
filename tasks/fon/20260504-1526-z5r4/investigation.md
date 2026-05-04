# listscrub Web 化 — Step 3 深い調査レポート

フォN id: 20260504-1526-z5r4 / 作成: 2026-05-04 / 調査者: エージェント直接

## 1. 関連ファイル一覧

### 1.1 既存 listscrub（再利用するロジック本体）

| パス | 役割 | 行数 | 備考 |
|---|---|---|---|
| `00_Program/common.py` | 共通ユーティリティ | 77 | `jst_timestamp`, `sanitize_stem`, `sniff_delimiter`, `norm_key`, `resolve_delimiter`, `delimiter_label`, `base_dir`, `resolve_input_file`, `setup_output_dir`, `copy_input_files` |
| `00_Program/ab_match.py` | A/B 突合 CLI | 310 | `make_row_key_from_dict/list`, `read_csv_dedup_first_row`, `write_dict_rows`, `write_list_rows`, `parse_positional_args`, `main` |
| `00_Program/dedup_csv.py` | 重複除去 CLI | 235 | LINE モード（改行区切り）と CSV モード（キー列指定）の 2 系統。`main` のみで関数分割なし |
| `00_Program/filter_lines.py` | 行フィルタ CLI | 62 | 単純な含む/含まないで分離、`main` のみ |
| `00_Program/reorder_columns.py` | カラム並べ替え CLI | 146 | テンプレート CSV のヘッダ順に合わせる、`main` のみで関数分割なし |
| `README.md` | 日英バイリンガルドキュメント | 131 | CLI 使用例とオプション一覧 |

### 1.2 リファレンスプロジェクト（freeder = Next.js 構造）

| パス | 役割 |
|---|---|
| `~/GitHub/tamekuniz/freeder/package.json` | Next.js 16.1.6 + React 19.2.3 + TypeScript 5 + Tailwind 4 |
| `~/GitHub/tamekuniz/freeder/next.config.ts` | `basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? ""` パターン |
| `~/GitHub/tamekuniz/freeder/Dockerfile` | `node:20-alpine` + `npm ci` + `npm run build` + `npm start`、`ARG NEXT_PUBLIC_BASE_PATH=/freeder` |
| `~/GitHub/tamekuniz/freeder/src/app/` | App Router 構造（`api/`, `page.tsx` 48KB, `login/`, `settings/`, `setup/`, `layout.tsx`） |
| `~/GitHub/tamekuniz/freeder/src/components/` | UI コンポーネント |
| `~/GitHub/tamekuniz/freeder/src/lib/` | ユーティリティ（DB アクセス、API クライアント等） |
| `~/GitHub/tamekuniz/freeder/src/middleware.ts` | 認証ミドルウェア（iron-session ベース） |

### 1.3 リファレンスプロジェクト（hbextra = Flask 構造）

| パス | 役割 |
|---|---|
| `~/GitHub/tamekuniz/hbextra/Dockerfile` | `python:3.11-slim` + `pip install -r requirements.txt` + `python hbextra.py` |
| `~/GitHub/tamekuniz/hbextra/requirements.txt` | `flask`, `pykakasi` のみ |
| `~/GitHub/tamekuniz/hbextra/hbextra.py` (40,608 bytes) | Flask app 本体。`DispatcherMiddleware` で `/hbextra` prefix 配信、`/` への直アクセスは `/hbextra/` へ 302 redirect |

### 1.4 インフラ（自宅サーバ）

| パス | 役割 |
|---|---|
| `~/server/compose.yaml` | Docker Compose: caddy + freeder/freeder-dev + hbextra/hbextra-dev + rep2z/rep2z-dev + DB |
| `~/server/caddy/Caddyfile` | host-based routing。`316006.com` (prd) / `dev.316006.com` (dev) を path matcher で振り分け、`basic_auth` で保護 |
| `~/server/repos/freeder-prd/` | freeder の prd 用ビルドコンテキスト（**GitHub から別 clone**、symlink でも submodule でもない） |
| `~/server/repos/freeder-dev/` | freeder の dev 用ビルドコンテキスト（同上、別 clone） |
| `~/server/repos/hbextra-prd/`, `hbextra-dev/` | hbextra も同パターン |
| `~/server/www/` | Caddy が `/srv` にマウントする静的ファイル群（`/` の通常配信用） |

## 2. 既存実装パターン

### 2.1 既存 listscrub CLI のパターン（リファクタ対象）

すべての CLI スクリプトに共通する構造:

1. `argparse` で位置引数 + オプション（`--header`, `--key-index`, `--delimiter` 等）を定義
2. `common.resolve_input_file(arg)` でファイル解決（フルパス or `IN/` 配下を探す）
3. `common.setup_output_dir(prog_name)` で `OUT/<timestamp>_<tool>/` を作成
4. `common.copy_input_files(out_dir, src...)` で入力ファイルを `OUT/.../input/` にコピー
5. ロジック処理（CSV/TSV 読み込み、Set/Dict 操作、出力 CSV 生成）
6. `summary.txt` を `out_dir / "summary.txt"` に書き込み + stdout に print

**重要な特徴:**
- **すべての I/O がディスクベース**（`Path.open`, `Path.write_text`, `csv.writer`(file)）
- 関数化されているのは `common.py` と `ab_match.py` のみ。`dedup_csv.py` / `filter_lines.py` / `reorder_columns.py` は `main()` 一本でロジックがインライン
- CSV 読み込みは `csv.DictReader` (header) / `csv.reader` (no header) を使い分け
- キー正規化は `norm_key`（`strip + lower + 引用符除去`）
- ファイル名・列名・キー値は **すべて UTF-8（BOM 対応 `utf-8-sig`）**

### 2.2 freeder の Next.js + Docker パターン

**ビルド時 basePath 注入:**

```dockerfile
ARG NEXT_PUBLIC_BASE_PATH=/freeder
ENV NEXT_PUBLIC_BASE_PATH=$NEXT_PUBLIC_BASE_PATH
RUN npm run build
```

```typescript
// next.config.ts
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const nextConfig: NextConfig = {
  basePath: BASE_PATH,
  assetPrefix: BASE_PATH,
  env: { NEXT_PUBLIC_BASE_PATH: BASE_PATH },
};
```

→ Next.js が自動的にすべての internal link と asset URL に `/freeder` prefix を付ける。

**compose.yaml での渡し方:**

```yaml
freeder:
  build:
    context: ./repos/freeder-prd
    args:
      NEXT_PUBLIC_BASE_PATH: /freeder
  expose: ["3000"]
```

### 2.3 hbextra の Flask prefix パターン

```python
from werkzeug.middleware.dispatcher import DispatcherMiddleware

_HBEXTRA_PREFIX = '/hbextra'

def _root_redirect_app(environ, start_response):
    target = _HBEXTRA_PREFIX + '/'
    start_response('302 Found', [('Location', target), ('Content-Type', 'text/plain; charset=utf-8')])
    return [b'Redirecting to /hbextra/']

app.wsgi_app = DispatcherMiddleware(_root_redirect_app, {_HBEXTRA_PREFIX: app.wsgi_app})
```

これは **Flask の流儀**。FastAPI なら別の方法が要る（後述）。

### 2.4 Caddyfile の path matcher パターン

```caddy
handle @host_prod {
    @protected_prod path /p2/* /kssk/* /moemoe/* /freeder /freeder/* /hbextra /hbextra/*
    basic_auth @protected_prod {
        jonji $2a$14$...
    }

    @freeder_prod path /freeder /freeder/*
    handle @freeder_prod {
        reverse_proxy freeder:3000
    }
}
```

特徴:
- `path /freeder /freeder/*` で末尾スラッシュなしと配下両方をマッチ
- `basic_auth` matcher は `@protected_*` で保護対象を path で限定
- `reverse_proxy` は service 名（compose 上のコンテナ名）+ port

### 2.5 compose.yaml のビルドコンテキスト分離パターン

prd と dev は **完全に別 service** + **別ビルドコンテキスト** (`./repos/<app>-prd` / `./repos/<app>-dev`)。

→ dev で別ブランチを試したいときは `~/server/repos/freeder-dev/` 内で `git checkout <branch>` してから `docker compose build freeder-dev` する流れ。

## 3. 影響範囲

### 3.1 既存 listscrub への影響

**目標**: 既存 CLI 動作を破壊せずに、コア関数を Web API から再利用可能にする。

**リファクタ案（推奨: 後方互換 + コア分離）:**

```
00_Program/
├── ab_match.py                  # CLI ラッパー（既存、ロジックを core から呼ぶように改修）
├── dedup_csv.py                 # 同上
├── filter_lines.py              # 同上
├── reorder_columns.py           # 同上
├── common.py                    # 共通ユーティリティ（CLI 用 IO 関数は維持）
└── core/                        # ★ 新規: メモリベース純粋関数群
    ├── __init__.py
    ├── ab_match.py              # ab_match(a_bytes, b_bytes, ...) -> dict[str, bytes]
    ├── dedup.py
    ├── filter_lines.py
    ├── reorder.py
    └── common.py                # norm_key, sniff_delimiter 等の純粋関数だけ抽出
```

**API 設計（コア関数のシグネチャ案）:**

```python
# core/ab_match.py
def ab_match(
    a_bytes: bytes,
    b_bytes: bytes,
    *,
    header_a: bool = True,
    header_b: bool = True,
    key_a: str | None = None,
    key_b: str | None = None,
    key_index_a: int | None = None,
    key_index_b: int | None = None,
    delimiter_a: str = "auto",  # "auto" | "tab" | "comma" | "semicolon"
    delimiter_b: str = "auto",
) -> tuple[dict[str, bytes], dict]:
    """戻り値: (出力ファイル名 -> bytes, summary dict)
    例: ({"in_both_123.csv": b"...", "only_a_xxx_45.csv": b"...", "only_b_xxx_67.csv": b"...", "summary.txt": b"..."}, {"a_total": ..., ...})
    """
```

**テストの観点**: 既存 CLI が refactor 後も同じ出力を出すか（既存サンプルで diff チェック）。

### 3.2 新規ファイル群

```
listscrub/
├── 00_Program/                  # ↑ リファクタ済み
├── api/                         # ★ 新規: FastAPI バック
│   ├── main.py                  # FastAPI app + 4 endpoints
│   ├── requirements.txt         # fastapi, uvicorn, python-multipart
│   └── Dockerfile               # python:3.11-slim + uvicorn 起動
├── web/                         # ★ 新規: Next.js フロント
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx              # ホーム（4 ツール一覧）
│   │   │   ├── ab-match/page.tsx
│   │   │   ├── dedup/page.tsx
│   │   │   ├── filter-lines/page.tsx
│   │   │   └── reorder/page.tsx
│   │   └── components/
│   │       ├── ToolStep.tsx          # 共通シグネチャ <ToolStep input onResult>
│   │       ├── AbMatchStep.tsx
│   │       ├── DedupStep.tsx
│   │       ├── FilterLinesStep.tsx
│   │       └── ReorderStep.tsx
│   ├── next.config.ts
│   ├── package.json
│   ├── Dockerfile
│   ├── tsconfig.json
│   └── postcss.config.mjs
└── tasks/fon/20260504-1526-z5r4/   # フォN 管理
```

### 3.3 自宅サーバ側への影響

**`~/server/compose.yaml` への追加 services（4 つ）:**

```yaml
listscrub-front:
  build:
    context: ./repos/listscrub-prd/web
    args:
      NEXT_PUBLIC_BASE_PATH: /listscrub
  container_name: listscrub-front
  restart: always
  expose: ["3000"]

listscrub-front-dev:
  build:
    context: ./repos/listscrub-dev/web
    args:
      NEXT_PUBLIC_BASE_PATH: /listscrub
  container_name: listscrub-front-dev
  restart: always
  expose: ["3000"]

listscrub-api:
  build:
    context: ./repos/listscrub-prd
    dockerfile: api/Dockerfile
  container_name: listscrub-api
  restart: always
  expose: ["8000"]

listscrub-api-dev:
  build:
    context: ./repos/listscrub-dev
    dockerfile: api/Dockerfile
  container_name: listscrub-api-dev
  restart: always
  expose: ["8000"]
```

**注意**: `listscrub-api` のビルドコンテキストは **リポルート**（`./repos/listscrub-prd`）にする。これは `00_Program/` を `api/` 内から `import` するため、context が api/ 配下では足りないから。`dockerfile: api/Dockerfile` で Dockerfile 位置だけ指定。

**`caddy` service の `depends_on` に追加:** `listscrub-front`, `listscrub-front-dev`, `listscrub-api`, `listscrub-api-dev`

**`~/server/caddy/Caddyfile` への追加:**

```caddy
# host_prod の handle 内
@protected_prod path ... /listscrub /listscrub/*
# basic_auth は既存ブロックに path 追加するだけ

# /listscrub/api/* を先にマッチ（path 順序重要）
@listscrub_api_prod path /listscrub/api/*
handle @listscrub_api_prod {
    reverse_proxy listscrub-api:8000
}

# /listscrub と /listscrub/* は Next.js
@listscrub_prod path /listscrub /listscrub/*
handle @listscrub_prod {
    reverse_proxy listscrub-front:3000
}
```

dev 側も同じ構造で `-dev` 付きサービスへ。

**`~/server/repos/listscrub-prd/` と `~/server/repos/listscrub-dev/` を作成（GitHub から clone）。**

**Cloudflare Tunnel**: `316006.com` と `dev.316006.com` のドメインは既に Tunnel で受けている前提（既存 freeder/hbextra が動作している = Tunnel は新規 listscrub の path 追加のみで反応するはず、Tunnel 設定変更は不要、と推測）。**未確認なので Step 7 で実機検証時に確認**。

## 4. 過去の類似実装

### 4.1 freeder の Next.js basePath 運用（直接参考になる）

- `next.config.ts` で `basePath` を環境変数化
- Dockerfile で `ARG NEXT_PUBLIC_BASE_PATH` をビルド時注入
- compose.yaml の `args` で値を渡す
- → listscrub の web/ も同じパターンを **そのまま適用**

### 4.2 hbextra の Flask prefix（FastAPI に翻訳が必要）

hbextra は `DispatcherMiddleware` で `/hbextra` prefix を扱うが、FastAPI で同じことをやるには:

**選択肢 A: Caddy 側で `handle_path` を使って prefix を剥がす**

```caddy
handle_path /listscrub/api/* {
    reverse_proxy listscrub-api:8000
}
```

- FastAPI 側は `/` ベースで実装（`@app.post("/ab_match")` など）
- 既存 rep2z (`handle_path /p2/*`) と同パターン
- **推奨**: 一番シンプル

**選択肢 B: FastAPI 側で `root_path` を設定**

```python
app = FastAPI(root_path="/listscrub/api")
```

- OpenAPI docs (`/listscrub/api/docs`) が正しく動く
- Caddy 側は普通の `reverse_proxy`
- 短所: hardcode になる、または環境変数経由で渡す手間

**選択肢 C: APIRouter prefix**

```python
router = APIRouter(prefix="/listscrub/api")
```

- 上記 A の Caddy 側でも prefix 残す形になる
- 一番冗長

**最終推奨: A**（既存 rep2z パターンと揃う、FastAPI コードがクリーン、`/docs` が必要なら開発時のみ別途 expose）。

### 4.3 git log と過去の蓄積

- `listscrub` リポは初期コミット 2 件のみ（`92ad2c9 Initial commit` + `f146117 Restructure into 00_Program/ with positional args, shared utils, and input file copying`）。Web 化 PR は完全に新規
- `tasks/lessons.md` は存在しない（このプロジェクトにとって初のフォN サイクル）
- 親プロジェクト群（freeder, hbextra）に `tasks/` ディレクトリはあるが、Web 化に直接関連する lessons はメモリ上に未確認

## 5. 想定される副作用 / リスク

### 5.1 既存 CLI のリグレッション

**リスク**: コア分離リファクタで既存 CLI の振る舞いが変わる。出力 CSV のフォーマット、ファイル名の連番、summary.txt の項目順などがズレる可能性。

**対策**:
- 既存 CLI が出すサンプル出力を「正解」として保存
- リファクタ後、同じ入力で diff 確認
- ローカルで `python3 00_Program/ab_match.py IN/list_a.csv IN/list_b.csv` を試して破壊が無いことを確認

### 5.2 メモリ要件（150 万件 × 30 万件突合）

**リスク**: FastAPI コンテナのメモリ上限。Docker の default unlimited だが、コンテナ内の Python プロセスが OOM Killer に殺される可能性。

**見積もり**:
- ファイル受信（`UploadFile`）: 200MB 前後
- `BytesIO` でメモリ展開: 200MB
- `csv.DictReader` で dict 化 + Set: 1〜2GB
- 出力生成（StringIO/BytesIO）: 数百 MB
- **ピーク 2〜3GB**

**対策**:
- 32GB の mmini4 では余裕
- compose.yaml で `mem_limit` を設定しない（unlimited）
- 万一に備えて `swapaccount=1` がカーネルで有効か確認（自宅サーバなので普通は OK）

### 5.3 ファイル無残置の網羅性

**リスク**: tempfile を使わなくても、以下の経路でディスクに書かれる可能性:
- FastAPI の `UploadFile` の **デフォルト挙動**: 1MB 超は `SpooledTemporaryFile` で `/tmp` に書く
- Uvicorn / FastAPI のアクセスログが標準出力 → Docker JSON ログドライバが `/var/lib/docker/containers/*/...-json.log` に書き込む
- `print` 文の中身がログに行く可能性

**対策**:
- `UploadFile` は使わず、`Request.body()` または `Request.stream()` で生バイトを直接受ける（`SpooledTemporaryFile` を回避）
- アクセスログには **URL のみ** 記録（クエリ文字列・ヘッダ・ボディは記録しない）
- `print` 文を入れない、ログレベル WARNING 以上のみ
- Caddy のアクセスログも URL のみ（既存設定が `format console` なので確認）

### 5.4 Cloudflare Tunnel の path ベース routing

**リスク**: 既存 Tunnel 設定が host ベース routing（`316006.com` → mmini4:80）のみで、`/listscrub` を別の host にルーティングする設定があると干渉する。

**確認方法**: Step 7 でブラウザ実機検証時に確認。`curl https://316006.com/listscrub/` で疎通確認。**Step 4 の plan には「Tunnel 設定確認」を 1 タスクとして含める**。

### 5.5 Next.js basePath とクライアント `fetch` の食い違い

**リスク**: Next.js の `basePath: '/listscrub'` 下で `fetch('/api/ab_match')` を書くと自動で `/listscrub/api/ab_match` には **ならない**（`fetch` は basePath 適用外）。**明示的に `fetch('/listscrub/api/ab_match')` と書く必要がある**。

**対策**:
- API クライアント関数を `web/src/lib/api.ts` に集約、`process.env.NEXT_PUBLIC_BASE_PATH` を base に組み立てる
- `const API_BASE = process.env.NEXT_PUBLIC_BASE_PATH ? `${process.env.NEXT_PUBLIC_BASE_PATH}/api` : '/api'`

### 5.6 大ファイル multipart アップロードのタイムアウト

**リスク**: 150 万件 CSV (約 200MB) のアップロード + 処理 + 結果ダウンロードが、Caddy / Next.js / FastAPI どこかでタイムアウトする可能性。

**対策**:
- Caddy: デフォルトでは reverse_proxy のタイムアウトはほぼ無制限だが、念のため `transport http { read_timeout 0 write_timeout 0 }` を確認
- Uvicorn: `--timeout-keep-alive 300` 等で長めに設定
- フロント: `fetch` の AbortController + UI の進捗表示でユーザーが諦めないように

### 5.7 React コンポーネントのワークフロー対応シグネチャ

**制約 6（MVP は単発、Phase 2 でワークフロー）を満たすために**: 各ツール画面の中身を `<XxxStep input={Blob|null} onResult={(Blob) => void}>` 互換コンポーネントとして実装。単発画面はそのコンポーネントを `input={null}` で wrap し、Phase 2 のワークフロー画面は input を流し込む形で再利用。

`onResult` の戻り値 `Blob` は **複数ファイル**を持つツール（ab_match の 3 ファイル + summary）の場合、ZIP 化して 1 つの Blob にする設計が素直。または `Blob[]` にするか。**Step 4 のプランニングで決定**。

## 6. 制約条件

1. **既存 freeder/hbextra の運用パターンに揃える**: ビルドコンテキスト命名 (`-prd` / `-dev`)、Caddyfile の path matcher 構造、Dockerfile スタイル
2. **アプリ層に認証コードを持ち込まない**: 将来 Uniikey 移行のため、Next.js middleware も FastAPI dependency も認証用には使わない（middleware.ts は freeder では iron-session 用だが listscrub では作らない）
3. **ファイル無残置（Constraints 1）**: tempfile 経由禁止、ディスクへの書き込みゼロ、ログにファイル名や個人情報を含めない
4. **既存 Python の I/O リファクタ範囲限定**: コア関数化に必要な範囲のみ。CSV パースのアルゴリズム本体やキー正規化のロジックは無修正
5. **bilingual UI 対応の保留**: 既存 README は日英バイリンガルだが、UI は日本語のみで MVP（Phase 2 で英訳要否を判断）
6. **データ規模制約**: 150 万件 × 30 万件突合まで保証。それ以上のサイズは Phase 2 で検討
7. **MVP スコープ厳守**: ワークフロー UI は作らない、ユーザー履歴も作らない、設定画面も作らない

## 7. テスト戦略

### 7.1 既存 CLI の回帰テスト（手動）

サンプル CSV を `IN/` に置き、リファクタ前後で `python3 00_Program/<tool>.py ...` を実行して `OUT/` の差分を `diff -r` で確認。

### 7.2 コア関数の単体テスト（pytest 推奨）

```
api/tests/
├── test_core_ab_match.py        # core.ab_match() の入出力検証
├── test_core_dedup.py
├── test_core_filter_lines.py
├── test_core_reorder.py
└── fixtures/
    ├── sample_a.csv             # 100 行程度の小サンプル
    ├── sample_b.csv
    └── ...
```

確認項目:
- in_both / only_a / only_b の件数が期待通り
- ヘッダ有無、キー列指定、デリミタ自動検出
- BOM 付き UTF-8 を扱える
- 巨大データのスモークテスト（pytest mark で `@pytest.mark.large` 区切り）

### 7.3 FastAPI エンドポイントのテスト（pytest + httpx.AsyncClient）

```
api/tests/test_endpoints.py
```

確認項目:
- `POST /ab_match` に multipart で 2 ファイル送ると 200 + ZIP が返る
- 不正リクエスト（ファイル無し、列指定間違い）で 400 が返る
- レスポンス後に `/tmp` に痕跡が残らない（テスト中に `os.listdir('/tmp')` を before/after で比較）

### 7.4 Web フロント（手動 + 軽い E2E）

- Next.js dev server (`npm run dev`) で各ツール画面を開く
- 小サンプルでファイルアップロード → 処理 → DL の流れを確認
- ブラウザ DevTools で `fetch` URL が `/listscrub/api/ab_match` 等になっているか確認
- React コンポーネントが `<ToolStep input={null} onResult={...}>` シグネチャで動くか（型チェック + dev 時の動作）

### 7.5 統合検証（実機: 自宅サーバ デプロイ後）

- `cd ~/server && docker compose up -d --build listscrub-front listscrub-front-dev listscrub-api listscrub-api-dev`
- `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`
- `https://dev.316006.com/listscrub/` を Cloudflare Tunnel 経由でブラウザアクセス → basic_auth プロンプト → ログイン → 4 ツール画面が表示される
- 150 万件 × 30 万件の `ab_match` を実行 → 完走 → ZIP DL
- mmini4 で `ls /tmp/ | grep -i listscrub` および `docker exec listscrub-api ls /tmp/` で痕跡なしを確認
- prd 側 (`https://316006.com/listscrub/`) でも疎通確認

### 7.6 不確かポイント（要追加調査）

- **Cloudflare Tunnel が `/listscrub` path を新規追加で受けてくれるか**（既存 Tunnel 設定の確認が未完了。`cloudflared tunnel route ingress list` 等で確認するか、または実機で疎通確認）
- **freeder の `src/middleware.ts` が listscrub の path に干渉しないか**: 別ドメイン・別コンテナなので干渉しないはずだが、Caddyfile 側で path が交差していないか念のため確認
- **既存 hbextra のセッションが `/listscrub` 配下で漏れないか**: Cookie の `Path` 属性次第。`/hbextra` Path で発行されていれば干渉なし、`Path=/` だとセッション情報が listscrub にも送られる（読まない設計だから害なし、ただし観点として記録）
