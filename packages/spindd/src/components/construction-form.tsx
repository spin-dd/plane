/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * spin-dd fork addition (2026-08-11): this file does not exist upstream.
 */

import { useState } from "react";
import type { ChangeEvent, FormEvent, ReactNode } from "react";
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

const CONTROL = "w-full rounded-md border border-subtle bg-surface-1 px-2.5 py-1.5 text-13 outline-none";
const LABEL = "mb-1 block text-11 text-tertiary";

/** フォームの入力値。すべて文字列で保持し、送信時に型を戻す。 */
type FormState = {
  projectId: string;
  contractNumber: string;
  officialName: string;
  clientName: string;
  siteAddress: string;
  buildingUse: string;
  structure: string;
  totalFloorArea: string;
  contractType: string;
  contractAmount: string;
  contractDate: string;
  start: string;
  end: string;
  actual: string;
  siteAgent: string;
  chiefEngineer: string;
  remarks: string;
};

/** FormState のキーから API のフィールド名へ。エラー表示の対応付けに使う。 */
const FIELD_TO_API: Record<keyof FormState, string> = {
  projectId: "project",
  contractNumber: "contract_number",
  officialName: "official_name",
  clientName: "client_name",
  siteAddress: "site_address",
  buildingUse: "building_use",
  structure: "structure",
  totalFloorArea: "total_floor_area",
  contractType: "contract_type",
  contractAmount: "contract_amount",
  contractDate: "contract_date",
  start: "construction_start",
  end: "construction_end",
  actual: "actual_completion",
  siteAgent: "site_agent",
  chiefEngineer: "chief_engineer",
  remarks: "remarks",
};

const initialState = (initial: TConstructionProject | undefined, unregistered: TUnregisteredProject[]): FormState => ({
  projectId: initial?.project ?? unregistered[0]?.id ?? "",
  contractNumber: initial?.contract_number ?? "",
  officialName: initial?.official_name ?? "",
  clientName: initial?.client_name ?? "",
  siteAddress: initial?.site_address ?? "",
  buildingUse: initial?.building_use ?? "",
  structure: initial?.structure ?? "",
  totalFloorArea: initial?.total_floor_area ?? "",
  contractType: initial?.contract_type ?? "lump_sum",
  contractAmount:
    initial?.contract_amount === null || initial?.contract_amount === undefined ? "" : String(initial.contract_amount),
  contractDate: initial?.contract_date ?? "",
  start: initial?.construction_start ?? "",
  end: initial?.construction_end ?? "",
  actual: initial?.actual_completion ?? "",
  siteAgent: initial?.site_agent ?? "",
  chiefEngineer: initial?.chief_engineer ?? "",
  remarks: initial?.remarks ?? "",
});

/** 数値入力を整数に落とす。空文字は null（未入力）として送る。 */
const toIntOrNull = (value: string): number | null => {
  const digits = value.replace(/[^\d-]/g, "");
  if (digits === "" || digits === "-") return null;
  const parsed = Number.parseInt(digits, 10);
  return Number.isNaN(parsed) ? null : parsed;
};

/** 日付入力を YYYY-MM-DD か null に落とす。 */
const toDateOrNull = (value: string): string | null => (value === "" ? null : value);

type FieldErrors = Record<string, string[]>;

/** ラベル・入力・補助テキスト・エラーの並びを 1 箇所に集約する。 */
function Field(props: {
  id: string;
  label: string;
  required?: boolean;
  errors?: string[];
  hint?: ReactNode;
  span2?: boolean;
  children: ReactNode;
}) {
  const { id, label, required, errors, hint, span2, children } = props;
  return (
    <div className={span2 ? "sm:col-span-2" : undefined}>
      <label className={LABEL} id={`${id}-label`} htmlFor={id}>
        {label}
        {required ? <span className="text-danger-primary"> *</span> : null}
      </label>
      {children}
      {hint ? <p className="mt-1 text-11 text-tertiary">{hint}</p> : null}
      {errors ? <p className="mt-1 text-11 text-danger-primary">{errors.join(" ")}</p> : null}
    </div>
  );
}

/**
 * 現場の選択。
 *
 * 編集時と候補ゼロ件のときは control を出さないので、見出しは span にする
 * （存在しない control を指す label を作らない）。
 */
function ProjectPicker(props: {
  isEdit: boolean;
  initial?: TConstructionProject;
  unregistered: TUnregisteredProject[];
  value: string;
  onChange: (event: ChangeEvent<HTMLSelectElement>) => void;
  errors?: string[];
}) {
  const { isEdit, initial, unregistered, value, onChange, errors } = props;
  const hasControl = !isEdit && unregistered.length > 0;

  return (
    <div className="sm:col-span-2">
      {hasControl ? (
        <label className={LABEL} htmlFor="spindd-project">
          現場
        </label>
      ) : (
        <span className={LABEL}>現場</span>
      )}

      {isEdit && initial ? (
        <p className="text-13 text-secondary">
          {initial.project_identifier} {initial.project_name}
          <span className="ml-2 text-11 text-tertiary">（登録後は変更できません）</span>
        </p>
      ) : unregistered.length === 0 ? (
        <p className="text-13 text-tertiary">工事情報が未登録の現場がありません。先に現場を作成してください。</p>
      ) : (
        <select id="spindd-project" className={CONTROL} value={value} onChange={onChange}>
          {unregistered.map((p) => (
            <option key={p.id} value={p.id}>
              {p.identifier} {p.name}
            </option>
          ))}
        </select>
      )}

      {errors ? <p className="mt-1 text-11 text-danger-primary">{errors.join(" ")}</p> : null}
    </div>
  );
}

