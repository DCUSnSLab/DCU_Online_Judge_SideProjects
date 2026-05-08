import { useScoreboard } from "../api/hooks";
import type { Problem, ScoreboardCell } from "../lib/types";
import { colorForResult, colorForScore } from "../lib/format";

type Selection =
  | { kind: "none" }
  | { kind: "row"; userId: number }
  | { kind: "col"; problemId: number }
  | { kind: "cell"; userId: number; problemId: number };

type Props = {
  contestId: number | null;
  selection: Selection;
  onSelect: (sel: Selection) => void;
};

export function Scoreboard({ contestId, selection, onSelect }: Props) {
  const { data, isLoading, error } = useScoreboard(contestId);

  if (contestId == null) return <Empty>좌측에서 과제를 선택하세요.</Empty>;
  if (isLoading) return <Empty>스코어보드 불러오는 중...</Empty>;
  if (error) return <Empty>오류: {(error as Error).message}</Empty>;
  if (!data) return null;

  const problems = data.problems;
  const isRow = (uid: number) =>
    selection.kind === "row" && selection.userId === uid;
  const isCol = (pid: number) =>
    selection.kind === "col" && selection.problemId === pid;
  const isCell = (uid: number, pid: number) =>
    selection.kind === "cell" && selection.userId === uid && selection.problemId === pid;

  return (
    <div className="overflow-auto">
      <div className="px-4 py-3 border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="flex items-baseline gap-3 flex-wrap">
          <span className="font-semibold">{data.lecture.title}</span>
          <span className="text-slate-400">·</span>
          <span className="text-slate-700">{data.contest.title}</span>
          <span className="text-slate-400 text-xs ml-auto">
            학생 {data.students.length} · 문제 {problems.length} · 정성평가 {data.n_evaluated_pairs}/{data.n_total_pairs}
          </span>
        </div>
      </div>

      <table className="w-full text-sm border-separate border-spacing-0">
        <thead className="sticky top-12 bg-slate-50 z-10">
          <tr>
            <th className="text-left px-3 py-2 border-b border-slate-200 sticky left-0 bg-slate-50 z-20">학생</th>
            {problems.map((p) => (
              <th
                key={p.id}
                onClick={() => onSelect({ kind: "col", problemId: p.id })}
                className={
                  "text-center px-2 py-2 border-b border-slate-200 cursor-pointer hover:bg-slate-100 " +
                  (isCol(p.id) ? "bg-blue-50" : "")
                }
                title={p.title}
              >
                <div className="font-semibold">{p.label}</div>
                <div className="text-[10px] text-slate-500">{p.total_score}점</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.students.map((row) => (
            <tr key={row.user_id} className={isRow(row.user_id) ? "bg-blue-50" : ""}>
              <td
                onClick={() => onSelect({ kind: "row", userId: row.user_id })}
                className={
                  "px-3 py-1.5 border-b border-slate-100 sticky left-0 bg-white cursor-pointer hover:bg-slate-50 " +
                  (isRow(row.user_id) ? "bg-blue-50" : "")
                }
              >
                <div className="font-medium">{row.username}</div>
                {row.realname && <div className="text-[10px] text-slate-500">{row.realname}</div>}
              </td>
              {problems.map((p) => (
                <Cell
                  key={p.id}
                  problem={p}
                  cell={row.by_problem[p.label]}
                  selected={isCell(row.user_id, p.id)}
                  onClick={() =>
                    onSelect({ kind: "cell", userId: row.user_id, problemId: p.id })
                  }
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Cell({
  problem, cell, selected, onClick,
}: {
  problem: Problem;
  cell: ScoreboardCell | undefined;
  selected: boolean;
  onClick: () => void;
}) {
  const tc = cell?.testcase;
  const qual = cell?.qualitative;
  const scoreColor = colorForScore(tc?.score ?? null, problem.total_score);
  return (
    <td
      onClick={onClick}
      className={
        "border-b border-slate-100 cursor-pointer text-center px-1 py-1 align-middle " +
        (selected ? "ring-2 ring-blue-500 ring-inset" : "hover:ring-1 hover:ring-slate-300 hover:ring-inset")
      }
    >
      <div className={`relative rounded text-xs font-medium px-2 py-1 ${scoreColor}`}>
        <div className="flex items-center justify-center gap-1">
          {tc ? (
            <>
              <span className={`inline-block rounded px-1 text-[9px] ${colorForResult(tc.result_label)}`}>
                {tc.result_label}
              </span>
              <span>{tc.score ?? "-"}</span>
            </>
          ) : (
            <span className="text-slate-400">·</span>
          )}
        </div>
        {qual && (
          <div className="absolute -top-1 -right-1 flex gap-[2px]">
            <span
              className="rounded-full bg-blue-600 text-white text-[8px] px-1 leading-tight"
              title={`정성 overall=${qual.overall} sps=${qual.suggested_partial_score}`}
            >
              {qual.overall ?? "?"}
            </span>
            {qual.ai_likelihood_score != null && (
              <span
                className={
                  "rounded-full text-white text-[8px] px-1 leading-tight " +
                  (qual.ai_likelihood_score >= 70
                    ? "bg-rose-600"
                    : qual.ai_likelihood_score >= 40
                    ? "bg-amber-500"
                    : "bg-slate-500")
                }
                title={`AI 가능성 ${qual.ai_likelihood_score}/${qual.ai_confidence}`}
              >
                AI{qual.ai_likelihood_score}
              </span>
            )}
          </div>
        )}
      </div>
    </td>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-center h-full text-slate-400">{children}</div>
  );
}
