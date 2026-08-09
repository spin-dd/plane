# CLAUDE.md

このリポジトリは [makeplane/plane](https://github.com/makeplane/plane) (Community Edition / AGPL-3.0) の
fork であり、日本の建設企業向け社内課題管理システムとしての利用可否を評価している。

**コードを書く前に [`CONTRIBUTING.spindd.md`](./CONTRIBUTING.spindd.md) を読むこと。**
ビルド・テスト・コードスタイルは upstream の [`AGENTS.md`](./AGENTS.md) に従う。

## 絶対に守るルール

1. **`apps/api/plane/db/migrations/` にマイグレーションを追加しない。**
   単一アプリに連番 123 本が並んでおり、`0123_xxx.py` を足すと upstream の `0123_yyy.py` と
   leaf node が衝突して Django が起動しなくなる。適用履歴が DB に残るため番号の振り直しは本番で効かない。
   独自モデルは**別 Django アプリ**（例 `plane.spindd`）に自前の `migrations/` を持たせて隔離する。
   既存テーブルへの列追加も禁止で、FK で繋いだ別テーブルに寄せる。

2. **upstream 追従はリリースタグ基準。`upstream/preview` も RC タグも基準にしない。**
   `git fetch upstream --tags` → `sync/vX.Y.Z` ブランチで `git merge vX.Y.Z`。
   タグを飛ばさず 1 リリースずつ。公開ブランチ（`spindd`）は rebase しない。

3. **改変は上から順に検討する。**
   環境変数 → i18n ロケール → CSS 上書き → **新規ファイル追加** → 既存ファイル改変（最終手段）。
   `packages/i18n/src/locales/ja` は en と完全同数（3,837 キー）で揃っているので、
   用語置換はコード差分ゼロで済む可能性が高い。まずそこを検証する。
   `ce`/`ee` の分離は `packages/editor` にしか無く、プラグイン seam は存在しない。

4. **upstream 由来のファイルを編集しない。**
   `AGENTS.md`、`CONTRIBUTING.md`、`.github/pull_request_template.md` などは触らない。
   fork 側の追加は新規ファイル（`CONTRIBUTING.spindd.md`、`CLAUDE.md`、
   `.github/workflows/spindd-*.yml`、`.github/PULL_REQUEST_TEMPLATE/`）に閉じる。

5. **このリポジトリは PUBLIC。**
   ロケールファイルも Issue / PR も公開される。顧客固有の名称・社内用語を書かない。
   既存ファイルを改変したら AGPL §5(a) の改変明記を入れ、既存の著作権ヘッダは消さない
   （`.py` / `.ts` は `copyright-check.yml` で CI 強制されている）。

## ブランチ

- `spindd` — 既定ブランチ。常に upstream のリリースタグを祖先に持つ（現在 `v1.4.1`）
- `preview` — upstream 追従用ミラー。作業ブランチのベースには使わない
- 作業ブランチは `spindd` から切り、`spindd` へ PR する

## 背景調査

Plane のセルフホスト構成・エディション差分・fork カスタマイズの一次情報:
<https://github.com/hdknr/blogs/pull/631>
