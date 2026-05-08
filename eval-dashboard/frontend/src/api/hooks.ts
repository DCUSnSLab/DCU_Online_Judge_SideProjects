import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  CellDetail,
  Contest,
  EvalStatus,
  Lecture,
  ScoreboardResponse,
} from "../lib/types";

export const useYears = () =>
  useQuery({ queryKey: ["years"], queryFn: async () => (await api.get<number[]>("/years")).data });

export const useSemesters = (year: number | null) =>
  useQuery({
    queryKey: ["semesters", year],
    enabled: year != null,
    queryFn: async () => (await api.get<number[]>(`/years/${year}/semesters`)).data,
  });

export const useLectures = (year: number | null, semester: number | null) =>
  useQuery({
    queryKey: ["lectures", year, semester],
    enabled: year != null && semester != null,
    queryFn: async () =>
      (await api.get<Lecture[]>(`/years/${year}/semesters/${semester}/lectures`)).data,
  });

export const useContests = (lectureId: number | null) =>
  useQuery({
    queryKey: ["contests", lectureId],
    enabled: lectureId != null,
    queryFn: async () => (await api.get<Contest[]>(`/lectures/${lectureId}/contests`)).data,
  });

export const useScoreboard = (contestId: number | null) =>
  useQuery({
    queryKey: ["scoreboard", contestId],
    enabled: contestId != null,
    queryFn: async () =>
      (await api.get<ScoreboardResponse>(`/contests/${contestId}/scoreboard`)).data,
  });

export const useCellDetail = (
  contestId: number | null,
  userId: number | null,
  problemId: number | null,
) =>
  useQuery({
    queryKey: ["cell", contestId, userId, problemId],
    enabled: contestId != null && userId != null && problemId != null,
    queryFn: async () =>
      (
        await api.get<CellDetail>(
          `/contests/${contestId}/students/${userId}/problems/${problemId}`,
        )
      ).data,
  });

export const useEvalStatus = (contestId: number | null) =>
  useQuery({
    queryKey: ["eval-status", contestId],
    enabled: contestId != null,
    queryFn: async () =>
      (await api.get<EvalStatus>(`/contests/${contestId}/eval-status`)).data,
  });

export const useStartEval = (contestId: number | null) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (force: boolean) => {
      const res = await api.post<{ job_id: string; n_total: number; n_to_run: number }>(
        `/contests/${contestId}/qualitative-eval`,
        { force },
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["eval-status", contestId] });
    },
  });
};
