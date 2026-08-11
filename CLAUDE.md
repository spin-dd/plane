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
   用語置換は i18n の値だけで済む（実績 1,016 箇所）。まずそこを検証する。

4. **拡張の継ぎ目（空スタブ）を使う。実装は継ぎ目に書かない。**
   CE は空のスタブを置き EE が実装で置き換える設計になっている。本体が空のものが 7 箇所ある
   （`app/routes/extended.ts`、`use-workspace-issue-properties-extended.tsx` など。一覧は
   `CONTRIBUTING.spindd.md` §3）。実装は `packages/spindd` / `apps/api/plane/spindd_ext` に置き、
   継ぎ目には re-export の 1 行だけを書く。
   `ExtendedProjectSidebar` などは CE の実装本体で継ぎ目ではない。**エクスポートされた本体が
   空かどうか**で判断する。
   バックエンドは `ROOT_URLCONF` と `INSTALLED_APPS` を `settings/spindd.py` で差し替えられるので、
   **upstream を 1 行も触らずに拡張できる。**

5. **upstream 由来のファイルを編集しない（継ぎ目とロケールを除く）。**
   `AGENTS.md`、`CONTRIBUTING.md`、`.github/pull_request_template.md` などは触らない。
   fork 側のファイルは `CONTRIBUTING.spindd.md`、`CLAUDE.md`、`poc/`、`docs/spindd-*`、
   `packages/spindd/`、`apps/api/spindd_ext/`、`apps/api/plane/settings/spindd.py`、
   `.github/workflows/spindd-*.yml`、`.github/PULL_REQUEST_TEMPLATE/`。
   これらは `spindd-fork-guard.yml` の `fork_owned` に登録して警告対象から外す。

6. **このリポジトリは PUBLIC。**
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
