/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * spin-dd fork addition (2026-08-10): this file does not exist upstream.
 *
 * React Router は appDirectory（apps/web/app）外のモジュールを直接ルートに
 * できないため、ここに薄いラッパーだけを置き、実装は @plane/spindd に持つ。
 * 新規ファイルなので upstream とコンフリクトしない。
 */

export { ConstructionLedgerPage as default } from "@plane/spindd";
