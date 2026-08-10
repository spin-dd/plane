# PoC: 建設現場の課題管理としての Plane 評価

Issue [#3](https://github.com/spin-dd/plane/issues/3) の実行環境。

架空の建設案件「（仮称）新川崎テクノロジーセンター新築工事」を素の Plane に投入し、
日本の建設現場の実務にどこまで耐えるかを確かめる。

> このディレクトリは fork 側で追加した**新規ファイルのみ**で構成されている。
> upstream 由来のファイルは 1 つも改変していない（[`CONTRIBUTING.spindd.md`](../CONTRIBUTING.spindd.md) §3）。

## 前提

- Docker（arm64 / amd64 いずれも可。`v1.4.1` は両アーキテクチャのイメージが公開されている）
- 空きディスク 5GB 程度
- ホストの `8080` 番ポート

イメージは upstream のリリース済みイメージ `makeplane/plane-*:v1.4.1` を使う。
`spindd` の基点タグと同一なのでソースビルドは不要。

## 起動

```bash
cp poc/.env.example poc/.env
# SECRET_KEY と LIVE_SERVER_SECRET_KEY を書き換える
#   openssl rand -hex 16

docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
  -f deployments/cli/community/docker-compose.yml \
  -f poc/docker-compose.override.yml up -d
```

`poc/docker-compose.override.yml` は `apps/api/plane/settings/spindd.py` をマウントして
`DJANGO_SETTINGS_MODULE` で有効化する（HEIC などの MIME 追加、`DATA_UPLOAD_MAX_MEMORY_SIZE`
の切り離し）。リリース済みイメージにはこのファイルが無いため、マウントで代替している。

**`--project-directory .` は必須。** 無いと override 内の相対パスが 1 つ目の compose
ファイルのディレクトリ基準で解決され、マウント元を見失う。

override 無しでも起動はできる（`FILE_SIZE_LIMIT` は環境変数だけで効く）。

`migrator` がマイグレーションを流し終わるまで 1〜2 分かかる。次が 200 を返せば準備完了。

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/api/instances/
```

## データ投入

```bash
docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
  -f deployments/cli/community/docker-compose.yml \
  -f poc/docker-compose.override.yml \
  exec -T api python - < poc/seed_construction.py
```

冪等なので何度実行してもよい。投入されるもの:

| 対象                 | 件数                                                          |
| -------------------- | ------------------------------------------------------------- |
| ワークスペース       | 1（株式会社スピン建設）                                       |
| プロジェクト（現場） | 1（26-A-0147 新川崎テクノロジーセンター新築工事 / `SKTC`）    |
| メンバー             | 5（現場代理人・工事主任・安全衛生責任者・設備担当・工事事務） |
| ステータス           | 6（未着手 / 施工中 / 検査待ち / 是正中 / 完了 / 保留）        |
| ラベル               | 13（分類 7 + 協力会社 6）                                     |
| 工種 Module          | 9                                                             |
| 月次 Cycle           | 6（2026年4月度〜9月度）                                       |
| 課題 Work Item       | 32                                                            |
| コメント             | 13                                                            |

### インスタンス初期設定

初回は Plane のインスタンスが未設定のため、そのままではログインできない
（`INSTANCE_NOT_CONFIGURED`）。次で設定する。

```bash
docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
  -f deployments/cli/community/docker-compose.yml \
  -f poc/docker-compose.override.yml \
  exec -T api python - < poc/setup_instance.py
```

### 工事台帳（spindd_ext）

独自 Django アプリのマイグレーションを流し、架空の工事情報 3 件を投入する。

```bash
docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
  -f deployments/cli/community/docker-compose.yml \
  -f poc/docker-compose.override.yml \
  exec -T api python manage.py migrate spindd_ext

docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
  -f deployments/cli/community/docker-compose.yml \
  -f poc/docker-compose.override.yml \
  exec -T api python - < poc/seed_construction_ledger.py
```

API は `/api/spindd/workspaces/spin-kensetsu/construction-ledger/`。
画面は `/<workspaceSlug>/construction-ledger`（**フロントは dev サーバでのみ確認できる**。
リリース済みイメージには `@plane/spindd` が含まれていない）。

```bash
pnpm turbo run build --filter=web^...   # 初回のみ
pnpm --filter web dev                    # http://localhost:3000
```

## ログイン

<http://localhost:8080>

| メール                            | 役割                             |
| --------------------------------- | -------------------------------- |
| `yamada@spin-kensetsu.example`    | 現場代理人・監理技術者（管理者） |
| `sato@spin-kensetsu.example`      | 工事主任                         |
| `suzuki@spin-kensetsu.example`    | 安全衛生責任者                   |
| `tanaka@spin-kensetsu.example`    | 設備担当                         |
| `takahashi@spin-kensetsu.example` | 工事事務                         |

パスワードは全員 `PlanePoC!2026`。**PoC 専用。外部公開しないこと。**

UI 言語はシードが `Profile.language = "ja"` を設定するので、そのまま日本語で表示される。
UI 言語を持つのは `User` ではなく `Profile`（既定 `"en"`）で、Profile は初回ログイン時に
遅延作成される点に注意（`apps/api/plane/db/models/user.py:251`）。

## 添付ファイル

| 項目                   | PoC の設定                             | upstream 既定            |
| ---------------------- | -------------------------------------- | ------------------------ |
| 上限サイズ             | **50MB**（`FILE_SIZE_LIMIT=52428800`） | 5MB                      |
| HEIC / HEIF            | **許可**（`spindd.py` で追加）         | 拒否                     |
| DWG / DXF              | **許可**（同上）                       | 明示的な MIME では拒否   |
| POST body の許容メモリ | 5MB に据え置き                         | `FILE_SIZE_LIMIT` と同値 |

添付は presigned POST で S3/MinIO へ直送され Django を経由しないため、上限を上げても
Django のメモリ消費は増えない。`DATA_UPLOAD_MAX_MEMORY_SIZE` を切り離しているのはそのため。

## 停止・破棄

```bash
# 停止（データは残る）
docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
  -f deployments/cli/community/docker-compose.yml \
  -f poc/docker-compose.override.yml down

# データごと破棄
docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
  -f deployments/cli/community/docker-compose.yml \
  -f poc/docker-compose.override.yml down -v
```

## 注意

- 登場する会社名・人名・工事名・金額はすべて**架空**である
- `poc/.env` は upstream の `.gitignore` により追跡されない。秘密情報はここに置く
- このリポジトリは PUBLIC。実在の顧客名・現場名を投入しないこと
