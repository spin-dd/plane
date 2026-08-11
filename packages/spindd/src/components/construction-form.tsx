/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * spin-dd fork addition (2026-08-11): this file does not exist upstream.
 */

import { useState } from "react";
import type { FormEvent } from "react";
import type {
  TConstructionProject,
  TConstructionProjectPayload,
  TContractType,
  TUnregisteredProject,
} from "../services/construction.service";

const CONTRACT_TYPES: { value: TContractType; label: string }[] = [
  { value: "lump_sum", label: "総価請負" },
  { value: "unit_price", label: "単価契約" },
  { value: "cost_plus_fee", label: "実費精算" },
];

type Props = {
  /** 編集対象。未指定なら新規登録。 */
  initial?: TConstructionProject;
  /** 新規登録時に選べる現場（工事情報が未登録のもの）。 */
  unregistered: TUnregisteredProject[];
  onSubmit: (payload: TConstructionProjectPayload) => Promise<void>;
  onCancel: () => void;
};

const field = "w-full rounded-md border border-subtle bg-surface-1 px-2.5 py-1.5 text-13 outline-none";
const label = "mb-1 block text-11 text-tertiary";

/** 数値入力を整数に落とす。空文字は null（未入力）として送る。 */
const toIntOrNull = (value: string): number | null => {
  const digits = value.replace(/[^\d-]/g, "");
  if (digits === "" || digits === "-") return null;
  const parsed = Number.parseInt(digits, 10);
  return Number.isNaN(parsed) ? null : parsed;
};

/** 日付入力を YYYY-MM-DD か null に落とす。 */
const toDateOrNull = (value: string): string | null => (value === "" ? null : value);

/**
 * 工事情報の登録・編集フォーム。
 *
 * 現場（project）は**作成時のみ**指定できる。作成後に付け替えられると
 * 工事番号や請負金額を他テナントの現場へ移送できてしまうため、
 * サーバ側でも read-only にしている（#11 のレビュー指摘）。
 */
