# 08 · eval-dashboard API · SSE 이벤트 계약 (DCUCODE 이식용)

> [`07-eval-system-summary.md`](./07-eval-system-summary.md) 가 전체 그림이라면, 본 문서는 **DCUCODE 가 흡수하거나 호출할 때 알아야 할 모든 endpoint 와 데이터 스키마**를 한 페이지에 모은 것입니다.

기준 코드: `eval-dashboard/backend/src/eval_dashboard/api/{nav,scoreboard,eval}.py` + `models.py`

---

## REST 엔드포인트 일람

모두 prefix `/api`. 헤더 `X-Requester: <browser-uuid>` 는 큐 합치기·식별용 (없어도 동작, 그러면 익명).

### 네비게이션 (메뉴 채우기용)

| Method | Path | 응답 |
|---|---|---|
| GET | `/years` | `[2026, 2025, ...]` (DISTINCT, status=true 강의만) |
| GET | `/years/{year}/semesters` | `[1, 2, 3]` |
| GET | `/years/{year}/semesters/{semester}/lectures` | `[{id, title, year, semester}, ...]` |
| GET | `/lectures/{lecture_id}` | `{id, title, year, semester}` (단건, MyJobsBanner 점프용) |
| GET | `/lectures/{lecture_id}/contests` | `[{id, title, lecture_id, lecture_contest_type, start_time, end_time}, ...]` |

### 스코어보드 (정량 + 정성 통합)

| Method | Path | 응답 |
|---|---|---|
| GET | `/contests/{contest_id}/scoreboard` | 매트릭스 전체 (아래 ScoreboardResponse 참조) |
| GET | `/contests/{contest_id}/students/{user_id}/problems/{problem_id}` | 단일 (학생, 문제) 셀 상세 (코드 + testcase + 정성 + AI-usage) |

### 평가 트리거 / 큐

| Method | Path | 응답 |
|---|---|---|
| GET | `/contests/{contest_id}/eval-status` | `{has_lecture_export, n_evaluated, n_pairs, last_run_at, running_job_id}` |
| POST | `/contests/{contest_id}/qualitative-eval` | body `{force: bool}`, header `X-Requester` → `EvalJobStarted` |
| GET | `/jobs/{job_id}` | job 상세 (status·n_done·n_total·requester_ids·queue_position) |
| GET | `/jobs/{job_id}/stream` | **SSE** — 이벤트 스트림 |
| GET | `/queue` | 글로벌 GPU 큐 스냅샷 (`QueueSnapshot`) |

기타: `GET /api/health` → `{"status":"ok"}`. OpenAPI 문서: `:8001/docs`.

---

## 응답 스키마

### `ScoreboardResponse`

```json
{
  "contest": {"id": 6181, "title": "...", "lecture_id": 388, "lecture_contest_type": "대회", "start_time": "...", "end_time": "..."},
  "lecture": {"id": 388, "title": "...", "year": 2025, "semester": 2},
  "problems": [
    {"id": 27432, "label": "P01", "title": "...", "total_score": 20, "difficulty": "Low"},
    ...
  ],
  "students": [
    {
      "user_id": 6255,
      "username": "alswo6592",
      "realname": "권민재",
      "by_problem": {
        "P01": {
          "testcase": {
            "submission_id": "...",
            "result": -1,
            "result_label": "WA",     // AC | WA | PA | TLE | RTLE | MLE | RE | SE | CE | PENDING | JUDGING
            "score": 0,
            "time_cost_ms": 0,
            "memory_cost_kb": 1572864,
            "language": "C"
          },
          "qualitative": {            // null 이면 아직 평가 안 됨
            "overall": 18,            // 0~100 정수
            "suggested_partial_score": 3,   // 0~total_score 정수
            "ai_likelihood_score": 15,      // 0~100 정수, null 가능
            "ai_confidence": "low",         // low|medium|high, null 가능
            "has_error": false
          }
        },
        "P02": { "testcase": null, "qualitative": null },     // 미제출 + 미평가
        ...
      }
    },
    ...
  ],
  "n_evaluated_pairs": 39,
  "n_total_pairs": 266
}
```

### Cell detail (`/students/{uid}/problems/{pid}`)

