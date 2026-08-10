/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * spin-dd fork addition (2026-08-10): this package does not exist upstream.
 *
 * 建設業向けの独自機能をまとめたパッケージ。
 * upstream の空スタブ（継ぎ目）からはここを re-export するだけにして、
 * 実装は全部この中に置く。継ぎ目の一覧は CONTRIBUTING.spindd.md §3 を参照。
 */

export { default as ConstructionLedgerPage } from "./pages/construction-ledger";
export { ConstructionService } from "./services/construction.service";
export type { TConstructionLedger, TConstructionProject, TContractType } from "./services/construction.service";
