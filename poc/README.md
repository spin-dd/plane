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

`poc/docker-compose.override.yml` はリリース済みイメージに**含まれない fork のコード**を
マウントして有効化する。

| マウント対象                                      | 目的                                                              |
| ------------------------------------------------- | ----------------------------------------------------------------- |
| `plane/settings/spindd.py`                        | `DJANGO_SETTINGS_MODULE` の差し替え（MIME 追加・アプリ登録・URL） |
| `plane/spindd_ext/`                               | 工事台帳の独自 Django アプリ                                      |
| `plane/app/views/issue/{base,comment,version}.py` | **GUEST の可視範囲の改変（優先度 5）**                            |

**最後の 3 つを載せないと、GUEST の可視範囲が upstream のまま（自分が作成した課題のみ）になり、
協力会社に担当課題が見えない。** `CONTRIBUTING.spindd.md` §3 の「実装中の優先度 5 の改変」の表と
対応している。fork 側で upstream ファイルを改変したらここにも足すこと。

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

独自 Django アプリのマイグレーションを流し、架空の工事情報 4 件を投入する。

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

**登録・編集は台帳ページのフォームから行う。** Plane は `django.contrib.admin` を
`INSTALLED_APPS` に含めておらず `admin/` の URL も無いため、Django admin は使えない。

書き込み権限は**ワークスペース ADMIN または対象現場の ADMIN** に限る（請負金額を含むため）。
シードの役割だと以下のようになる。

| ユーザー                                         | 権限   | 編集できる現場                 |
| ------------------------------------------------ | ------ | ------------------------------ |
| `yamada`（ワークスペース ADMIN）                 | 全現場 | すべて                         |
| `sato`（SKTC の現場 ADMIN）                      | 1 現場 | SKTC のみ                      |
| `suzuki` / `tanaka` / `takahashi`（現場 MEMBER） | なし   | 閲覧のみ（編集ボタンが出ない） |

画面は `/<workspaceSlug>/construction-ledger`（**フロントは dev サーバでのみ確認できる**。
リリース済みイメージには `@plane/spindd` が含まれていない）。

```bash
pnpm turbo run build --filter=web^...   # 初回のみ
pnpm --filter web dev                    # http://localhost:3000
```

### 残り 3 現場の課題と協力会社アカウント

```bash
docker compose --project-name plane-poc --env-file poc/.env --project-directory . \
  -f deployments/cli/community/docker-compose.yml \
  -f poc/docker-compose.override.yml \
  exec -T api python - < poc/seed_more_sites.py
```

性格の違う 3 現場に課題を入れ、**協力会社の GUEST アカウント**を作る。

| 現場 | 性格                         | 課題 |
| ---- | ---------------------------- | ---: |
| SKTC | 新築・施工中                 |   32 |
| TKMS | 居ながら改修・竣工済み       |    8 |
| YKHS | 既存稼働中の増築・夜間作業   |    7 |
| OMYA | 駅前狭小敷地の新築・着工直後 |    6 |

## 協力会社の可視範囲を確かめる

GUEST は「**自分が作成した、または自分が担当している**課題」だけが見える（[#14](https://github.com/spin-dd/plane/pull/14)）。
upstream の CE は「自分が作成した課題のみ」なので、元請が起票して割り当てた是正指示は
担当者に見えない。その差を確認できるデータが入っている。

| アカウント                                    | 参加現場    | 見える課題      |
| --------------------------------------------- | ----------- | --------------- |
| `misaki@misaki-steel.example`（三崎鉄骨建設） | YKHS        | 7 件中 **1 件** |
| `daiwa@daiwa-kiso.example`（大和基礎工業）    | YKHS / OMYA | 各 **1 件**     |
| `toyo@toyo-densetsu.example`（東洋電設工業）  | TKMS        | 8 件中 **2 件** |

パスワードは全員 `PlanePoC!2026`。いずれも**担当だが作成者ではない**課題なので、
upstream の CE のままなら 0 件になる。

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
