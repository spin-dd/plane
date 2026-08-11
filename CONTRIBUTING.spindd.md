# spin-dd/plane fork 運用ガイド

このリポジトリは [makeplane/plane](https://github.com/makeplane/plane) (Community Edition / AGPL-3.0) の fork である。
日本の建設企業向け社内課題管理システムとしての利用可否を評価し、必要なカスタマイズを積むことを目的とする。

**このファイルは fork 側で追加した新規ファイルであり、upstream には存在しない。**
upstream 由来のファイル（`AGENTS.md`、`CONTRIBUTING.md`、`.github/pull_request_template.md` など）は
コンフリクトの原因になるため、原則として編集しない。

---

## 0. なぜルールが要るのか

fork を維持する以上、**upstream のコミットを取り込み続けられること**が前提条件になる。
upstream は約 3 ヶ月で **109 コミット / 300 ファイル超**のペースで動いている（v1.3.1 → v1.4.1 実測）。
この追従が破綻すると、セキュリティ修正も取り込めなくなり、fork そのものが行き止まりになる。

以下のルールはすべて「追従コストを構造的に下げる」ことを目的としている。

一次情報の調査: <https://github.com/hdknr/blogs/pull/631>

---

## 1. ブランチとリモートの構成

| 名前                     | 役割                                                          |
| ------------------------ | ------------------------------------------------------------- |
| `spindd`                 | **既定ブランチ。** 常に upstream のリリースタグを祖先に持つ   |
| `preview`                | upstream 追従用のミラー。**作業ブランチのベースには使わない** |
| `sync/vX.Y.Z`            | upstream のリリースタグを取り込むための一時ブランチ           |
| `feat/<issue>-<desc>` 等 | 作業ブランチ。`spindd` から切って `spindd` へ PR              |

初回セットアップ:

```bash
git remote add upstream https://github.com/makeplane/plane.git
git fetch upstream --tags
```

---

## 2. 追従は必ず「リリースタグ」基準で行う

```bash
git fetch upstream --tags
git tag -l 'v*' --sort=-v:refname | head        # 最新のリリースタグを確認
git checkout -b sync/vX.Y.Z spindd
git merge vX.Y.Z                                # rebase ではなく merge
# コンフリクト解消 → CI → PR → spindd へマージ
```

### やってはいけないこと

- ❌ **`upstream/preview` を merge / rebase する。**
  `preview` は upstream の開発ブランチであり、リリース前の壊れた状態を含む。
- ❌ **`-rc1` / `-rc2` などの RC タグを基準にする。**
  実例: 当初 `spindd` は `preview` HEAD（= `v1.4.1-rc2`）から切られており、
  リリースタグ `v1.4.1` の 4 コミット手前だった。現在は `v1.4.1` に fast-forward 済み。
- ❌ **タグを飛ばしてまとめて取り込む。**
  1 リリースずつ順に取り込む。飛ばすとコンフリクト解消が破綻し、レビュー不能になる。
- ❌ **公開ブランチを rebase する。** `spindd` は公開済みなので履歴を書き換えない。

### 追従の頻度

- 通常: リリースごと（四半期あたり 100 コミット超を工数として計上する）
- 臨時: セキュリティ修正。改変する以上、公式イメージは使えず自前ビルドになるため、
  **どの程度の遅延で取り込むかの基準を事前に決めておく**

---

## 3. 改変はどこに置くか

コンフリクト量は**既存ファイルを何行変えたか**にほぼ比例する。
下の表を**上から順に**検討し、下へ落ちるほど設計を見直すこと。

| 優先 | 手段                                           | 追従耐性        | 主な用途                           |
| ---- | ---------------------------------------------- | --------------- | ---------------------------------- |
| 1    | 環境変数・インスタンス設定                     | ◎ 差分ゼロ      | 認証、SMTP、ストレージ、`AMQP_URL` |
| 2    | i18n ロケール (`packages/i18n/src/locales/ja`) | ○ JSON の値のみ | 用語の置換                         |
| 3    | テーマ・CSS の上書き                           | ○               | 見た目・ブランディング             |
| 4    | 新規ファイル / 新規 Django アプリの追加        | ○ 衝突しない    | 独自機能                           |
| 5    | 既存ファイルの改変                             | ✕ 毎回衝突      | **最終手段。** PR に理由を明記する |

### 拡張の継ぎ目（seam）は存在する

> 2026-08-10 訂正: 以前このガイドは「プラグイン seam は存在しない」と記述していた。**誤りだった。**
> CE は空のスタブを置き、EE が同じファイルを実装で置き換える設計になっている。

**本体が空のスタブ = 拡張のための継ぎ目**である。CE では空のまま維持されるので upstream がほとんど触らず、
ここを埋める形の改変はコンフリクトしにくい。

| ファイル                                                                        | 空スタブ                                   | 用途                     |
| ------------------------------------------------------------------------------- | ------------------------------------------ | ------------------------ |
| `apps/web/app/routes/extended.ts`                                               | `extendedRoutes = []`                      | 画面の追加               |
| `apps/web/app/routes/redirects/extended/index.ts`                               | `extendedRedirectRoutes = []`              | リダイレクト             |
| `apps/web/core/hooks/use-workspace-issue-properties-extended.tsx`               | `() => {}`                                 | カスタムプロパティの取得 |
| `apps/web/core/components/workspace-notifications/notification-card/content.ts` | `ADDITIONAL_NOTIFICATION_CONTENT_MAP = {}` | 通知種別の追加           |
| `packages/constants/src/auth/extended.ts`                                       | `EXTENDED_LOGIN_MEDIUM_LABELS = {}`        | 認証手段の追加           |
| `packages/editor/src/ce/constants/assets.ts`                                    | `ADDITIONAL_ASSETS_META_DATA_RECORD = {}`  | エディタ拡張             |
| `packages/editor/src/ce/constants/extensions.ts`                                | `ADDITIONAL_BLOCK_NODE_TYPES = []`         | 同上                     |

`routes.ts` は `mergeRoutes(coreRoutes, extendedRoutes)` で合成しており、`extendedRoutes` 側が
core を上書きできる（`app/routes/helper.ts`）。

**注意:** `ExtendedProjectSidebar` / `ExtendedAppHeader` / `extended-sidebar-item.tsx` などは
CE の実装本体であり継ぎ目ではない。"extended" は「拡張サイドバー」という UI 要素の名前である。
継ぎ目かどうかは**エクスポートされている本体が空かどうか**で判断する。

### 継ぎ目の使い方: 実装は自パッケージ、継ぎ目は 1 行

継ぎ目のファイルに実装を書くと、そのファイルがコンフリクト対象として育ってしまう。
**実装は必ず `packages/spindd`（フロント）/ `apps/api/plane/spindd_ext`（バックエンド）に置き、
継ぎ目には re-export の 1 行だけを書く。**

```ts
// apps/web/app/routes/extended.ts（upstream のスタブ。本体をこの 1 行に差し替える）
export { extendedRoutes } from "@plane/spindd/routes";
```

こうするとコンフリクト面積が「機能の大きさ」ではなく「継ぎ目の数」になる。

### バックエンドは upstream を 1 行も触らずに拡張できる

`ROOT_URLCONF` と `INSTALLED_APPS` はどちらも**設定値**なので、`plane/settings/spindd.py` から
差し替えられる。`plane/urls.py` も `plane/settings/common.py` も改変不要である。

```python
# apps/api/plane/settings/spindd.py
INSTALLED_APPS += ("plane.spindd_ext",)
ROOT_URLCONF = "plane.spindd_ext.urls"     # plane/urls.py を編集せずに URL を足せる
```

```python
# apps/api/plane/spindd_ext/urls.py（新規）
from plane.urls import urlpatterns as plane_urlpatterns

urlpatterns = [*plane_urlpatterns, path("api/spindd/", include("plane.spindd_ext.api.urls"))]
```

独自アプリなので `migrations/` も自前で持て、§4 の連番衝突も起きない。

**アプリは `plane` パッケージの内側に置くこと。** `apps/api/Dockerfile.api` は
`COPY plane plane/` しかしないため、`plane` の外に置くと本番イメージに含まれず、
`DJANGO_SETTINGS_MODULE=plane.settings.spindd` を有効にしたイメージが
`ModuleNotFoundError` で起動不能になる（API 全体が落ちる）。

**Plane の削除は soft delete である。** 独自モデルが Plane のモデルを FK で参照する場合、
`plane.db.mixins.SoftDeleteModel` を継承して `deleted_at` を持たせる。
`plane/bgtasks/deletion_task.py` は関連先に `deleted_at` がある場合だけ連鎖させるため、
これが無いと現場を削除しても独自レコードが残り続け、OneToOne の枠と一意キーを
占有したまま再登録できなくなる。一意制約も `condition=Q(deleted_at__isnull=True)` を付ける。

### 実装中の優先度 5 の改変（追従時に必ず確認する）

継ぎ目が無く、やむを得ず upstream の実コンポーネントを改変している箇所。
**追従でコンフリクトしたら、必ず下の注意点を読んでから解決すること。**

| 対象                                                                                                                    | 改変内容                                                                                                                                  | 追従時の確認                                                                                                                                                                                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/views/issue/base.py`（6 箇所）<br>`app/views/issue/comment.py`（1 箇所）<br>`app/views/issue/version.py`（1 箇所） | GUEST の可視範囲を「作成者のみ」→「作成者 or 担当者」に拡張。判定は `plane/spindd_ext/guest_scope.py` に集約し、各所は 1 行の呼び出し置換 | **ここは GHSA-32c7-84jc-4w67 (WEB-8074) の修正箇所である。**<br>解決後に必ず両方のテストを通す:<br>`plane/tests/contract/app/test_issue_list_guest_scope_app.py`（upstream の CVE 回帰）<br>`plane/tests/contract/app/test_issue_guest_assignee_scope_spindd.py`（fork の拡張） |

改変の理由は Issue #12（EE 評価）と #13。Commercial Edition では Project Guest が
"view-only access to assigned work items" と定義されており、この拡張は
upstream の Commercial 版と同じ意味に揃えるものであって独自解釈ではない。

**判定ロジックを各所にインラインで書き戻さないこと。** `guest_scope.py` に集約してあるのは、
追従のたびに 8 箇所の条件式をレビューし直す羽目にならないようにするためである。

### 継ぎ目で足りない場合

継ぎ目は「画面の追加」と「データ取得」用で、**既存画面への差し込み用のものは無い**。
現場詳細画面に工事情報パネルを出すような改変は実コンポーネントを触ることになる（優先度 5）。

避けるには、**既存画面に差し込まず独立したページとして作る**。`extendedRoutes` に素直に乗るため
追従耐性が段違いに良い。既存画面への差し込みは、独立ページで代替できないと確認できてから行う。

### Django settings を上書きする（`common.py` を触らない）

`manage.py` / `wsgi.py` / `asgi.py` / `celery.py` はいずれも

```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.production")
```

としている。**`setdefault` なので環境変数が既にあればそちらが勝つ。**

したがって設定を変えたいときは `plane/settings/common.py` を改変せず、
**`apps/api/plane/settings/spindd.py`（新規ファイル）に追記**して
環境変数 `DJANGO_SETTINGS_MODULE=plane.settings.spindd` で有効化する。

```python
# apps/api/plane/settings/spindd.py
from .production import *  # noqa

ATTACHMENT_MIME_TYPES = [*ATTACHMENT_MIME_TYPES, "image/heic", "image/heif"]
```

優先度 1（環境変数）と 4（新規ファイル）の組み合わせで優先度 5 を回避できる。
ハードコードされたリストや定数を変えたくなったら、まずここで足せないか検討すること。

PoC のスタックは upstream のリリース済みイメージを使っており `spindd.py` を含まないため、
`poc/docker-compose.override.yml` がこのファイルをマウントして有効化する。
本番では自前イメージをビルドし、環境変数で指定する。

### まず i18n で足りるか確かめる

`packages/i18n/src/locales/ja` は 28 ファイルあり、en と完全同数（3,837 キー）で揃っている。
**用語の置換はコード差分ゼロで済む。** UI の改変に着手する前に、必ずこの見極めを行うこと。

実績: 作業項目→課題 / プロジェクト→現場 / サイクル→工程 / モジュール→工種 の 1,016 箇所を
値の置換だけで実現した（[`docs/spindd-glossary.md`](docs/spindd-glossary.md)）。

なお `sync:check` はキーの存在しか見ないため、**値が英語のまま残っていても 100% と報告する。**
ja には実際に 72 件の未翻訳値が残っていた（大半はプレースホルダや固有名詞だが、
`Cycles` `Modules` のような一般名詞も混ざっていた）。翻訳漏れは en/ja の値を突き合わせて検出する。

> ⚠️ このリポジトリは PUBLIC である。ロケールファイルもそのまま公開されるため、
> 顧客固有の名称や社内用語を i18n に入れてはいけない（§5 参照）。

---

## 4. Django マイグレーションの連番衝突を避ける

**このリポジトリで最も痛い地雷。**

`apps/api/plane/db/migrations/` は**単一アプリに連番 123 本**が並んでいる
（最新は `0122_alter_draftissue_assignees_...`）。

ここに独自モデルの `0123_xxx.py` を足すと、upstream も次のリリースで `0123_yyy.py` を追加してくる。
結果、追従のたびに Django が

```
Conflicting migrations detected; multiple leaf nodes in the migration graph
```

を出して起動しなくなる。しかもマイグレーションの適用履歴は DB に残るため、
**番号を振り直す解決は本番では効かない。**

### ルール

- ✅ 独自モデルは**別の Django アプリ**（例: `plane.spindd`）として作り、自前の `migrations/` を持たせる
- ✅ 既存テーブルに列を足したくなったら、`OneToOneField` / `ForeignKey` で繋いだ**別テーブルに寄せる**
- ❌ **`apps/api/plane/db/migrations/` にファイルを追加しない**
- ❌ Plane 側のモデルに `add_field` するマイグレーションを書かない

この禁止は `.github/workflows/spindd-fork-guard.yml` の CI で機械的に検査される。

---

## 5. AGPL と公開リポジトリの運用

このリポジトリは **PUBLIC** である。

### AGPL 上の義務

- **§13 の開示義務**は、公開 fork を維持していれば素直に満たせる。
  「AGPL だからカスタマイズできない」は誤りである。
- **§5(a)**: 改変したファイルには「**改変した旨と改変日**」を明記する。
  リポジトリを公開しているだけでは足りない。既存ファイルを改変する PR では必ず確認すること。
- **既存の著作権表示を消さない。**
  全 `.py` / `.ts` に `Copyright (c) 2023-present Plane Software, Inc.` と
  `SPDX-License-Identifier: AGPL-3.0-only` のヘッダがあり、`addlicense` と `COPYRIGHT.txt` で
  CI 強制されている（`.github/workflows/copyright-check.yml`）。fork 側でもこの運用を引き継ぐ。
- **商標は AGPL の対象外。**
  リブランドするなら「**ロゴと製品名は差し替えるが、著作権表示とライセンス表記は残す**」が正しい形。
  逆をやると両方の意味で誤る。
- 稼働中のアプリ内にソースへの導線を置き、**デプロイ済みコミットと公開コミットの一致を CI で保証する**。

### 公開リポジトリゆえの注意

- **ロケールファイルは公開される。** 顧客固有の名称・社内用語を入れない
- **Issue / PR も公開になる。** 顧客名や障害の詳細を含む議論は別の場所で行う
- **公開前に履歴全体を秘匿情報スキャンにかける。** fork は upstream の履歴も引き継ぐので、
  自社コミットだけ見ても足りない

### エディションの前提

- このリポジトリは **Community Edition (AGPL)**。`prime.plane.so` から入る Commercial Edition とは
  **別コードベース**である
- 有料プランへ上げるには先に Commercial への乗り換えが必要で、CE に積んだ改造は作り直しになりうる
- インポーター（Jira / Linear / Asana 等）は Cloud と Commercial 専用で **CE には含まれない**。
  既存データの移行は REST API を自作する
- CE の席数上限は公式説明が 4 通りに割れている
  （[makeplane/plane#9086](https://github.com/makeplane/plane/issues/9086)、未決着）。
  人数を根拠に採否を判断するなら Plane から書面で回答を得ること

---

## 6. コンフリクトを構造的に減らす

**差別化に関係しない修正は upstream へ PR を出す。**
取り込まれた分は恒久的にリベース対象から外れる。
バグ修正・i18n・アクセシビリティ改善が該当する。
upstream の `CONTRIBUTING.md` を見る限り CLA の要求は記載されていないので、上流化のハードルは低い。

---

## 7. チェックリスト

### 新機能を実装する前

- [ ] §3 の表を上から検討し、より上位の手段で済まないことを確認したか
- [ ] 独自モデルを `plane.db` ではなく別アプリに隔離したか（§4）
- [ ] 用語の変更を i18n ロケールで賄えるか検証したか（§3）

### 既存ファイルを改変する PR

- [ ] より上位の手段が使えない理由を PR に書いたか
- [ ] 改変明記（AGPL §5(a)）を入れたか
- [ ] 既存の著作権ヘッダを保持しているか

### upstream 追従の PR

- [ ] 基準がリリースタグか（`preview` / RC タグではないか）
- [ ] タグを飛ばしていないか
- [ ] `.github/PULL_REQUEST_TEMPLATE/upstream-sync.md` を使ったか
