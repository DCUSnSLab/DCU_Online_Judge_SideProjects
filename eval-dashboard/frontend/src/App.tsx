import { useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Scoreboard } from "./components/Scoreboard";
import { DetailPanel } from "./components/DetailPanel";
import { EvalControls } from "./components/EvalControls";
import { MyJobsBanner } from "./components/MyJobsBanner";

type Selection =
  | { kind: "none" }
  | { kind: "row"; userId: number }
  | { kind: "col"; problemId: number }
  | { kind: "cell"; userId: number; problemId: number };

type State = {
  year: number | null;
  semester: number | null;
  lectureId: number | null;
  contestId: number | null;
};

const EMPTY: State = { year: null, semester: null, lectureId: null, contestId: null };

/** Partial update that cascades downstream-resets on upstream changes,
 * mimicking the natural "pick year → semester → lecture → contest" flow. */
function applyPick(prev: State, p: Partial<State>): State {
  const next: State = { ...prev };
  if ("year" in p) {
    next.year = p.year ?? null;
    if (next.year !== prev.year) {
      next.semester = null;
      next.lectureId = null;
      next.contestId = null;
    }
  }
  if ("semester" in p) {
    next.semester = p.semester ?? null;
    if (next.semester !== prev.semester) {
      next.lectureId = null;
      next.contestId = null;
    }
  }
  if ("lectureId" in p) {
    next.lectureId = p.lectureId ?? null;
    if (next.lectureId !== prev.lectureId) {
      next.contestId = null;
    }
  }
  if ("contestId" in p) {
    next.contestId = p.contestId ?? null;
  }
  return next;
}

export default function App() {
  const [s, setS] = useState<State>(EMPTY);
  const [selection, setSelection] = useState<Selection>({ kind: "none" });

  const handlePick = (patch: Partial<State>) => {
    setS((prev) => applyPick(prev, patch));
    setSelection({ kind: "none" });
  };

  /** Programmatic jump from MyJobsBanner — set all four at once,
   * bypassing cascade resets. */
  const handleJump = (full: { year: number; semester: number; lectureId: number; contestId: number }) => {
    setS(full);
    setSelection({ kind: "none" });
  };

  return (
    // h-screen + overflow-hidden: lock to viewport so child panes scroll
    // internally instead of growing the body. Without this a tall scoreboard
    // pushes the sidebar down and EvalControls off-screen.
    <div className="h-screen overflow-hidden flex">
      <div className="flex flex-col w-72 shrink-0 h-full overflow-hidden border-r border-slate-200 bg-white">
        <div className="overflow-y-auto min-h-0">
          <Sidebar
            year={s.year}
            semester={s.semester}
            lectureId={s.lectureId}
            contestId={s.contestId}
            onChange={handlePick}
          />
          <div className="px-4 pb-2">
            <MyJobsBanner onJump={handleJump} />
          </div>
        </div>
        {/* Spacer pushes EvalControls to the very bottom regardless of upper content height. */}
        <div className="flex-1" />
        <EvalControls contestId={s.contestId} />
      </div>

      <main className="flex-1 min-w-0 bg-white overflow-hidden">
        <Scoreboard
          contestId={s.contestId}
          selection={selection}
          onSelect={setSelection}
        />
      </main>

      <DetailPanel
        contestId={s.contestId}
        selection={selection}
        onClose={() => setSelection({ kind: "none" })}
      />
    </div>
  );
}
