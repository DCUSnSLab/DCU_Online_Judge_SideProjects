import { useCellDetail, useScoreboard } from "../api/hooks";
import type { ScoreboardResponse } from "../lib/types";
import { colorForResult } from "../lib/format";

type Selection =
  | { kind: "none" }
  | { kind: "row"; userId: number }
  | { kind: "col"; problemId: number }
  | { kind: "cell"; userId: number; problemId: number };

type Props = {
  contestId: number | null;
  selection: Selection;
  onClose: () => void;
};

export function DetailPanel({ contestId, selection, onClose }: Props) {
  if (selection.kind === "none") return null;
  return (
    <aside className="w-[40rem] shrink-0 border-l border-slate-200 bg-white overflow-auto">
      <div className="sticky top-0 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <div className="text-sm text-slate-500">상세</div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700">✕</button>
      </div>
      <div className="p-4">
        {selection.kind === "row" && contestId != null && (
          <RowDetail contestId={contestId} userId={selection.userId} />
        )}
        {selection.kind === "col" && contestId != null && (
          <ColDetail contestId={contestId} problemId={selection.problemId} />
        )}
        {selection.kind === "cell" && contestId != null && (
          <CellDetail
            contestId={contestId}
            userId={selection.userId}
            problemId={selection.problemId}
          />
        )}
      </div>
    </aside>
  );
}

