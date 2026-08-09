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

| 名前 | 役割 |
|---|---|
| `spindd` | **既定ブランチ。** 常に upstream のリリースタグを祖先に持つ |
| `preview` | upstream 追従用のミラー。**作業ブランチのベースには使わない** |
| `sync/vX.Y.Z` | upstream のリリースタグを取り込むための一時ブランチ |
| `feat/<issue>-<desc>` 等 | 作業ブランチ。`spindd` から切って `spindd` へ PR |

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

| 優先 | 手段 | 追従耐性 | 主な用途 |
|---|---|---|---|
| 1 | 環境変数・インスタンス設定 | ◎ 差分ゼロ | 認証、SMTP、ストレージ、`AMQP_URL` |
| 2 | i18n ロケール (`packages/i18n/src/locales/ja`) | ○ JSON の値のみ | 用語の置換 |
| 3 | テーマ・CSS の上書き | ○ | 見た目・ブランディング |
| 4 | 新規ファイル / 新規 Django アプリの追加 | ○ 衝突しない | 独自機能 |
| 5 | 既存ファイルの改変 | ✕ 毎回衝突 | **最終手段。** PR に理由を明記する |

### プラグイン seam は存在しない

`ce` / `ee` の分離は `packages/editor` にしか無く、`ee` は `ce` を re-export しているだけである。
**Plane は editor 以外に拡張ポイントを持たないので、独自機能の置き場所は自分で設計する必要がある。**

### まず i18n で足りるか確かめる

`packages/i18n/src/locales/ja` は 28 ファイルあり、en と完全同数（3,837 キー）で揃っている。
「課題」→「是正指示」のような**用語の置換はコード差分ゼロで済む**可能性がある。
UI の改変に着手する前に、必ずこの見極めを行うこと。

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
