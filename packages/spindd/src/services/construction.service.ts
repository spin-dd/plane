/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * spin-dd fork addition (2026-08-10): this file does not exist upstream.
 */

import type { AxiosInstance } from "axios";
import { create } from "axios";

export type TContractType = "lump_sum" | "unit_price" | "cost_plus_fee";

export type TConstructionProject = {
  id: number;
  project: string;
  project_name: string;
  project_identifier: string;
  contract_number: string;
  official_name: string;
  client_name: string;
  site_address: string;
  building_use: string;
  structure: string;
  total_floor_area: string | null;
  contract_type: TContractType;
  contract_type_label: string;
  contract_amount: number | null;
  contract_date: string | null;
  construction_start: string | null;
  construction_end: string | null;
  actual_completion: string | null;
  site_agent: string;
  chief_engineer: string;
  remarks: string;
  is_completed: boolean;
};

export type TConstructionLedger = {
  /** 可視範囲の総件数。`results` は `limit` で切り詰められることがある。 */
  count: number;
  /** `count` が `limit` を超えて切り詰められたか。 */
  truncated: boolean;
  /** 請負金額の合計。切り詰めの影響を受けないよう DB 側で集計している。 */
  total_contract_amount: number;
  /**
   * 編集できる現場の id。ワークスペース ADMIN なら `"all"`。
   * UI の出し分けにだけ使う。権限はサーバ側が強制する。
   */
  editable_project_ids: "all" | string[];
  results: TConstructionProject[];
};

/** 登録・更新で送るフィールド。`project` は作成時のみ受け付けられる。 */
export type TConstructionProjectPayload = Partial<
  Pick<
    TConstructionProject,
    | "contract_number"
    | "official_name"
    | "client_name"
    | "site_address"
    | "building_use"
    | "structure"
    | "total_floor_area"
    | "contract_type"
    | "contract_amount"
    | "contract_date"
    | "construction_start"
    | "construction_end"
    | "actual_completion"
    | "site_agent"
    | "chief_engineer"
    | "remarks"
  >
> & { project?: string };

export type TUnregisteredProject = { id: string; name: string; identifier: string };

/**
 * 工事台帳 API のクライアント。
 *
 * エンドポイントは spindd_ext（独自 Django アプリ）が /api/spindd/ 配下に提供する。
 *
 * upstream の `APIService`（`packages/services/src/api.service.ts`）を継承していないのは、
 * それが `@plane/services` の公開 export に含まれておらず、深いパス import も
 * exports マップで塞がれているためである。非公開の内部 API に寄りかかると
 * upstream 追従で黙って壊れるので、axios を直接使う自己完結の実装にしている。
 * `withCredentials: true` は Plane のセッション Cookie を送るために必要。
 */
export class ConstructionService {
  private readonly client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = create({ baseURL, withCredentials: true });
  }

  async ledger(workspaceSlug: string): Promise<TConstructionLedger> {
    const response = await this.client.get<TConstructionLedger>(
      `/api/spindd/workspaces/${workspaceSlug}/construction-ledger/`
    );
    return response.data;
  }

  async unregisteredProjects(workspaceSlug: string): Promise<{ count: number; results: TUnregisteredProject[] }> {
    const response = await this.client.get<{ count: number; results: TUnregisteredProject[] }>(
      `/api/spindd/workspaces/${workspaceSlug}/construction-projects/unregistered/`
    );
    return response.data;
  }

  /**
   * 新規登録。`project` は作成時のみ指定できる（作成後は付け替え不可）。
   *
   * CSRF トークンは不要。`BaseSessionAuthentication.enforce_csrf` が no-op で
   * REST API では CSRF を強制していないため、`withCredentials` だけで通る。
   */
  async create(workspaceSlug: string, payload: TConstructionProjectPayload): Promise<TConstructionProject> {
    const response = await this.client.post<TConstructionProject>(
      `/api/spindd/workspaces/${workspaceSlug}/construction-projects/`,
      payload
    );
    return response.data;
  }

  async update(workspaceSlug: string, id: number, payload: TConstructionProjectPayload): Promise<TConstructionProject> {
    const response = await this.client.patch<TConstructionProject>(
      `/api/spindd/workspaces/${workspaceSlug}/construction-projects/${id}/`,
      payload
    );
    return response.data;
  }
}
