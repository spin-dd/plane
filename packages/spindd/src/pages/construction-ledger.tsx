/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * spin-dd fork addition (2026-08-10): this file does not exist upstream.
 */

import { useState } from "react";
import { useParams } from "react-router";
import useSWR from "swr";
import { API_BASE_URL } from "@plane/constants";
import { ConstructionForm } from "../components/construction-form";
import { ConstructionService } from "../services/construction.service";
import type { TConstructionProject, TConstructionProjectPayload } from "../services/construction.service";

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
 * Plane の現場（Project）に紐づく工事情報を一覧・登録・編集する独自ページ。
 * 既存画面に差し込むのではなく独立ページにしているのは、`extendedRoutes` の
 * 継ぎ目に素直に乗せて upstream 追従のコンフリクトを避けるためである
 * （CONTRIBUTING.spindd.md §3）。
 */
export default function ConstructionLedgerPage() {
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();

  const [editing, setEditing] = useState<TConstructionProject | "new" | null>(null);

  const ledgerKey = slug ? `SPINDD_CONSTRUCTION_LEDGER_${slug}` : null;
  const { data, error, isLoading, mutate } = useSWR(ledgerKey, slug ? () => constructionService.ledger(slug) : null, {
    revalidateOnFocus: false,
  });

  // 未登録の現場は「登録」を開くときにしか使わないので、それまで取りに行かない。
  const { data: unregistered, mutate: mutateUnregistered } = useSWR(
    slug && editing !== null ? `SPINDD_CONSTRUCTION_UNREGISTERED_${slug}` : null,
    slug ? () => constructionService.unregisteredProjects(slug) : null,
    { revalidateOnFocus: false }
  );

  if (isLoading) {
    return <div className="p-6 text-13 text-tertiary">読み込み中…</div>;
  }

  if (error) {
    // AxiosError をそのまま JSON 化すると toJSON() が config（URL・ヘッダ・パラメータ）
    // まで含めるため、画面にはステータスと概要だけを出す。
    const status = (error as { response?: { status?: number } })?.response?.status;
    return (
      <div className="p-6">
        <p className="text-13 text-danger-primary">
          工事台帳を取得できませんでした。{status ? `（HTTP ${status}）` : ""}
        </p>
        <p className="mt-1 text-11 text-tertiary">
          この現場に参加しているか、工事情報が登録されているかを確認してください。
        </p>
      </div>
    );
  }

  const rows = data?.results ?? [];
  const editableIds = data?.editable_project_ids ?? [];
  // 権限はサーバ側が強制する。ここは UI の出し分けだけ。
  const canEdit = (row: TConstructionProject) => editableIds === "all" || editableIds.includes(row.project);
  const canCreate = editableIds === "all" || editableIds.length > 0;

  const handleSubmit = async (payload: TConstructionProjectPayload) => {
    if (!slug) return;
    if (editing === "new") {
      await constructionService.create(slug, payload);
    } else if (editing) {
      await constructionService.update(slug, editing.id, payload);
    }
    setEditing(null);
    await Promise.all([mutate(), mutateUnregistered()]);
  };

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <div className="flex flex-shrink-0 items-baseline justify-between gap-4 border-b border-subtle px-6 py-4">
        <h1 className="text-16 font-semibold text-primary">工事台帳</h1>
        <div className="flex items-center gap-3">
          <p className="text-13 text-tertiary">
            {data?.count ?? 0} 件{data?.truncated ? `（${rows.length} 件を表示）` : ""} / 請負金額合計{" "}
            {yen(data?.total_contract_amount ?? 0)}
          </p>
          {canCreate ? (
            <button
              type="button"
              onClick={() => setEditing("new")}
              className="rounded-md bg-layer-2 px-3 py-1.5 text-13 font-medium text-primary"
            >
              工事情報を登録
            </button>
          ) : null}
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="p-6 text-13 text-tertiary">
          工事情報が登録されている現場がありません。
          {canCreate ? "「工事情報を登録」から追加してください。" : ""}
        </div>
      ) : (
        <div className="flex-grow overflow-auto">
          <table className="w-full min-w-[1180px] border-collapse text-13">
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
                <th className="px-4 py-2 whitespace-nowrap" />
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
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    {canEdit(row) ? (
                      <button
                        type="button"
                        onClick={() => setEditing(row)}
                        className="text-11 text-tertiary underline underline-offset-2"
                      >
                        編集
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing !== null ? (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 p-4">
          <div className="shadow-lg w-full max-w-3xl rounded-lg bg-surface-1">
            <ConstructionForm
              initial={editing === "new" ? undefined : editing}
              unregistered={unregistered?.results ?? []}
              onSubmit={handleSubmit}
              onCancel={() => setEditing(null)}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
