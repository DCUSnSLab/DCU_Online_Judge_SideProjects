export type Lecture = { id: number; title: string; year: number; semester: number };

export type Contest = {
  id: number;
  title: string;
  lecture_id: number | null;
  lecture_contest_type: string;
  start_time: string | null;
  end_time: string | null;
};

export type Problem = {
  id: number;
  label: string;
  title: string;
  total_score: number;
  difficulty: string;
};

export type TestcaseCell = {
  submission_id: string | null;
  result: number | null;
  result_label: string | null;
  score: number | null;
  time_cost_ms: number | null;
  memory_cost_kb: number | null;
  language: string | null;
};

export type QualitativeShort = {
  overall: number | null;
  suggested_partial_score: number | null;
  ai_likelihood_score: number | null;
  ai_confidence: string | null;
  has_error: boolean;
};

export type ScoreboardCell = {
  testcase: TestcaseCell | null;
  qualitative: QualitativeShort | null;
};

export type ScoreboardRow = {
  user_id: number;
  username: string;
  realname: string | null;
  by_problem: Record<string, ScoreboardCell>;
};

export type ScoreboardResponse = {
  contest: Contest;
  lecture: Lecture;
  problems: Problem[];
  students: ScoreboardRow[];
  n_evaluated_pairs: number;
  n_total_pairs: number;
};

export type EvalStatus = {
  has_lecture_export: boolean;
  n_evaluated: number;
  n_pairs: number;
  last_run_at: string | null;
  running_job_id: string | null;
};

export type CellDetail = {
  lecture_id: number;
  contest_id: number;
  problem: {
    id: number; label: string; title: string;
    description: string; input_description: string; output_description: string;
    samples: { input?: string; output?: string }[];
    total_score: number; difficulty: string;
    time_limit: number; memory_limit: number;
  };
  submission: null | {
    id: string; code: string; language: string;
    result: number; result_label: string;
    statistic_info: Record<string, unknown>;
    create_time: string | null;
  };
  qualitative: null | {
    scores?: Record<string, number>;
    comments?: Record<string, { assessment?: string; suggestion?: string }>;
    overall?: number;
    summary?: string;
    suggested_partial_score?: number;
  };
  ai_usage_assessment: null | {
    likelihood_score?: number;
    confidence?: string;
    signals?: { category: string; observation: string; weight: string }[];
    counter_signals?: string[];
    summary?: string;
    disclaimer?: string;
    error?: string | null;
  };
};
