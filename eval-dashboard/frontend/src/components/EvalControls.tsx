import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useEvalStatus, useStartEval } from "../api/hooks";

type Props = { contestId: number | null };

type Progress = {
  n: number;
  total: number;
  stage?: string;
  current?: string;
  logTail?: string[];        // last few log lines
  done?: boolean;
  skipped?: boolean;
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

  // Reset progress when contest changes.
  useEffect(() => {
    setProgress(null);
    detach();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contestId]);

  const pushLog = (line: string) =>
    setProgress((p) => {
      const cur = p ?? { n: 0, total: 0 };
      const tail = [...(cur.logTail ?? []), line].slice(-5);
      return { ...cur, logTail: tail };
    });

  const attach = (jobId: string) => {
    detach();
    pushLog(`SSE 연결 → job ${jobId.slice(0, 8)}`);
    const es = new EventSource(`/api/jobs/${jobId}/stream`);
    esRef.current = es;
    es.addEventListener("started", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setProgress((p) => ({
        ...(p ?? { n: 0, total: 0 }),
        n: 0,
        total: data.n_total ?? 0,
        stage: "시작",
      }));
      pushLog(`started · 예상 ${data.n_total ?? 0}건`);
    });
    es.addEventListener("stage", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setProgress((p) => ({
        ...(p ?? { n: 0, total: 0 }),
        stage: data.name,
        total: data.n_to_run ?? p?.total ?? 0,
      }));
      pushLog(`stage · ${data.name}${data.n_to_run != null ? ` (${data.n_to_run}건)` : ""}`);
    });
    es.addEventListener("progress", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setProgress((p) => ({
        ...(p ?? { n: 0, total: 0 }),
        n: data.n,
        total: data.total,
        current: `${data.current_user}/${data.current_problem} (overall=${data.ev_overall})`,
        logTail: [...((p ?? { logTail: [] }).logTail ?? []), data.log_line ?? "(no log)"].slice(-5),
      }));
    });
    es.addEventListener("warn", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      pushLog(`⚠ ${data.message ?? ""}`);
    });
    es.addEventListener("log", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      if (data.line) pushLog(data.line);
    });
    es.addEventListener("ping", () => {
      // keepalive — ignore but reset stalls
    });
    es.addEventListener("done", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      const skipped = !!data.skipped;
      setProgress((p) => ({
        ...(p ?? { n: 0, total: 0 }),
        done: true,
        skipped,
        stage: skipped
          ? "이미 모든 학생·문제가 평가되어 있습니다"
          : `완료 — 성공 ${data.n_evaluated} / 실패 ${data.n_failed}`,
      }));
      pushLog(skipped
        ? "skipped (전체 캐시 적중)"
        : `done · 성공 ${data.n_evaluated} / 실패 ${data.n_failed}`);
      qc.invalidateQueries({ queryKey: ["scoreboard", contestId] });
      qc.invalidateQueries({ queryKey: ["eval-status", contestId] });
      detach();
      // Auto-clear ONLY for actual successful run (not skipped, not error).
      if (!skipped) {
        window.setTimeout(() => setProgress(null), 10000);
      }
    });
    es.addEventListener("error", (e) => {
      const data = JSON.parse((e as MessageEvent).data || "{}");
      setProgress((p) => ({
        ...(p ?? { n: 0, total: 0 }),
        error: data.message ?? "stream error",
      }));
      pushLog(`error · ${data.message ?? "stream error"}`);
      detach();
    });
    es.onerror = () => {
      // Network-level — server may be slow. Don't clear UI.
      pushLog("(네트워크 일시 오류, 재연결 시도 중)");
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
    setProgress({ n: 0, total: 0, stage: "요청 중...", logTail: [] });
    try {
      const res = await startMut.mutateAsync(force);
      pushLog(`POST /qualitative-eval (force=${force}) → n_to_run=${res.n_to_run}`);
      // If server replied n_to_run=0 we're going to see skipped; tell the user proactively.
      if (res.n_to_run === 0 && !force) {
        setProgress((p) => ({
          ...(p ?? { n: 0, total: 0 }),
          stage: "처리할 항목이 없습니다 — 모든 학생·문제가 이미 평가되어 있음",
        }));
      }
      attach(res.job_id);
    } catch (e) {
      const msg = (e as { response?: { data?: { detail?: string } }; message?: string })
        .response?.data?.detail ?? (e as Error).message;
      setProgress({ n: 0, total: 0, error: msg, logTail: [] });
    }
  };

  if (contestId == null) return null;

  const running = !!progress && !progress.done && !progress.error;
  const pct =
    progress && progress.total > 0
      ? Math.round((progress.n / progress.total) * 100)
      : running
      ? 0
      : 100;

  const barColor = progress?.error
    ? "bg-rose-500"
    : progress?.skipped
    ? "bg-slate-400"
    : progress?.done
    ? "bg-emerald-500"
    : "bg-blue-500";

  return (
    <div className="border-t border-slate-200 p-4 space-y-2 bg-slate-50">
      <div className="text-xs text-slate-500">
        평가 캐시: {status.data?.n_evaluated ?? "-"}건
        {status.data?.last_run_at && (
          <> · 마지막 {new Date(status.data.last_run_at).toLocaleString()}</>
        )}
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => start(false)}
          disabled={running || startMut.isPending}
          className="flex-1 rounded bg-blue-600 text-white text-sm py-1.5 hover:bg-blue-700 disabled:bg-slate-300"
        >
          {running ? "평가 중..." : "정성평가"}
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
        <div className="space-y-1.5 mt-2 rounded border border-slate-200 bg-white p-2.5">
          <div className="flex justify-between text-xs">
            <span className={progress.error ? "text-rose-700" : progress.skipped ? "text-slate-700" : "text-slate-700 font-medium"}>
              {progress.stage ?? "진행 중"}
            </span>
            {progress.total > 0 && (
              <span className="text-slate-500 tabular-nums">
                {progress.n}/{progress.total} ({pct}%)
              </span>
            )}
          </div>

          <div className="h-2 bg-slate-200 rounded overflow-hidden">
            <div
              className={`h-full transition-all ${barColor}`}
              style={{ width: `${pct}%` }}
            />
          </div>

          {progress.current && (
            <div className="text-[11px] text-slate-600 truncate" title={progress.current}>
              ▸ {progress.current}
            </div>
          )}

          {progress.logTail && progress.logTail.length > 0 && (
            <details className="text-[10px] text-slate-500">
              <summary className="cursor-pointer hover:text-slate-700">
                로그 ({progress.logTail.length}줄)
              </summary>
              <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap break-all bg-slate-50 p-1.5 rounded">
                {progress.logTail.join("\n")}
              </pre>
            </details>
          )}

          {progress.error && (
            <div className="text-xs text-rose-700">{progress.error}</div>
          )}

          {(progress.done || progress.error) && (
            <div className="flex justify-end pt-1">
              <button
                onClick={() => setProgress(null)}
                className="text-[11px] text-slate-500 hover:text-slate-800 underline"
              >
                닫기
              </button>
            </div>
          )}

          {progress.skipped && (
            <div className="text-[11px] text-slate-500 leading-snug">
              새로 평가하려면 우측 <span className="font-medium">재평가</span> 버튼을 누르세요.
              <br />
              개별 항목이 누락된 경우는 lecture-code-review 의 export 가 새 제출을 가져온 뒤 다시 시도하세요.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
