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

docker compose --project-name plane-poc --env-file poc/.env \
  -f deployments/cli/community/docker-compose.yml up -d
```

`migrator` がマイグレーションを流し終わるまで 1〜2 分かかる。次が 200 を返せば準備完了。

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/api/instances/
```

## データ投入

```bash
docker compose --project-name plane-poc --env-file poc/.env \
  -f deployments/cli/community/docker-compose.yml \
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
docker compose --project-name plane-poc --env-file poc/.env \
  -f deployments/cli/community/docker-compose.yml \
  exec -T api python - < poc/setup_instance.py
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

言語は右上のプロフィール → Settings から日本語に切り替える。

## 停止・破棄

```bash
# 停止（データは残る）
docker compose --project-name plane-poc --env-file poc/.env \
  -f deployments/cli/community/docker-compose.yml down

# データごと破棄
docker compose --project-name plane-poc --env-file poc/.env \
  -f deployments/cli/community/docker-compose.yml down -v
```

## 注意

- 登場する会社名・人名・工事名・金額はすべて**架空**である
- `poc/.env` は upstream の `.gitignore` により追跡されない。秘密情報はここに置く
- このリポジトリは PUBLIC。実在の顧客名・現場名を投入しないこと
