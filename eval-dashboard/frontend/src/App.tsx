import { useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Scoreboard } from "./components/Scoreboard";
import { DetailPanel } from "./components/DetailPanel";
import { EvalControls } from "./components/EvalControls";

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

export default function App() {
  const [s, setS] = useState<State>({
    year: null, semester: null, lectureId: null, contestId: null,
  });
  const [selection, setSelection] = useState<Selection>({ kind: "none" });

  const update = (patch: Partial<State>) => setS((prev) => ({ ...prev, ...patch }));

  return (
    <div className="h-full flex">
      <div className="flex flex-col w-72 shrink-0">
        <Sidebar
          year={s.year}
          semester={s.semester}
          lectureId={s.lectureId}
          contestId={s.contestId}
          onChange={(p) => {
            update(p);
            setSelection({ kind: "none" });
          }}
        />
        <div className="flex-1" />
        <EvalControls contestId={s.contestId} />
      </div>

      <main className="flex-1 min-w-0 bg-white">
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
