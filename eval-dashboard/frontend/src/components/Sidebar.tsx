import { useEffect } from "react";
import {
  useContests,
  useLectures,
  useSemesters,
  useYears,
} from "../api/hooks";

type Props = {
  year: number | null;
  semester: number | null;
  lectureId: number | null;
  contestId: number | null;
  onChange: (s: {
    year?: number | null;
    semester?: number | null;
    lectureId?: number | null;
    contestId?: number | null;
  }) => void;
};

export function Sidebar({ year, semester, lectureId, contestId, onChange }: Props) {
  const years = useYears();
  const semesters = useSemesters(year);
  const lectures = useLectures(year, semester);
  const contests = useContests(lectureId);

  // Reset downstream when upstream changes.
  useEffect(() => { onChange({ semester: null, lectureId: null, contestId: null }); }, [year]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { onChange({ lectureId: null, contestId: null }); }, [semester]);                // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { onChange({ contestId: null }); }, [lectureId]);                                // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <aside className="w-72 shrink-0 border-r border-slate-200 bg-white p-4 flex flex-col gap-4">
      <h1 className="text-lg font-semibold tracking-tight">eval-dashboard</h1>

      <Field label="년도">
        <Select
          value={year ?? ""}
          options={(years.data ?? []).map((y) => ({ value: y, label: String(y) }))}
          loading={years.isLoading}
          placeholder="선택"
          onChange={(v) => onChange({ year: v == null ? null : Number(v) })}
        />
      </Field>

      <Field label="학기">
        <Select
          value={semester ?? ""}
          options={(semesters.data ?? []).map((s) => ({ value: s, label: `${s}학기` }))}
          disabled={year == null}
          loading={semesters.isLoading}
          placeholder={year == null ? "년도 먼저" : "선택"}
          onChange={(v) => onChange({ semester: v == null ? null : Number(v) })}
        />
      </Field>

      <Field label="과목">
        <Select
          value={lectureId ?? ""}
          options={(lectures.data ?? []).map((l) => ({ value: l.id, label: l.title }))}
          disabled={semester == null}
          loading={lectures.isLoading}
          placeholder={semester == null ? "학기 먼저" : "선택"}
          onChange={(v) => onChange({ lectureId: v == null ? null : Number(v) })}
        />
      </Field>

      <Field label="과제·실습·시험">
        <Select
          value={contestId ?? ""}
          options={(contests.data ?? []).map((c) => ({
            value: c.id,
            label: `[${c.lecture_contest_type || "?"}] ${c.title}`,
          }))}
          disabled={lectureId == null}
          loading={contests.isLoading}
          placeholder={lectureId == null ? "과목 먼저" : "선택"}
          onChange={(v) => onChange({ contestId: v == null ? null : Number(v) })}
        />
      </Field>
    </aside>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      {children}
    </label>
  );
}

function Select({
  value, options, onChange, disabled, loading, placeholder,
}: {
  value: number | string;
  options: { value: number; label: string }[];
  onChange: (v: number | null) => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
}) {
  return (
    <select
      className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 disabled:bg-slate-100 disabled:text-slate-400"
      value={value === null ? "" : String(value)}
      disabled={!!disabled || loading}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
    >
      <option value="">{loading ? "loading..." : placeholder ?? "선택"}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}
