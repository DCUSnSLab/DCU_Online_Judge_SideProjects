# 진행상황

## Phase 1: 4-뷰 대시보드 + 정성평가 트리거 (SSE)

- 상태: **completed (사용자 confirm 대기)**
- 브랜치: `phase3/eval-dashboard`
- 시작: 2026-05-08
- 완료: 2026-05-09
- 범위:
  - Backend: FastAPI :8001 — DB 직결(psycopg pool) + 디스크 read (llm-code-review out/) + subprocess (lecture/llm-code-review CLI)
  - Frontend: Vite + React 19 + TypeScript + Tailwind 3 + TanStack Query — :5173, /api 프록시
  - 정성평가 트리거: 누락 (user, problem) 만 추려 `--problem`/`--username` 다회 호출. force=true 면 out_archive/ 로 백업 후 전체 재실행
  - SSE: `[N/M] user/Pn ...` 로그 라인을 정규식으로 파싱 → progress 이벤트
- 검증 결과 (golden sample lecture 388 / contest 6181):

| 항목 | 결과 |
|---|---|
| Backend 헬스체크 (years, semesters, lectures, contests, scoreboard, eval-status, cell detail) | 모두 200 + 의도된 데이터 |
| 매트릭스 구성 | 38명(명단 27 + 제출만 한 외부 11) × 7문제 |
| 정성/AI 평가 캐시 — 시작 | 39/266 셀 |
| 평가 트리거 (force=false) | 누락 62건 식별 → 약 2분 34초 / 실패 0 |
| 정성/AI 평가 캐시 — 완료 | 101/266 셀 (final_submissions.csv 의 전체 쌍) |
| Single-flight 보호 | 두 번째 POST → 409 |

- 다음 페이즈로 넘어가는 조건: 사용자 GUI 직접 사용 confirm 후

## Phase 2 (TBD)

- 백그라운드 큐 (Redis/RQ/Celery) + 알림
- 인증/권한
- 다중 contest 동시 평가
- 모바일 반응형
