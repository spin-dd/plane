/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * spin-dd fork addition (2026-08-10): this file does not exist upstream.
 */

import { useParams } from "react-router";
import useSWR from "swr";
import { API_BASE_URL } from "@plane/constants";
import { ConstructionService } from "../services/construction.service";
import type { TConstructionProject } from "../services/construction.service";

const constructionService = new ConstructionService(API_BASE_URL);

const yen = (value: number | null) => (value === null ? "—" : `${value.toLocaleString("ja-JP")} 円`);

const area = (value: string | null) => (value === null ? "—" : `${Number(value).toLocaleString("ja-JP")} m²`);

const period = (row: TConstructionProject) => {
  const start = row.construction_start ?? "—";
  const end = row.actual_completion ?? row.construction_end ?? "—";
  return `${start} 〜 ${end}`;
};

/**
 * 工事台帳。
 *
 * Plane の現場（Project）に紐づく工事情報を一覧する独自ページ。
 * 既存画面に差し込むのではなく独立ページにしているのは、`extendedRoutes` の
 * 継ぎ目に素直に乗せて upstream 追従のコンフリクトを避けるためである
 * （CONTRIBUTING.spindd.md §3）。
 */
export default function ConstructionLedgerPage() {
  const { workspaceSlug } = useParams();

  const { data, error, isLoading } = useSWR(
    workspaceSlug ? `SPINDD_CONSTRUCTION_LEDGER_${workspaceSlug}` : null,
    workspaceSlug ? () => constructionService.ledger(workspaceSlug.toString()) : null,
    { revalidateOnFocus: false }
  );

  if (isLoading) {
    return <div className="p-6 text-13 text-tertiary">読み込み中…</div>;
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-danger-text text-13">工事台帳を取得できませんでした。</p>
        <pre className="mt-2 overflow-x-auto rounded-md bg-layer-1 p-3 text-11 text-tertiary">
          {JSON.stringify(error, null, 2)}
        </pre>
      </div>
    );
  }

  const rows = data?.results ?? [];

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <div className="flex flex-shrink-0 items-baseline justify-between border-b border-subtle px-6 py-4">
        <h1 className="text-16 font-semibold text-primary">工事台帳</h1>
        <p className="text-13 text-tertiary">
          {data?.count ?? 0} 件 / 請負金額合計 {yen(data?.total_contract_amount ?? 0)}
        </p>
      </div>

      {rows.length === 0 ? (
        <div className="p-6 text-13 text-tertiary">工事情報が登録されている現場がありません。</div>
      ) : (
        <div className="flex-grow overflow-auto">
          <table className="w-full min-w-[1100px] border-collapse text-13">
            <thead className="sticky top-0 bg-layer-1">
              <tr className="text-left text-tertiary">
                <th className="px-4 py-2 font-medium whitespace-nowrap">工事番号</th>
                <th className="px-4 py-2 font-medium whitespace-nowrap">現場</th>
                <th className="px-4 py-2 font-medium whitespace-nowrap">発注者</th>
                <th className="px-4 py-2 font-medium whitespace-nowrap">構造・規模</th>
                <th className="px-4 py-2 text-right font-medium whitespace-nowrap">延床面積</th>
                <th className="px-4 py-2 font-medium whitespace-nowrap">契約形態</th>
                <th className="px-4 py-2 text-right font-medium whitespace-nowrap">請負金額</th>
                <th className="px-4 py-2 font-medium whitespace-nowrap">工期</th>
                <th className="px-4 py-2 font-medium whitespace-nowrap">現場代理人</th>
                <th className="px-4 py-2 font-medium whitespace-nowrap">状態</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-subtle align-top">
                  <td className="px-4 py-2 font-medium whitespace-nowrap text-primary">{row.contract_number}</td>
                  <td className="px-4 py-2 text-secondary">
                    <span className="text-tertiary">{row.project_identifier}</span> {row.project_name}
                  </td>
                  <td className="px-4 py-2 text-secondary">{row.client_name || "—"}</td>
                  <td className="px-4 py-2 text-secondary">{row.structure || "—"}</td>
                  <td className="px-4 py-2 text-right whitespace-nowrap text-secondary">
                    {area(row.total_floor_area)}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap text-secondary">{row.contract_type_label}</td>
                  <td className="px-4 py-2 text-right whitespace-nowrap text-secondary">{yen(row.contract_amount)}</td>
                  <td className="px-4 py-2 whitespace-nowrap text-secondary">{period(row)}</td>
                  <td className="px-4 py-2 whitespace-nowrap text-secondary">{row.site_agent || "—"}</td>
                  <td className="px-4 py-2 whitespace-nowrap">
                    {row.is_completed ? (
                      <span className="rounded-full bg-layer-2 px-2 py-0.5 text-11 text-tertiary">竣工</span>
                    ) : (
                      <span className="rounded-full bg-layer-2 px-2 py-0.5 text-11 text-secondary">施工中</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