```json
{
  "lecture_id": 388,
  "contest_id": 6181,
  "problem": {
    "id": 27432,
    "label": "P01",
    "title": "...",
    "description": "<html>...",         // 원본 그대로 (HTML 가능)
    "input_description": "...",
    "output_description": "...",
    "samples": [{"input": "...", "output": "..."}, ...],
    "total_score": 20,
    "difficulty": "Low",
    "time_limit": 1000,                  // ms
    "memory_limit": 256                  // MB
  },
  "submission": null | {
    "id": "...",
    "code": "<full source>",
    "language": "C",
    "result": -1,
    "result_label": "WA",
    "statistic_info": {"score": 0, "time_cost": 0, "memory_cost": 1572864, ...},
    "create_time": "..."
  },
  "qualitative": null | {
    "scores": {"correctness": 2, "algorithm": 1, "readability": 3, "problem_understanding": 1},
    "comments": {
      "correctness": {"assessment": "...", "suggestion": "..."},
      "algorithm":   {"assessment": "...", "suggestion": "..."},
      "readability": {"assessment": "...", "suggestion": "..."},
      "problem_understanding": {"assessment": "...", "suggestion": "..."}
    },
    "overall": 18,
    "summary": "...",
    "suggested_partial_score": 3,
    "model_used": "<profile-default>",
    "llm_latency_ms": 2196,
    "error": null,
    "recomputed": {                      // 산식 재계산이 모델값을 덮어쓴 경우만 키 존재
      "overall": {"model": 19, "formula": 18, "diff": -1}
    }
  },
  "ai_usage_assessment": null | {
    "likelihood_score": 15,
    "confidence": "low",
    "signals": [
      {"category": "comment_style|naming|structure|idiom|consistency|irrelevant_feature|absence_of_learner_traces|other",
       "observation": "...",
       "weight": "low|medium|high"}
    ],
    "counter_signals": ["...", "..."],
    "summary": "...",
    "disclaimer": "이 평가는 참고 신호일 뿐이며 부정행위 판단의 단독 근거가 아닙니다.",
    "model_used": "...",
    "llm_latency_ms": 2120,
    "error": null
  }
}
```

### `EvalJobStarted` (POST 응답)

```json
{
  "job_id": "uuid",
  "n_total": 68,
  "n_already_evaluated": 0,
  "n_to_run": 68,
  "joined_existing": false,            // 이미 진행 중인 job 에 합류했는지
  "queue_position": 2,                  // 1-based; null 이면 즉시 실행 슬롯 획득
  "slots_in_use": 3,
  "slots_total": 3
}
```

### `QueueSnapshot` (`GET /queue`)

```json
{
  "slots_total": 3,
  "slots_in_use": 3,
  "queue_size": 2,
  "running": [
    {"job_id": "...", "lecture_id": 388, "contest_id": 6172,
     "requester_ids": ["req-aaaaaa", "req-bbbbbb"],
     "n_done": 12, "n_total": 68, "started_at": "..."}
  ],
  "pending": [
    {"job_id": "...", "lecture_id": 388, "contest_id": 6181,
     "requester_ids": ["req-cccccc"],
     "queue_position": 1, "enqueued_at": "..."}
  ]
}
```

---

## SSE 이벤트 일람 (`GET /jobs/{job_id}/stream`)

`Content-Type: text/event-stream`. 이벤트는 모두 `event: <name>\ndata: <json>\n\n` 형태.

| event | 시점 | data 스키마 |
|---|---|---|
| `queued` | 큐에 처음 들어왔을 때 | `{queue_position, queue_size, slots_in_use, slots_total}` |
| `queue-update` | 다른 job 의 시작/종료로 슬롯 상태 변할 때마다 (모든 pending 에 broadcast) | `{queue_position, queue_size, slots_in_use, slots_total}` |
| `started` | 슬롯 획득해서 실제 실행 시작 | `{lecture_id, contest_id, n_total, slots_in_use, slots_total}` |
| `stage` | 단계 전환 — `lecture-code-review export`, `archiving previous evaluations`, `qualitative+ai_usage`, `problem P01` 등 | `{name, n_to_run?, n_users?}` |
| `progress` | llm-code-review 가 한 (user, problem) 평가 완료할 때마다 | `{n, total, current_user, current_problem, ev_overall, ev_sps, ev_latency_ms, ai_usage, log_line}` |
| `log` | INFO/WARN/ERROR 로그 라인 (progress 패턴에 맞지 않는) | `{line}` |
| `warn` | llm-code-review 가 한 평가에 실패했을 때 | `{message}` |
| `done` | 모든 단계 완료 — 정상 종료. `skipped:true` 면 처리할 항목 0건 | `{n_evaluated, n_failed, skipped}` |
| `error` | job 실패 (`status=failed`) | `{message}` |
| `ping` | idle 시 keepalive | `{ts}` |

