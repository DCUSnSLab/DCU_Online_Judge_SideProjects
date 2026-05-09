# 07 · eval system 전체 요약 (DCUCODE 이식용)

> 이 문서는 `DCU_Online_Judge_SideProjects/` 안에서 만들어진 3개의 사이드 프로젝트가 무엇인지, 어떻게 연결되어 있는지, 왜 그렇게 설계됐는지를 한 번에 보여줍니다. 다음 두 문서와 함께 읽으면 됩니다:
>
> - [`08-api-and-events.md`](./08-api-and-events.md) — REST · SSE 계약 명세
> - [`09-dcucode-integration.md`](./09-dcucode-integration.md) — DCUCODE 본체에 어떻게 가져갈지 단계별 가이드

## 1. 만들어진 것

| # | 프로젝트 | 역할 | 형태 | 산출물 |
|---|---|---|---|---|
| 1 | **`lecture-code-review`** | 특정 강의 × 특정 contest 의 학생 제출 코드를 PostgreSQL 에서 직결로 끌어와 디스크에 export | Python 3.10 CLI | `out/<run>/_meta/*.{csv,json}` + `codes/<u>/<P>/*.{c,cpp,...}` + `final_codes/<u>/<P>.<ext>` (학생·문제별 마지막 제출) + `_meta/problems/<P0n>.json` (문제 풀텍스트) |
| 2 | **`llm-code-review`** | export 된 final 코드 + 문제 메타를 입력으로 onprem Qwen3.5-35B 호출 → 4축 정성 평가 + AI 사용 가능성 평가 | Python 3.10 CLI (의존: `dcu-llm`) | `out/<run>/evaluations/<u>/<P0n>.json` (평가+AI-usage 형제 필드) + `reports/<u>/<P0n>.md` (사람용) + `_meta/summary.csv` |
| 3 | **`eval-dashboard`** | 위 두 결과를 통합해 보여주는 GUI. 사이드바에서 강의/과제 선택 → 매트릭스 + 셀 상세. 정성평가 트리거(SSE 진행률) + 글로벌 GPU 큐 | FastAPI (`:8001`) + React 19 + Vite + TS + Tailwind (`:5173`) | (런타임 — 별도 산출물 없음) |

## 2. 3개 프로젝트가 연결되는 방식

```
                  PostgreSQL (oj-postgres-dev)
                          │ SELECT only
                          │
       ┌─────────────────────────────────┐
       │                                 │
       ▼                                 ▼
┌──────────────────────┐         ┌──────────────────────┐
│ lecture-code-review  │         │ eval-dashboard       │
│  (CLI)               │         │  backend             │
│  --lecture-id 388    │         │  (FastAPI)           │
│  --contest-id 6181   │         │                      │
└──────────┬───────────┘         └──────────┬───────────┘
           │ 디스크 export                       │ subprocess
           ▼                                 │
   out/<run>/                              │
   ├── _meta/                              │
   │   ├── lecture.json                    │
   │   ├── contest.json                    │
   │   ├── problems/<P0n>.json             │
   │   ├── final_submissions.csv           │
   │   └── students.csv                    │
   ├── codes/...                           │
   └── final_codes/<u>/<P0n>.<ext> ◀───┐   │
                                       │   │
                ┌──────────────────────┼───┘
                │ subprocess (CLI)     │
                ▼                      │
        ┌──────────────────────┐       │
        │ llm-code-review      │       │
        │  (CLI)               │       │
        │  --input <run>       │───────┘ read
        │  --problem P01       │
        │  --username <u>      │
        └──────────┬───────────┘
                   │ Qwen3.5-35B (onprem) HTTP
                   ▼
        out/<run>/evaluations/<u>/<P0n>.json  ◀──┐
                                                  │
                                                  │ disk read
                                                  │
                                       ┌──────────┴───────────┐
                                       │ eval-dashboard      │
                                       │  backend ↔ frontend │
                                       │  (REST + SSE)       │
                                       └──────────────────────┘
```

