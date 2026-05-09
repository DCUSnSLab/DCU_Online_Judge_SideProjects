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

## Phase 1 후속 — SSE 실시간 진행 fix (commit 5a29068)

- 상태: completed
- subprocess stdout block-buffered 해결 (`python -u` + `PYTHONUNBUFFERED=1`)
- SSE generator sync `queue.get` → async `asyncio.Queue` per-subscriber 전환
- 결과: thread pool 고갈로 인한 백엔드 hang 해소, 진행 라인 실시간 도착

## Phase 1 후속 — 글로벌 GPU 큐

- 상태: **completed (사용자 confirm 대기)**
- 시작: 2026-05-09
- 완료: 2026-05-09
- 범위:
  - `GpuScheduler` 클래스 — `BoundedSemaphore(N=3)` + FIFO pending list
  - `MAX_CONCURRENT_EVAL_JOBS` env (default 3)
  - SSE 새 이벤트: `queued`, `queue-update` (모든 pending job 에 broadcast)
  - 동일 contest 합치기: 두 번째 요청자는 같은 job 의 SSE 에 합류, `requester_ids` 에 추가
  - `X-Requester` 헤더 (브라우저 localStorage uuid)
  - `GET /api/queue` 검증·운영 점검용 스냅샷
  - Frontend `EvalControls` — 대기 박스 (⏳ 대기 중 — N번째 / GPU K/3) + 합류 안내
- 검증 결과:

| 시나리오 | 결과 |
|---|---|
| 1. 동일 contest 합치기 | REQ_6181 force 후 REQ_6181_BUDDY 의 force=false → `joined_existing=true`, 같은 job_id, requester_ids = ["REQ_6181","REQ_6181_BUDDY"] |
| 2. 슬롯 초과 → 큐 진입 | 5개 contest 빠르게 트리거 → 처음 3개 running, 4·5번째 queued (queue_position 1·2) |
| 3. 슬롯 해제 → 자동 promote | 첫 번째 끝나자 pending#1 (6179) 가 running 으로 전이, queue_size 2→1, queue-update 모든 pending 에 broadcast |
| 4. `/api/queue` 스냅샷 | slots_in_use/total + running[]·pending[] 정확 반영 |

## Phase 2 (TBD)

- 백그라운드 큐 영속화 (Redis/RQ/Celery) + 서버 재시작 시 복구
- 알림 (이메일·슬랙)
- 인증/권한
- Cancel API
- 모바일 반응형
