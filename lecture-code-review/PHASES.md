# 진행상황

> 각 페이즈 시작/완료 시 갱신. 검증 결과·차단 요소·다음 페이즈 진입 조건을 명시.

## Phase 1: DB → 디스크 export

- 상태: **completed (사용자 confirm 대기)**
- 시작: 2026-05-08
- 완료: 2026-05-08
- 범위: lecture/contest 지정 → 학생 코드 + 메타데이터 디스크 export (read-only)
- 출력 형식:
  - `_meta/{lecture,contest}.json`
  - `_meta/problems/<P0n>.json` (description, samples, hint, time/memory limit, languages, test_case_score 등 풀텍스트)
  - `_meta/{problems,students,submissions,final_submissions}.csv`
  - `_meta/summary.json`
  - `codes/<username>/<problem_label>/<YYYYMMDD-HHMMSS>_<sub_id_short>__<RESULT>.<ext>` (모든 제출)
  - `final_codes/<username>/<problem_label>.<ext>` (학생별 문제별 **최종 제출** — Phase 2 평가 입력)
- Golden sample: `lecture_id=388` × `contest_id=6181` — `C프로그래밍(5분반, 전수빈) / 2024-2 C프로그래밍 기말고사`
- 검증 결과 (DB ↔ export 교차 일치):

| 지표 | DB SELECT | Export |
|---|---|---|
| 제출 수 | 192 | 192 |
| 제출자 수 (DISTINCT user_id) | 27 | 27 |
| `result=-2` (CE) | 16 | 16 |
| `result=-1` (WA) | 22 | 22 |
| `result=0` (AC) | 45 | 45 |
| `result=8` (PA) | 109 | 109 |
| `lecture_signup_class.lecture_id=388` 학생 | 37 | 37 |
| Contest 문제 수 | 7 | 7 |
| 코드 파일 수 (`find codes -type f`) | — | 192 |
| 학생 디렉토리 수 (`ls codes/`) | — | 27 |
| **DISTINCT (user_id, problem_id) 조합** | **101** | **101** |
| **final_codes 파일 수** | — | **101** |
| **final_submissions.csv 행 수** | — | **101** |
| 문제 풀텍스트 (`_meta/problems/*.json`) | — | 7 |

최종 제출 결과 분포 (final_by_result): AC=40, PA=46, WA=9, CE=6

- 출력 위치: `out/lecture-388_contest-6181/`
- 실행: `.venv/bin/lecture-code-review -L 388 -C 6181` (≈ 0.05초)
- 다음 페이즈로 넘어가는 조건: 사용자 confirm 시 Phase 2 plan 별도 작성

## Phase 2: (TBD)

- 결정 시점: Phase 1 완료 후 별도 plan 으로 재진입
- 후보: 가져온 코드에 대한 자동 검토 (LLM 기반 코드리뷰, 동일 학생의 코드 변천사, 채점 결과와의 cross-check 등)