**핵심 원칙**: 세 프로젝트는 Python 모듈 import 로 결합되지 않습니다. 오직 **CLI subprocess + 디스크 파일 + DB read** 로만 연결되어 있어, DCUCODE 에 흡수할 때 부분적으로/단계적으로 가져갈 수 있습니다.

## 3. 데이터 흐름

### 3-1. 정량 데이터 (testcase 기반 OJ 채점 결과)

```
OJ submission 테이블  ─→  lecture-code-review SELECT  ─→  final_submissions.csv
                                                          + final_codes/<u>/<P>.<ext>
```

DCUCODE 본체에서는 이미 OJ DB 를 갖고 있으므로 lecture-code-review 의 SELECT 쿼리는 그대로 재사용 가능. 디스크에 export 하지 않고 DB → API 응답으로 바로 흘려도 됩니다.

### 3-2. 정성 데이터 (LLM 평가)

```
final_codes/<u>/<P>.<ext>  +  problems/<P>.json   (문제 메타)
                  │
                  ▼
            llm-code-review
                  │
                  ▼
         evaluations/<u>/<P>.json  ─ {
            evaluation: {
              scores: { correctness, algorithm, readability, problem_understanding },
              comments: { axis: { assessment, suggestion } },
              overall: int [0,100],          # round((sum_axes)/40 * 100)  단일 산식
              suggested_partial_score: int,  # round(total_score*(c+p)/20) 단일 산식
              ...
            },
            ai_usage_assessment: {
              likelihood_score: int [0,100],
              confidence: low|medium|high,
              signals: [...], counter_signals: [...],
              summary: ..., disclaimer: ...
            }
         }
```

평가 결과 자체가 디스크에 영구 저장되어 있어 캐시 역할을 함. 같은 (user, problem) 을 다시 호출해도 결과 재사용.

### 3-3. 통합 (대시보드)

eval-dashboard backend 는:
- 정량: PostgreSQL 직결로 즉시 가져옴
- 정성: 디스크 `evaluations/<u>/<P>.json` 을 읽어 매트릭스 셀에 합쳐줌
- 누락: 셀에 정성 결과가 없으면 null → 프론트가 빈 배지로 표시

## 4. 핵심 설계 결정 (왜 그렇게 했는지)

### 4-1. 점수 산식 단일 원천 + 후처리 재계산

LLM 이 응답에 `overall` 과 `suggested_partial_score` 를 자체 계산해서 보내주지만, 백엔드는 그 값을 신뢰하지 않고 `rubric.overall_score()` / `partial_score()` 함수로 **무조건 재계산해서 덮어씁니다**. 모델값과 계산값 차이는 `evaluation.recomputed` 필드에 기록.

이유: LLM 이 산식을 가끔 어긴다. 점수 일관성이 시스템 전체에서 보장되어야 학생/교수가 신뢰할 수 있음. (검증: P01·P05·P07 39 evaluation 모두 산식 일치, V1)

### 4-2. 코멘트는 `{assessment, suggestion}` nested 강제

이유: 평면 string 으로 두면 "가독성이 떨어진다" 같은 추상 평가만 나옴. 두 키로 강제 분리하니 모델이 자동으로 "현재 상태" + "개선 방향" 을 작성하게 됨. 1-shot 예시도 프롬프트에 박았음.

### 4-3. AI 사용 가능성은 별도 LLM 호출

같은 호출에 묶으면 AI 탐지 판단이 정성평가 점수에 새어들어갈 수 있음. 별도 호출 → `evaluation` 과 형제 레벨 (`ai_usage_assessment`) 로 저장. 점수 계산 경로와 완전히 분리. `counter_signals` 필드 필수 (한쪽 관점으로만 추론 안 하도록).

### 4-4. 글로벌 GPU 큐 + 동일 contest 합치기

운영 시: 여러 사용자가 동시에 정성평가 요청, GPU 는 1곳, 동시 처리 가능 세션 ~3개.

- `BoundedSemaphore(N)` + FIFO pending list
- 같은 contest 두 번 요청 → 하나의 job 으로 합침 (`requester_ids` 에 누적). 양쪽 SSE 모두 받음. GPU 시간 낭비 0.
- `force=true` 는 항상 새 job (기존 결과 `out_archive/` 로 백업).

