/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * spin-dd fork addition (2026-08-10): this file does not exist upstream.
 */

import { layout, route } from "@react-router/dev/routes";
import type { RouteConfigEntry } from "@react-router/dev/routes";

/**
 * fork が追加する画面のルート定義。
 *
 * `apps/web/app/routes/extended.ts`（upstream の空スタブ）から re-export される。
 * スタブ側には 1 行しか書かないので、upstream 追従時のコンフリクト面積が
 * 「機能の大きさ」ではなく「継ぎ目の数」に収まる。
 *
 * ファイルパスは `apps/web/app/` からの相対で解決される。React Router が
 * appDirectory 外のモジュールを直接ルートにできないため、`app/spindd/` 配下に
 * 薄いラッパーを置き、実装はこのパッケージから import している。
 *
 * レイアウトの入れ子は core と同じファイルを指定している。`mergeRoutes` が
 * `file` をキーに deep merge するため、これでワークスペースのサイドバー配下に
 * 差し込まれる（`apps/web/app/routes/helper.ts`）。
 */
export const extendedRoutes: RouteConfigEntry[] = [
  layout("./(all)/layout.tsx", [
    layout("./(all)/[workspaceSlug]/layout.tsx", [
      layout("./(all)/[workspaceSlug]/(projects)/layout.tsx", [
        route(":workspaceSlug/construction-ledger", "./spindd/construction-ledger/page.tsx"),
      ]),
    ]),
  ]),
];
