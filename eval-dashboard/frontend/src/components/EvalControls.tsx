import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useEvalStatus, useStartEval } from "../api/hooks";

type Props = { contestId: number | null };

type Progress = {
  n: number;
  total: number;
  current?: string;
  stage?: string;
  done?: boolean;
  error?: string;
};

export function EvalControls({ contestId }: Props) {
  const status = useEvalStatus(contestId);
  const startMut = useStartEval(contestId);
  const qc = useQueryClient();
  const [progress, setProgress] = useState<Progress | null>(null);
  const esRef = useRef<EventSource | null>(null);

  // Auto-attach to running job on mount.
  useEffect(() => {
    if (!status.data?.running_job_id) return;
    attach(status.data.running_job_id);
    return () => detach();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status.data?.running_job_id]);

  const attach = (jobId: string) => {
    detach();
    const es = new EventSource(`/api/jobs/${jobId}/stream`);
    esRef.current = es;
    es.addEventListener("started", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setProgress({ n: 0, total: data.n_total ?? 0, stage: "시작" });
    });
    es.addEventListener("stage", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setProgress((p) => ({ ...(p ?? { n: 0, total: 0 }), stage: data.name, total: data.n_to_run ?? p?.total ?? 0 }));
    });
    es.addEventListener("progress", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setProgress({
        n: data.n,
        total: data.total,
        current: `${data.current_user}/${data.current_problem} (overall=${data.ev_overall})`,
      });
    });
    es.addEventListener("warn", (e) => {
      console.warn("eval-warn", (e as MessageEvent).data);
    });
    es.addEventListener("done", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setProgress((p) => ({ ...(p ?? { n: 0, total: 0 }), done: true, stage: `완료 (성공 ${data.n_evaluated} / 실패 ${data.n_failed})` }));
      qc.invalidateQueries({ queryKey: ["scoreboard", contestId] });
      qc.invalidateQueries({ queryKey: ["eval-status", contestId] });
      detach();
      // Auto-clear after a short delay so the user sees completion.
      setTimeout(() => setProgress(null), 4000);
    });
    es.addEventListener("error", (e) => {
      const data = JSON.parse((e as MessageEvent).data || "{}");
      setProgress({ n: 0, total: 0, error: data.message ?? "stream error" });
      detach();
    });
    es.onerror = () => {
      // Network-level. Don't show as fatal — server may be slow.
    };
  };

  const detach = () => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  };

  const start = async (force: boolean) => {
    if (contestId == null) return;
    setProgress({ n: 0, total: 0, stage: "요청 중..." });
    try {
      const res = await startMut.mutateAsync(force);
      attach(res.job_id);
    } catch (e) {
      setProgress({ n: 0, total: 0, error: (e as Error).message });
    }
  };

  if (contestId == null) return null;

  const running = !!progress && !progress.done && !progress.error;
  const pct = progress && progress.total > 0
    ? Math.round((progress.n / progress.total) * 100)
    : 0;

  return (
    <div className="border-t border-slate-200 p-4 space-y-2 bg-slate-50">
      <div className="text-xs text-slate-500">
        평가 캐시: {status.data?.n_evaluated ?? "-"}건 (마지막 실행 {status.data?.last_run_at ?? "없음"})
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => start(false)}
          disabled={running || startMut.isPending}
          className="flex-1 rounded bg-blue-600 text-white text-sm py-1.5 hover:bg-blue-700 disabled:bg-slate-300"
        >
          정성평가
        </button>
        <button
          onClick={() => start(true)}
          disabled={running || startMut.isPending}
          className="rounded border border-slate-300 text-slate-700 text-sm px-3 py-1.5 hover:bg-slate-100 disabled:text-slate-400"
        >
          재평가
        </button>
      </div>
      {progress && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-slate-500">
            <span>{progress.stage ?? "진행 중"}</span>
            <span>{progress.total > 0 ? `${progress.n}/${progress.total}` : "..."}</span>
          </div>
          <div className="h-2 bg-slate-200 rounded overflow-hidden">
            <div
              className={`h-full transition-all ${progress.error ? "bg-rose-500" : progress.done ? "bg-emerald-500" : "bg-blue-500"}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          {progress.current && <div className="text-[11px] text-slate-500 truncate">{progress.current}</div>}
          {progress.error && <div className="text-xs text-rose-600">오류: {progress.error}</div>}
        </div>
      )}
    </div>
  );
}