### 4-5. SSE async generator + history replay

진행 상황을 EventSource 로 push. 핵심:
- 자식 Python 의 stdout 이 block-buffered 라 `python -u` + `PYTHONUNBUFFERED=1` 로 line-buffered 강제 (이거 안 하면 progress 라인이 4KB 또는 종료 시까지 안 옴)
- SSE generator 는 `async` (`asyncio.Queue` per subscriber) — sync `queue.get` 으로 만들면 uvicorn thread pool 고갈로 health check 도 hang
- Job 별 `history` 버퍼 — 늦게 SSE 연결한 클라이언트도 이전 이벤트 전부 replay. 페이지 새로고침/재방문 시 진행 상황 복원.

### 4-6. 프로젝트 격리

세 프로젝트는 서로 Python 모듈 import 안 함. CLI subprocess + 디스크 파일 / DB read 로만 결합. 이유: DCUCODE 에 가져갈 때 부분적으로 가져가도 동작 보장됨. 한 프로젝트 변경이 다른 프로젝트를 깨뜨리지 않음.

## 5. 검증된 정량 지표

| 검증 | 결과 |
|---|---|
| 정량: lecture 388 / contest 6181 / 문제 7개 / 학생 38 | 매트릭스 정상 표시, 모든 셀 testcase 점수 표기 |
| 정성: P01·P05·P07 39 evaluation, 4축 + AI-usage | 100% 성공 (실패 0), 산식 일관성 39/39 일치, 반복성 axis stdev 0~0.58 |
| AI-usage 대조군: 사람 작성 reference solution P01 vs 학생 평균 | refsol likelihood=15 < 학생 평균 26.2 (false positive 없음) |
| GPU 큐: 5개 contest 동시 트리거 | 3개 running + 2개 queued, 슬롯 해제 시 자동 promote, queue-update broadcast |
| 동일 contest 합치기 | 두 번째 요청자가 같은 job 의 SSE 에 합류 (`joined_existing=true`), GPU 호출 1번만 |
| GUI 상태 복원 | contest A → B → A 이동 시 history replay 로 progress 자동 복원 |

## 6. 자세한 내용을 어디서 찾을지

| 주제 | 위치 |
|---|---|
| OJ DB 스키마 (`lecture`, `contest`, `submission`, `problem`, `lecture_signup_class`) | [`01-backend.md`](./01-backend.md) + lecture-code-review/src/lecture_code_review/queries.py |
| LLM 게이트웨이 (Qwen onprem) | [`01-backend.md`](./01-backend.md) §"LLM 게이트웨이 통합" + sideproject/dcu_llm |
| 정성 평가 프롬프트 / 산식 / 4축 체크리스트 | llm-code-review/src/llm_code_review/{prompt.py, rubric.py} |
| AI 사용 가능성 평가 프롬프트 / 스키마 | llm-code-review/src/llm_code_review/ai_usage.py |
| eval-dashboard backend 진입점 | eval-dashboard/backend/src/eval_dashboard/main.py |
| eval-dashboard 핵심 동작 (큐, SSE) | eval-dashboard/backend/src/eval_dashboard/eval_runner.py |
| eval-dashboard 프론트 진입 | eval-dashboard/frontend/src/App.tsx |
| 페이즈별 작업 이력 | 각 프로젝트의 `PHASES.md` |

## 7. 한계 / 비범위

- **인증 없음**: `X-Requester` 는 단순 식별자(브라우저 localStorage uuid). 위변조 가능. 신뢰 모델은 "내부 LAN".
- **큐 in-memory**: 백엔드 재시작 시 진행 중 job + 큐 손실 (실행 중 subprocess 도 같이 죽음). Redis/Celery 같은 영속 큐 없음.
- **Cancel API 없음**: 큐에 들어간 job 은 끝까지 실행.
- **단일 GPU 슬롯 풀**: 한 endpoint 가정. 멀티 GPU 라우팅 없음.
- **테스트 자동화 미비**: 수동 검증 위주. unit test 없음.
- **전체 대기열 보기 UI 없음**: 본인 job + 글로벌 GPU 슬롯 점유 정도만 노출.