export function ConstructionForm({ initial, unregistered, onSubmit, onCancel }: Props) {
  const isEdit = initial !== undefined;

  const [projectId, setProjectId] = useState(initial?.project ?? unregistered[0]?.id ?? "");
  const [contractNumber, setContractNumber] = useState(initial?.contract_number ?? "");
  const [officialName, setOfficialName] = useState(initial?.official_name ?? "");
  const [clientName, setClientName] = useState(initial?.client_name ?? "");
  const [siteAddress, setSiteAddress] = useState(initial?.site_address ?? "");
  const [buildingUse, setBuildingUse] = useState(initial?.building_use ?? "");
  const [structure, setStructure] = useState(initial?.structure ?? "");
  const [totalFloorArea, setTotalFloorArea] = useState(initial?.total_floor_area ?? "");
  const [contractType, setContractType] = useState<TContractType>(initial?.contract_type ?? "lump_sum");
  const [contractAmount, setContractAmount] = useState(
    initial?.contract_amount === null || initial?.contract_amount === undefined ? "" : String(initial.contract_amount)
  );
  const [contractDate, setContractDate] = useState(initial?.contract_date ?? "");
  const [start, setStart] = useState(initial?.construction_start ?? "");
  const [end, setEnd] = useState(initial?.construction_end ?? "");
  const [actual, setActual] = useState(initial?.actual_completion ?? "");
  const [siteAgent, setSiteAgent] = useState(initial?.site_agent ?? "");
  const [chiefEngineer, setChiefEngineer] = useState(initial?.chief_engineer ?? "");
  const [remarks, setRemarks] = useState(initial?.remarks ?? "");

  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string[]>>({});

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setErrors({});

    const payload: TConstructionProjectPayload = {
      contract_number: contractNumber.trim(),
      official_name: officialName.trim(),
      client_name: clientName.trim(),
      site_address: siteAddress.trim(),
      building_use: buildingUse.trim(),
      structure: structure.trim(),
      total_floor_area: totalFloorArea === "" ? null : totalFloorArea,
      contract_type: contractType,
      contract_amount: toIntOrNull(contractAmount),
      contract_date: toDateOrNull(contractDate),
      construction_start: toDateOrNull(start),
      construction_end: toDateOrNull(end),
      actual_completion: toDateOrNull(actual),
      site_agent: siteAgent.trim(),
      chief_engineer: chiefEngineer.trim(),
      remarks: remarks.trim(),
    };
    // 作成時のみ現場を送る。編集時に送るとサーバ側で read-only として無視される。
    if (!isEdit) payload.project = projectId;

    try {
      await onSubmit(payload);
    } catch (error) {
      // DRF は {field: ["message"]} 形式で返す。表示できる形だけ拾う。
      const data = (error as { response?: { data?: unknown } })?.response?.data;
      if (data && typeof data === "object") {
        const normalized: Record<string, string[]> = {};
        for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
          normalized[key] = Array.isArray(value) ? value.map(String) : [String(value)];
        }
        setErrors(normalized);
      } else {
        setErrors({ detail: ["保存できませんでした。"] });
      }
    } finally {
      setSubmitting(false);
    }
  };

  const fieldError = (name: string) =>
    errors[name] ? <p className="mt-1 text-11 text-danger-primary">{errors[name].join(" ")}</p> : null;

  const canSubmit = !submitting && contractNumber.trim() !== "" && (isEdit || projectId !== "");

  return (
    <form onSubmit={handleSubmit} className="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden">
      <div className="flex-shrink-0 border-b border-subtle px-5 py-3">
        <h2 className="text-14 font-semibold text-primary">{isEdit ? "工事情報を編集" : "工事情報を登録"}</h2>
      </div>

      <div className="flex-grow overflow-y-auto px-5 py-4">
        {errors.detail ? (
          <p className="mb-3 rounded-md bg-layer-1 px-3 py-2 text-13 text-danger-primary">{errors.detail.join(" ")}</p>
        ) : null}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <span className={label}>現場</span>
            {isEdit ? (
              <p className="text-13 text-secondary">
                {initial.project_identifier} {initial.project_name}
                <span className="ml-2 text-11 text-tertiary">（登録後は変更できません）</span>
              </p>
            ) : unregistered.length === 0 ? (
              <p className="text-13 text-tertiary">工事情報が未登録の現場がありません。先に現場を作成してください。</p>
            ) : (
              <select className={field} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                {unregistered.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.identifier} {p.name}
                  </option>
                ))}
              </select>
            )}
            {fieldError("project")}
          </div>

          <div>
            <label className={label} htmlFor="spindd-contract-number">
              工事番号 <span className="text-danger-primary">*</span>
            </label>
            <input
              id="spindd-contract-number"
              className={field}
              value={contractNumber}
              onChange={(e) => setContractNumber(e.target.value)}
              placeholder="26-A-0147"
            />
            {fieldError("contract_number")}
          </div>

          <div>
            <label className={label} htmlFor="spindd-client">
              発注者
            </label>
            <input
              id="spindd-client"
              className={field}
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
            />
            {fieldError("client_name")}
          </div>

          <div className="sm:col-span-2">
            <label className={label} htmlFor="spindd-official-name">
              工事名称
            </label>
            <input
              id="spindd-official-name"
              className={field}
              value={officialName}
              onChange={(e) => setOfficialName(e.target.value)}
            />
            {fieldError("official_name")}
          </div>

          <div className="sm:col-span-2">
            <label className={label} htmlFor="spindd-address">
              工事場所
            </label>
            <input
              id="spindd-address"
              className={field}
              value={siteAddress}
              onChange={(e) => setSiteAddress(e.target.value)}
            />
            {fieldError("site_address")}
          </div>

          <div>
            <label className={label} htmlFor="spindd-use">
              用途
            </label>
            <input
              id="spindd-use"
              className={field}
              value={buildingUse}
              onChange={(e) => setBuildingUse(e.target.value)}
            />
          </div>

          <div>
            <label className={label} htmlFor="spindd-structure">
              構造・規模
            </label>
            <input
              id="spindd-structure"
              className={field}
              value={structure}
              onChange={(e) => setStructure(e.target.value)}
              placeholder="S造 地下1階 地上8階"
            />
          </div>

          <div>
            <label className={label} htmlFor="spindd-area">
              延床面積（m²）
            </label>
            <input
              id="spindd-area"
              className={field}
              value={totalFloorArea ?? ""}
              onChange={(e) => setTotalFloorArea(e.target.value)}
              inputMode="decimal"
              placeholder="18450.00"
            />
            {fieldError("total_floor_area")}
          </div>

          <div>
            <label className={label} htmlFor="spindd-contract-type">
              契約形態
            </label>
            <select
              id="spindd-contract-type"
              className={field}
              value={contractType}
              onChange={(e) => setContractType(e.target.value as TContractType)}
            >
              {CONTRACT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className={label} htmlFor="spindd-amount">
              請負金額（円）
            </label>
            <input
              id="spindd-amount"
              className={field}
              value={contractAmount}
              onChange={(e) => setContractAmount(e.target.value)}
              inputMode="numeric"
              placeholder="4820000000"
            />
            <p className="mt-1 text-11 text-tertiary">
              {toIntOrNull(contractAmount) === null
                ? "未入力"
                : `${toIntOrNull(contractAmount)?.toLocaleString("ja-JP")} 円`}
            </p>
            {fieldError("contract_amount")}
          </div>

          <div>
            <label className={label} htmlFor="spindd-contract-date">
              契約日
            </label>
            <input
              id="spindd-contract-date"
              type="date"
              className={field}
              value={contractDate ?? ""}
              onChange={(e) => setContractDate(e.target.value)}
            />
          </div>

          <div>
            <label className={label} htmlFor="spindd-start">
              着工日
            </label>
            <input
              id="spindd-start"
              type="date"
              className={field}
              value={start ?? ""}
              onChange={(e) => setStart(e.target.value)}
            />
          </div>

          <div>
            <label className={label} htmlFor="spindd-end">
              竣工予定日
            </label>
            <input
              id="spindd-end"
              type="date"
              className={field}
              value={end ?? ""}
              onChange={(e) => setEnd(e.target.value)}
            />
          </div>

          <div>
            <label className={label} htmlFor="spindd-actual">
              実竣工日
            </label>
            <input
              id="spindd-actual"
              type="date"
              className={field}
              value={actual ?? ""}
              onChange={(e) => setActual(e.target.value)}
            />
            <p className="mt-1 text-11 text-tertiary">入力すると台帳で「竣工」として扱われます。</p>
          </div>

          <div>
            <label className={label} htmlFor="spindd-agent">
              現場代理人
            </label>
            <input
              id="spindd-agent"
              className={field}
              value={siteAgent}
              onChange={(e) => setSiteAgent(e.target.value)}
            />
          </div>

          <div>
            <label className={label} htmlFor="spindd-engineer">
              監理技術者・主任技術者
            </label>
            <input
              id="spindd-engineer"
              className={field}
              value={chiefEngineer}
              onChange={(e) => setChiefEngineer(e.target.value)}
            />
          </div>

          <div className="sm:col-span-2">
            <label className={label} htmlFor="spindd-remarks">
              備考
            </label>
            <textarea
              id="spindd-remarks"
              className={`${field} min-h-[72px]`}
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="flex flex-shrink-0 items-center justify-end gap-2 border-t border-subtle px-5 py-3">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-subtle px-3 py-1.5 text-13 text-secondary"
        >
          キャンセル
        </button>
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-layer-2 px-3 py-1.5 text-13 font-medium text-primary disabled:opacity-50"
        >
          {submitting ? "保存中…" : "保存"}
        </button>
      </div>
    </form>
  );
}