function RowDetail({ contestId, userId }: { contestId: number; userId: number }) {
  const { data } = useScoreboard(contestId);
  if (!data) return <Loading />;
  const row = data.students.find((s) => s.user_id === userId);
  if (!row) return <div>학생을 찾을 수 없음</div>;

  const totals = totalsForRow(data, userId);
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">{row.username}{row.realname ? ` · ${row.realname}` : ""}</h2>
      <div className="text-sm text-slate-500">전체 testcase 점수 합계: <span className="text-slate-900 font-medium">{totals.tc}/{totals.tcMax}</span></div>
      <table className="w-full text-sm">
        <thead className="text-slate-500 text-xs">
          <tr><th className="text-left">문제</th><th>결과</th><th>점수</th><th>정성</th><th>AI</th></tr>
        </thead>
        <tbody>
          {data.problems.map((p) => {
            const cell = row.by_problem[p.label];
            const tc = cell?.testcase;
            const q = cell?.qualitative;
            return (
              <tr key={p.id} className="border-t border-slate-100">
                <td className="py-1.5">{p.label}</td>
                <td className="text-center">
                  {tc?.result_label ? (
                    <span className={`text-[10px] rounded px-1.5 py-0.5 ${colorForResult(tc.result_label)}`}>{tc.result_label}</span>
                  ) : <span className="text-slate-400">-</span>}
                </td>
                <td className="text-center">{tc?.score ?? "-"}/{p.total_score}</td>
                <td className="text-center">{q?.overall ?? "-"}</td>
                <td className="text-center">{q?.ai_likelihood_score ?? "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function totalsForRow(data: ScoreboardResponse, uid: number) {
  const row = data.students.find((s) => s.user_id === uid);
  if (!row) return { tc: 0, tcMax: 0 };
  let tc = 0;
  let tcMax = 0;
  for (const p of data.problems) {
    tcMax += p.total_score;
    tc += row.by_problem[p.label]?.testcase?.score ?? 0;
  }
  return { tc, tcMax };
}

function ColDetail({ contestId, problemId }: { contestId: number; problemId: number }) {
  const { data } = useScoreboard(contestId);
  if (!data) return <Loading />;
  const problem = data.problems.find((p) => p.id === problemId);
  if (!problem) return <div>문제를 찾을 수 없음</div>;

  const rows = data.students.map((s) => {
    const cell = s.by_problem[problem.label];
    return {
      username: s.username,
      realname: s.realname,
      result: cell?.testcase?.result_label,
      score: cell?.testcase?.score,
      qualOverall: cell?.qualitative?.overall,
      ai: cell?.qualitative?.ai_likelihood_score,
    };
  });
  const submitted = rows.filter((r) => r.result != null);
  const acCount = submitted.filter((r) => r.result === "AC").length;
  const avgScore =
    submitted.length > 0
      ? Math.round(submitted.reduce((s, r) => s + (r.score ?? 0), 0) / submitted.length)
      : 0;

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">{problem.label} · {problem.title}</h2>
      <div className="text-xs text-slate-500">난이도 {problem.difficulty} · 배점 {problem.total_score}</div>
      <div className="text-sm text-slate-500">제출자 {submitted.length}/{rows.length} · AC {acCount} · 평균 점수 {avgScore}</div>
      <table className="w-full text-sm">
        <thead className="text-slate-500 text-xs">
          <tr><th className="text-left">학생</th><th>결과</th><th>점수</th><th>정성</th><th>AI</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.username} className="border-t border-slate-100">
              <td className="py-1.5">{r.username}{r.realname ? ` · ${r.realname}` : ""}</td>
              <td className="text-center">
                {r.result ? (
                  <span className={`text-[10px] rounded px-1.5 py-0.5 ${colorForResult(r.result)}`}>{r.result}</span>
                ) : <span className="text-slate-400">-</span>}
              </td>
              <td className="text-center">{r.score ?? "-"}/{problem.total_score}</td>
              <td className="text-center">{r.qualOverall ?? "-"}</td>
              <td className="text-center">{r.ai ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CellDetail({
  contestId, userId, problemId,
}: {
  contestId: number;
  userId: number;
  problemId: number;
}) {
  const { data, isLoading, error } = useCellDetail(contestId, userId, problemId);
  if (isLoading) return <Loading />;
  if (error) return <div className="text-rose-600 text-sm">오류: {(error as Error).message}</div>;
  if (!data) return null;

  const p = data.problem;
  const sub = data.submission;
  const q = data.qualitative;
  const ai = data.ai_usage_assessment;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{p.label} · {p.title}</h2>
        <div className="text-xs text-slate-500">난이도 {p.difficulty} · 배점 {p.total_score} · {p.time_limit}ms / {p.memory_limit}MB</div>
      </div>

      <Section title="자동 채점 결과">
        {sub ? (
          <div className="text-sm">
            <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] ${colorForResult(sub.result_label)}`}>{sub.result_label}</span>
            <span className="ml-2">점수 {(sub.statistic_info as any)?.score ?? "-"}/{p.total_score}</span>
            <span className="ml-2 text-slate-500">시간 {(sub.statistic_info as any)?.time_cost ?? "-"}ms</span>
            <span className="ml-2 text-slate-500">메모리 {(sub.statistic_info as any)?.memory_cost ?? "-"}KB</span>
            <span className="ml-2 text-slate-500">언어 {sub.language}</span>
          </div>
        ) : (
          <div className="text-sm text-slate-400">제출 없음</div>
        )}
      </Section>

      <Section title="정성 평가">
        {!q ? (
          <div className="text-sm text-slate-400">아직 평가되지 않음. 좌측 '정성평가' 버튼을 눌러주세요.</div>
        ) : (
          <div className="space-y-2 text-sm">
            <div>
              종합 <span className="font-semibold">{q.overall ?? "-"}/100</span> · 부분점수 제안 <span className="font-semibold">{q.suggested_partial_score ?? "-"}/{p.total_score}</span>
            </div>
            <table className="w-full text-xs">
              <thead className="text-slate-500"><tr><th className="text-left">축</th><th>점수</th><th className="text-left">평가</th><th className="text-left">개선</th></tr></thead>
              <tbody>
                {(["correctness", "algorithm", "readability", "problem_understanding"] as const).map((axis) => {
                  const c = q.comments?.[axis];
                  return (
                    <tr key={axis} className="border-t border-slate-100 align-top">
                      <td className="py-1 pr-2 whitespace-nowrap">{axis}</td>
                      <td className="text-center">{q.scores?.[axis] ?? "-"}</td>
                      <td className="py-1 pr-2 text-slate-700">{c?.assessment ?? "-"}</td>
                      <td className="py-1 text-slate-700">{c?.suggestion ?? "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {q.summary && <div className="text-xs text-slate-600 italic">{q.summary}</div>}
          </div>
        )}
      </Section>

      <Section title="AI 사용 가능성 — 참고용 · 점수 미반영">
        {!ai ? (
          <div className="text-sm text-slate-400">없음</div>
        ) : ai.error ? (
          <div className="text-sm text-rose-600">실패: {ai.error}</div>
        ) : (
          <div className="space-y-2 text-sm">
            <div>likelihood <span className="font-semibold">{ai.likelihood_score ?? "-"}/100</span> · confidence <span className="font-medium">{ai.confidence ?? "-"}</span></div>
            {ai.disclaimer && <div className="text-[11px] text-slate-500 italic">⚠ {ai.disclaimer}</div>}
            {ai.signals && ai.signals.length > 0 && (
              <div>
                <div className="text-xs text-slate-500 mt-1">신호</div>
                <ul className="list-disc pl-5 text-xs space-y-0.5">
                  {ai.signals.map((s, i) => (
                    <li key={i}><span className="text-slate-400">[{s.weight}]</span> <span className="text-slate-500">{s.category}</span>: {s.observation}</li>
                  ))}
                </ul>
              </div>
            )}
            {ai.counter_signals && ai.counter_signals.length > 0 && (
              <div>
                <div className="text-xs text-slate-500 mt-1">반대 신호</div>
                <ul className="list-disc pl-5 text-xs space-y-0.5">
                  {ai.counter_signals.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            )}
            {ai.summary && <div className="text-xs text-slate-700">{ai.summary}</div>}
          </div>
        )}
      </Section>

      <Section title={`학생 코드 ${sub ? `(${sub.language})` : ""}`}>
        {sub ? (
          <pre className="bg-slate-900 text-slate-100 text-xs p-3 rounded overflow-auto max-h-96 whitespace-pre"><code>{sub.code}</code></pre>
        ) : (
          <div className="text-sm text-slate-400">없음</div>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">{title}</h3>
      {children}
    </div>
  );
}

function Loading() {
  return <div className="text-sm text-slate-400">로딩 중...</div>;
}
