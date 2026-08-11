/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Modified by spin-dd on 2026-08-10 (AGPL-3.0 §5(a)):
 * upstream ではこのファイルは `extendedRoutes = []` の空スタブである。
 * fork のルート定義を @plane/spindd から re-export するだけに留めることで、
 * 追従時のコンフリクト面積をこの 1 行に閉じ込めている。
 */

export { extendedRoutes } from "@plane/spindd/routes";