type Props = {
  /** 編集対象。未指定なら新規登録。 */
  initial?: TConstructionProject;
  /** 新規登録時に選べる現場（工事情報が未登録のもの）。 */
  unregistered: TUnregisteredProject[];
  onSubmit: (payload: TConstructionProjectPayload) => Promise<void>;
  onCancel: () => void;
};

/**
 * 工事情報の登録・編集フォーム。
 *
 * 現場（project）は**作成時のみ**指定できる。作成後に付け替えられると
 * 工事番号や請負金額を他テナントの現場へ移送できてしまうため、
 * サーバ側でも read-only にしている（#11 のレビュー指摘）。
 */
export function ConstructionForm({ initial, unregistered, onSubmit, onCancel }: Props) {
  const isEdit = initial !== undefined;

  // フィールドごとに useState を並べず 1 つに畳んでいる。
  // 初期値の組み立ても initialState() の 1 箇所に収まる。
  const [form, setForm] = useState<FormState>(() => initialState(initial, unregistered));
  const set =
    (key: keyof FormState) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setErrors({});

    const payload: TConstructionProjectPayload = {
      contract_number: form.contractNumber.trim(),
      official_name: form.officialName.trim(),
      client_name: form.clientName.trim(),
      site_address: form.siteAddress.trim(),
      building_use: form.buildingUse.trim(),
      structure: form.structure.trim(),
      total_floor_area: form.totalFloorArea === "" ? null : form.totalFloorArea,
      contract_type: form.contractType as TContractType,
      contract_amount: toIntOrNull(form.contractAmount),
      contract_date: toDateOrNull(form.contractDate),
      construction_start: toDateOrNull(form.start),
      construction_end: toDateOrNull(form.end),
      actual_completion: toDateOrNull(form.actual),
      site_agent: form.siteAgent.trim(),
      chief_engineer: form.chiefEngineer.trim(),
      remarks: form.remarks.trim(),
    };
    // 作成時のみ現場を送る。編集時に送るとサーバ側で read-only として無視される。
    if (!isEdit) payload.project = form.projectId;

    try {
      await onSubmit(payload);
    } catch (error) {
      // DRF は {field: ["message"]} 形式で返す。表示できる形だけ拾う。
      const data = (error as { response?: { data?: unknown } })?.response?.data;
      if (data && typeof data === "object") {
        const normalized: FieldErrors = {};
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

  /** 単純なテキスト / 日付入力。16 個の繰り返しを 1 行に畳む。 */
  const text = (
    key: keyof FormState,
    labelText: string,
    opts: {
      type?: string;
      placeholder?: string;
      hint?: ReactNode;
      span2?: boolean;
      required?: boolean;
      numeric?: boolean;
    } = {}
  ) => {
    const id = `spindd-${key}`;
    return (
      <Field
        id={id}
        label={labelText}
        required={opts.required}
        errors={errors[FIELD_TO_API[key]]}
        hint={opts.hint}
        span2={opts.span2}
      >
        <input
          id={id}
          aria-labelledby={`${id}-label`}
          type={opts.type}
          className={CONTROL}
          value={form[key]}
          onChange={set(key)}
          placeholder={opts.placeholder}
          inputMode={opts.numeric ? "numeric" : undefined}
        />
      </Field>
    );
  };

  const canSubmit = !submitting && form.contractNumber.trim() !== "" && (isEdit || form.projectId !== "");
  const amount = toIntOrNull(form.contractAmount);
  const amountPreview = amount === null ? "未入力" : `${amount.toLocaleString("ja-JP")} 円`;

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
          <ProjectPicker
            isEdit={isEdit}
            initial={initial}
            unregistered={unregistered}
            value={form.projectId}
            onChange={set("projectId")}
            errors={errors.project}
          />

          {text("contractNumber", "工事番号", { placeholder: "26-A-0147", required: true })}
          {text("clientName", "発注者")}
          {text("officialName", "工事名称", { span2: true })}
          {text("siteAddress", "工事場所", { span2: true })}
          {text("buildingUse", "用途")}
          {text("structure", "構造・規模", { placeholder: "S造 地下1階 地上8階" })}
          {text("totalFloorArea", "延床面積（m²）", { placeholder: "18450.00" })}

          <Field id="spindd-contractType" label="契約形態" errors={errors.contract_type}>
            <select
              id="spindd-contractType"
              aria-labelledby="spindd-contractType-label"
              className={CONTROL}
              value={form.contractType}
              onChange={set("contractType")}
            >
              {CONTRACT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>

          {text("contractAmount", "請負金額（円）", {
            placeholder: "4820000000",
            hint: amountPreview,
            numeric: true,
          })}
          {text("contractDate", "契約日", { type: "date" })}
          {text("start", "着工日", { type: "date" })}
          {text("end", "竣工予定日", { type: "date" })}
          {text("actual", "実竣工日", { type: "date", hint: "入力すると台帳で「竣工」として扱われます。" })}
          {text("siteAgent", "現場代理人")}
          {text("chiefEngineer", "監理技術者・主任技術者")}

          <Field id="spindd-remarks" label="備考" span2 errors={errors.remarks}>
            <textarea
              id="spindd-remarks"
              aria-labelledby="spindd-remarks-label"
              className={`${CONTROL} min-h-[72px]`}
              value={form.remarks}
              onChange={set("remarks")}
            />
          </Field>
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
