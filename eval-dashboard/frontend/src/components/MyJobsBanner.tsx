import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useQueueSnapshot } from "../api/hooks";
import type { Lecture } from "../lib/types";
import { getRequesterId } from "../lib/session";

type Job = {
  job_id: string;
  lecture_id: number;
  contest_id: number;
  requester_ids: string[];
  status: "running" | "pending";
  n_done?: number;
  n_total?: number;
  queue_position?: number;
};

type Props = {
  onJump: (sel: {
    year: number;
    semester: number;
    lectureId: number;
    contestId: number;
  }) => void;
};

export function MyJobsBanner({ onJump }: Props) {
  const queue = useQueueSnapshot();
  const qc = useQueryClient();
  const myId = getRequesterId();

  const qs = queue.data;
  if (!qs) return null;

  const jobs: Job[] = [
    ...qs.running
      .filter((r) => r.requester_ids.includes(myId))
      .map((r) => ({ ...r, status: "running" as const })),
    ...qs.pending
      .filter((p) => p.requester_ids.includes(myId))
      .map((p) => ({ ...p, status: "pending" as const })),
  ];

  if (jobs.length === 0) return null;

  const handleJump = async (j: Job) => {
    // Need year/sem to fully populate sidebar. Fetch via cache or API.
    let lecture = qc.getQueryData<Lecture>(["lecture", j.lecture_id]);
    if (!lecture) {
      try {
        lecture = (await api.get<Lecture>(`/lectures/${j.lecture_id}`)).data;
        qc.setQueryData(["lecture", j.lecture_id], lecture);
      } catch {
        return;
      }
    }
    onJump({
      year: lecture.year,
      semester: lecture.semester,
      lectureId: j.lecture_id,
      contestId: j.contest_id,
    });
  };

  return (
    <div className="rounded border border-blue-200 bg-blue-50 p-2 space-y-1">
      <div className="text-[11px] font-semibold text-blue-900">
        내 작업 ({jobs.length})
      </div>
      <ul className="space-y-1">
        {jobs.map((j) => (
          <li
            key={j.job_id}
            className="flex items-center justify-between text-[11px] gap-2"
          >
            <button
              onClick={() => handleJump(j)}
              className="text-left text-blue-700 hover:underline truncate flex-1 min-w-0"
              title="이 contest 로 이동"
            >
              contest {j.contest_id}
            </button>
            <span className="tabular-nums text-slate-600 shrink-0">
              {j.status === "running"
                ? `${j.n_done ?? 0}/${j.n_total || "?"}`
                : `대기 ${j.queue_position}번째`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