### history replay

SSE 연결 시 백엔드는 **이미 발생한 모든 이벤트** (`job.history`, 최대 500개) 를 먼저 replay 한 뒤 실시간 스트림으로 전환합니다. 페이지 새로고침이나 contest 재방문 시 진행 상태 자동 복원.

### 흐름 예시 (정상)

```
event: queued        data: {queue_position:2, ...}
event: queue-update  data: {queue_position:1, ...}    # 다른 job 끝남
event: started       data: {lecture_id:388, contest_id:6181, n_total:0, slots_in_use:3}
event: stage         data: {name:"lecture-code-review export"}
event: stage         data: {name:"qualitative+ai_usage", n_to_run:21}
event: stage         data: {name:"problem P01", n_users:21}
event: log           data: {line:"... INFO HTTP Request: POST .../chat/completions ..."}
event: progress      data: {n:1, total:21, current_user:"alswo6592", current_problem:"P01", ev_overall:"18", ev_sps:"3", ai_usage:"15/low", ...}
... (반복)
event: done          data: {n_evaluated:21, n_failed:0, skipped:false}
```

---

## 클라이언트 구현 노트

- POST 응답이 `joined_existing:true` 면 두 번째 요청자가 기존 job 에 합류한 것. UI 에 안내 표시 권장.
- POST 응답이 `n_to_run:0` 이고 `force:false` 였다면 SSE 가 곧바로 `done {skipped:true}` 만 보내고 끝남. UI 에서 "이미 모두 평가됨" 메시지 + "재평가" 버튼 안내.
- `409` 응답은 더 이상 던지지 않음 (single-flight 가 합치기로 대체됨). 다만 force=true 가 동시에 여러 개 들어오면 별도 job 으로 큐에 쌓임 (의도).
- `GET /jobs/{job_id}/stream` 의 `EventSource` 는 자동 재연결 시도하니 `onerror` 에서 fatal 처리하지 말 것.
- 매트릭스 갱신: `done` 이벤트 받으면 `/contests/{id}/scoreboard` 를 `invalidate` (TanStack Query) 하면 정성/AI 컬럼 갱신됨.

---

## 헤더 / 쿠키

| 이름 | 출처 | 용도 |
|---|---|---|
| `X-Requester` | 클라이언트 (브라우저 localStorage uuid 또는 인증 시스템의 사용자 식별자) | 큐 합치기 시 `requester_ids` 누적, MyJobsBanner 의 "내 작업" 필터링 |

CORS 는 `Settings.cors_origins` 환경변수로 화이트리스트 (default `http://localhost:5173`). 인증 헤더는 현재 사용 안 함.

---

## 환경변수

`backend/.env.example` 참조.

| 키 | 기본값 | 의미 |
|---|---|---|
| `PG_DSN` | `postgresql://onlinejudge:onlinejudge@127.0.0.1:5432/onlinejudge` | OJ PostgreSQL DSN |
| `LECTURE_CR_DIR` | (없음, 필수) | `lecture-code-review` 프로젝트 루트 (subprocess + out/ read 용) |
| `LLM_CR_DIR` | (없음, 필수) | `llm-code-review` 프로젝트 루트 (subprocess + out/ read 용) |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 콤마 구분 |
| `MAX_CONCURRENT_EVAL_JOBS` | `3` | GPU 동시 슬롯 |

LLM 자체 환경변수 (Qwen onprem) 는 `llm-code-review/.env` 에 별도. eval-dashboard 가 subprocess 호출 시 `os.environ` 을 그대로 상속하므로, eval-dashboard 가 띄워지는 셸에 LLM env 가 노출돼 있어야 합니다.
