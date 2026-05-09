# 09 · DCUCODE 본체로 이식 가이드

> 본 문서는 사이드 프로젝트로 만든 평가 시스템을 **DCUCODE 본체에 흡수**할 때의 단계적 가이드입니다. 의사결정 기준 + 코드 매핑 + 단계별 작업 목록.

읽기 전 권장:
- [`07-eval-system-summary.md`](./07-eval-system-summary.md) — 전체 그림
- [`08-api-and-events.md`](./08-api-and-events.md) — 정확한 계약
- [`01-backend.md`](./01-backend.md) — DCUCODE 본체 Django 구조 (lecture/qna/llm 앱 위치)

---

## 1. 통합 옵션 비교

세 프로젝트 (lecture-code-review / llm-code-review / eval-dashboard) 를 DCUCODE 안으로 가져오는 방법은 크게 세 가지입니다. 어느 방향이든 **세 프로젝트가 disk + DB + CLI 만으로 결합되어 있어 점진적 흡수가 가능**합니다.

### 옵션 A: **사이드카 그대로 운영 + DCUCODE 가 dashboard 만 호출**

DCUCODE 본체에는 메뉴/링크만 추가하고, eval-dashboard 는 별도 서비스(`localhost:8001`) 로 계속 운영. iframe 임베드 또는 새 창으로 띄움.

| 장점 | 단점 |
|---|---|
| DCUCODE 코드 변경 최소 | 별도 프로세스 운영 부담 (uvicorn, vite) |
| 사이드 프로젝트 그대로 사용, 검증된 동작 그대로 | DCUCODE 인증/세션 통합 어려움 (별도 X-Requester) |
| 빠르게 시작 가능 | 사용자 입장에서 두 시스템처럼 보임 |

→ **PoC / 시범 운영용으로 적합.**

### 옵션 B: **백엔드 흡수 + 프론트는 DCUCODE 의 OJ Vue 안으로**

eval-dashboard backend 의 핵심 로직(스코어보드 합성, 큐, SSE)을 DCUCODE 본체 Django 에 새 앱(예: `eval`)으로 추가. 프론트는 DCUCODE 의 Vue OJ admin 영역에 새 라우트로 옮김.

| 장점 | 단점 |
|---|---|
| 인증/권한이 DCUCODE 의 Django session/JWT 와 통합됨 | 변환 비용 큼 (FastAPI → Django, React → Vue) |
| 운영 프로세스 단일화 | 큐/SSE 재구현 필요 (Django Channels 등) |
| DCUCODE 운영 도구로 자연스럽게 보임 | DCUCODE 가 Django 2.1.7 / Vue 2.6 / Webpack 3 — 구버전 호환 부담 |

→ **장기 운영 통합용. 가장 권장.**

### 옵션 C: **하이브리드 — backend 만 흡수, eval-dashboard frontend 는 DCUCODE Vue 에서 iframe**

Django 에 평가 트리거·SSE 만 추가하고, 프론트는 React 로 만든 eval-dashboard frontend 를 그대로 써서 DCUCODE Vue 페이지에 iframe 으로 임베드.

| 장점 | 단점 |
|---|---|
| 인증은 Django 와 통합 | iframe 은 부드럽지 않은 UX |
| 프론트 재작성 부담 없음 | DCUCODE-eval-dashboard 양쪽 관리 |

→ **중기 절충안.**

**권장**: 옵션 A 로 시작 (사이드카 운영) → 사용자 피드백 수집 → 옵션 B 로 전환 (장기).

---

## 2. DCUCODE Django 앱 매핑

옵션 B 를 가정한 매핑입니다 (옵션 A 도 backend 진입점을 어디로 둘지 참고).

### 새 Django 앱: `eval` 또는 `qualitative_eval`

위치: `DCU_Online_Judge_Backend/eval/` (또는 `qualitative_eval/`).

```
eval/
├── __init__.py
├── apps.py
├── models.py            # 새 모델 — 본 가이드 §5 참고. (또는 디스크 파일만 사용해 모델 0개)
├── urls/
│   └── oj.py            # /api/eval/... 라우트
├── views/
│   ├── nav.py           # eval-dashboard 의 api/nav.py 에 대응
│   ├── scoreboard.py    #               api/scoreboard.py
│   └── eval_trigger.py  #               api/eval.py
├── services/
│   ├── queries.py       # SQL → Django ORM 으로 변환 (lecture-code-review/queries.py)
│   ├── eval_store.py    # llm-code-review out/ 디스크 read
│   ├── eval_runner.py   # GpuScheduler + subprocess
│   └── prompt_rubric/   # llm-code-review/{prompt,rubric,ai_usage}.py 흡수
└── tests.py
```

### 기존 DCUCODE 앱과의 관계

| DCUCODE 기존 앱 | eval 앱과의 관계 |
|---|---|
| `lecture` | `Lecture`, `signup_class`, `ta_admin_class` 모델을 ORM 으로 직접 import 해서 사용 (이미 같은 DB) |
| `contest` | `Contest`, `Contest.lecture_id`, `Contest.lecture_contest_type` 사용 |
| `submission` | `Submission` ORM 으로 정량 점수 가져옴. 디스크 export 단계 생략 가능 |
| `problem` | `Problem` ORM 으로 메타 가져옴 (description, samples, total_score, difficulty 등) |
| `account.User` | `requester_id` 자리에 `request.user.id` (또는 `username`) 사용 — 인증 통합 |
| `llm` | DCUCODE 의 `llm` 앱이 이미 LLM 게이트웨이 추상화를 갖고 있음. 정성평가도 그 게이트웨이 재사용 가능 (자체 호출 vs 게이트웨이 통일은 운영 결정) |

---

## 3. 핵심 모듈 → DCUCODE 매핑

### 3-1. SQL 쿼리 → Django ORM

`lecture-code-review/src/lecture_code_review/queries.py` 와 `eval-dashboard/backend/src/eval_dashboard/queries.py` 의 raw SQL 들 (`list_years`, `list_lectures`, `list_contests`, `list_problems`, `list_students`, `list_final_submissions`, `get_submission_code`).

ORM 변환 패턴:

```python
# raw SQL
SELECT DISTINCT year FROM lecture WHERE status = true ORDER BY year DESC

# Django ORM 등가
from lecture.models import Lecture
Lecture.objects.filter(status=True).values_list("year", flat=True).distinct().order_by("-year")
```

가장 까다로운 것: `list_final_submissions` 의 `ROW_NUMBER() OVER (PARTITION BY user_id, problem_id ORDER BY create_time DESC)`. Django 4+ 라면 `Window` 함수 사용 가능. DCUCODE 는 Django 2.1.7 이라 — raw SQL 그대로 쓰는 게 가장 단순:

```python
from django.db import connection
with connection.cursor() as cur:
    cur.execute("WITH ranked AS ( ... ROW_NUMBER() OVER ... ) SELECT ... WHERE rn=1 ...", [lecture_id, contest_id])
    rows = cur.fetchall()
```

### 3-2. 디스크 파일 vs DB 영속화

현재 평가 결과는 `llm-code-review/out/<run>/evaluations/<u>/<P>.json` 으로 디스크 저장. DCUCODE 흡수 시 두 가지 선택:

**A. 디스크 그대로 두기**: 가장 빠르고 검증됨. 디렉토리 경로만 settings 화. 백업·복원 단순.

**B. DB 테이블로 옮기기**: `eval_evaluation`, `eval_ai_usage` 같은 새 테이블. 동시성·쿼리·인덱싱 강함. ORM 으로 통합 검색.

→ **권장 단계**: 우선 디스크 유지 (A) 로 옮기고, 일정 기간 운영 후 통계/검색 요구가 강해지면 DB(B) 로 마이그레이션. 디스크 → DB 마이그레이션 스크립트는 단순 (json 파일 순회 → bulk_create).

### 3-3. SSE / 큐 → Django Channels

eval-dashboard 의 핵심: `asyncio.Queue` per subscriber + history replay + `BoundedSemaphore` 큐.

DCUCODE 가 Django 인 경우 SSE 는 두 가지 길:

- **`django-eventstream`** (가장 단순) — view 에서 yield. ASGI 서버 필요 (uvicorn/daphne).
- **Django Channels + WebSocket** — 양방향 필요해지면 자연스러움.

큐 자체는 그대로 가져와도 됨 (`BoundedSemaphore + threading.Thread`). Django app 의 `apps.py` 의 `ready()` 에서 scheduler 인스턴스 생성. 다만 Django 가 multi-worker(gunicorn workers > 1) 로 띄워져 있으면 **각 worker 가 별도 큐를 가지므로** Redis-backed 큐로 옮겨야 함:

- gunicorn `--workers 1 --threads N` 으로 운영 → 현재 in-memory 큐 그대로 사용 가능
- multi-worker → Celery/RQ + Redis broker 필수

DCUCODE production deploy 의 worker 설정 확인 필요 ([`04-deploy.md`](./04-deploy.md) 참조).

### 3-4. 인증 / requester

- `X-Requester` 헤더 → DCUCODE 의 `request.user` 로 대체
- `Job.requester_ids: list[str]` → `list[int]` (User PK) 로 변경
- 권한: `request.user.admin_type` 가 `ADMIN`/`SUPER_ADMIN`/`TA_ADMIN` 인지 체크 (이미 DCUCODE 에 데코레이터 있음 — `account/decorators.py` 참고)
- 학생 노출 금지: 정성평가 트리거 + 매트릭스 보기는 교수/TA 만

### 3-5. CLI subprocess

eval-dashboard backend 가 lecture-code-review/llm-code-review CLI 를 subprocess 로 띄움. DCUCODE 흡수 시 두 길:

- **subprocess 그대로 유지**: 격리·재시작 단순. lecture/llm-code-review 코드는 그대로 두고 paths 만 settings 화.
- **모듈 import 로 흡수**: 빠른 호출. 장점: subprocess 오버헤드 없음. 단점: lecture-code-review/llm-code-review 가 Django 앱 안으로 흡수돼야 함 (또는 path-based dependency).

→ **권장**: lecture-code-review 는 ORM 으로 완전히 대체 (subprocess 제거). llm-code-review 는 그대로 subprocess 유지하거나 모듈 import. progress 라인 파싱은 그대로.

### 3-6. 프론트 (옵션 B 진행 시)

DCUCODE 의 Vue OJ admin 라우터(`Frontend/src/pages/admin/router.js`) 에 `EvalDashboard` 신규 라우트 추가. 컴포넌트 구조:

| eval-dashboard React 컴포넌트 | Vue 변환 |
|---|---|
| `App.tsx` (h-screen flex 3-column) | 페이지 컨테이너 컴포넌트 |
| `Sidebar.tsx` (4단 select) | iview/element-ui select 4개 |
| `MyJobsBanner.tsx` | 같은 패턴 (TanStack Query → Vuex/axios polling) |
| `Scoreboard.tsx` (학생×문제 매트릭스) | echarts 또는 plain table. DCUCODE 가 echarts 이미 사용 |
| `DetailPanel.tsx` (slide-in) | iview Drawer 컴포넌트 |
| `EvalControls.tsx` (버튼 + ProgressBar + SSE) | EventSource 그대로, iview Progress |

프론트 재작성 시 핵심 로직(상태 머신, history replay 처리) 은 동일. DCUCODE Webpack 3 / Vue 2.6 호환만 주의.

---

## 4. 단계별 작업 (옵션 B 가정)

### Phase 0: 결정

- [ ] 통합 옵션 (A/B/C) 선택
- [ ] 평가 결과 영속화 방식 (디스크 유지 vs DB 이전) 결정
- [ ] LLM 호출 방식 (자체 vs DCUCODE llm 앱 게이트웨이) 결정
- [ ] gunicorn worker 수 검토 → in-memory 큐 가능 여부

### Phase 1: 백엔드 흡수 (Django app 신설)

- [ ] `Backend/eval/` 앱 생성, `INSTALLED_APPS` 에 등록
- [ ] `services/queries.py` — raw SQL 또는 ORM 으로 정량 데이터 조회 함수 작성 (lecture-code-review/queries.py 참고)
- [ ] `services/eval_store.py` — 디스크 read 그대로 가져옴 (옵션 결정에 따라)
- [ ] `services/eval_runner.py` — `GpuScheduler` + `_run_job` 그대로 가져옴, requester_id 를 User PK 로 변경
- [ ] `services/prompt_rubric/` — llm-code-review/{prompt,rubric,ai_usage,llm,evaluator}.py 흡수
- [ ] `views/scoreboard.py` — `/api/eval/contests/{id}/scoreboard` 등 엔드포인트, [`08-api-and-events.md`](./08-api-and-events.md) 의 스키마와 동일하게
- [ ] `views/eval_trigger.py` — POST + SSE. SSE 는 `django-eventstream` 또는 ASGI streaming 으로
- [ ] CSRF/Auth: `@login_required` + admin_type 체크

### Phase 2: 프론트 흡수

- [ ] `Frontend/src/pages/admin/views/eval/` 디렉토리 생성
- [ ] React 컴포넌트들을 Vue 2 로 변환 (위 표 참고)
- [ ] EventSource 는 그대로 사용 (브라우저 native API)
- [ ] 매트릭스 셀 색상·배지 로직 그대로 (Tailwind → 직접 CSS)
- [ ] DCUCODE admin 라우터에 등록

### Phase 3: 검증

본 사이드 프로젝트에서 통과한 검증 시나리오를 동일하게 재현:

- [ ] lecture 388 / contest 6181 (38명, 7문제) 매트릭스 표시
- [ ] 셀 클릭 → 코드 + 정성 + AI-usage 상세
- [ ] 정성평가 트리거 → SSE 진행 → done 후 매트릭스 갱신
- [ ] 동일 contest 두 사용자 동시 트리거 → 합치기 동작
- [ ] 5개 contest 동시 트리거 → 큐 진입 + 순차 실행
- [ ] 다른 contest 로 이동 후 돌아왔을 때 history replay 로 진행 상태 복원

### Phase 4: 운영 정착

- [ ] gunicorn worker 1 / threads N 설정 (in-memory 큐 안전)
- [ ] LLM 자격증명 보관 위치 결정 (env vs `/data/config/llm_gateway_api_key`)
- [ ] 디스크 정리 정책 (out/ 디렉토리 quota, archive 압축 주기)
- [ ] 모니터링 — gunicorn access log + eval_runner subprocess 종료 로그
- [ ] 사용자 가이드 / TA 매뉴얼

---

## 5. 새로 만들 모델 (옵션 B + DB 영속화 시)

```python
# Backend/eval/models.py

class EvalRun(models.Model):
    """One run = one (lecture, contest, started_at). 디스크 캐시 대신 DB 보관 시."""
    id = models.AutoField(primary_key=True)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    n_evaluated = models.IntegerField(default=0)
    n_failed = models.IntegerField(default=0)
    rubric_version = models.CharField(max_length=32, default="v1")

    class Meta:
        db_table = "eval_run"
        indexes = [models.Index(fields=["lecture", "contest", "-started_at"])]


class EvalEvaluation(models.Model):
    """학생 × 문제 단위 정성 평가."""
    run = models.ForeignKey(EvalRun, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    submission_id = models.TextField()             # final 제출 id (FK 안 거는 이유: cascade 부담)
    scores = JSONField()                           # {correctness, algorithm, readability, problem_understanding}
    comments = JSONField()                          # {axis: {assessment, suggestion}}
    overall = models.IntegerField()
    suggested_partial_score = models.IntegerField()
    summary = models.TextField()
    model_used = models.CharField(max_length=128)
    llm_latency_ms = models.IntegerField()
    error = models.TextField(null=True, blank=True)
    raw_response = models.TextField(blank=True)

    class Meta:
        db_table = "eval_evaluation"
        unique_together = [("run", "user", "problem")]
        indexes = [
            models.Index(fields=["user", "problem"]),
            models.Index(fields=["run", "user"]),
        ]


class EvalAiUsageAssessment(models.Model):
    """별도 LLM 호출의 결과 — 점수에 영향 X, 채점자 참고용."""
    evaluation = models.OneToOneField(EvalEvaluation, on_delete=models.CASCADE, related_name="ai_usage")
    likelihood_score = models.IntegerField()       # 0-100
    confidence = models.CharField(max_length=8)    # low|medium|high
    signals = JSONField()                          # [{category, observation, weight}]
    counter_signals = JSONField()                  # ["..."]
    summary = models.TextField()
    disclaimer = models.TextField()
    model_used = models.CharField(max_length=128)
    llm_latency_ms = models.IntegerField()
    error = models.TextField(null=True, blank=True)
    raw_response = models.TextField(blank=True)

    class Meta:
        db_table = "eval_ai_usage"
```

마이그레이션: `python manage.py makemigrations eval && python manage.py migrate eval`.

디스크 → DB 마이그레이션 스크립트 (`management/commands/migrate_evaluations_from_disk.py`):

```python
from pathlib import Path
import json
class Command(BaseCommand):
    def handle(self, **kw):
        out = Path(settings.LLM_CR_DIR) / "out"
        for run_dir in out.iterdir():
            # parse "lecture-388_contest-6181"
            parts = run_dir.name.split("_")
            lecture_id = int(parts[0].split("-")[1])
            contest_id = int(parts[1].split("-")[1])
            run = EvalRun.objects.create(lecture_id=lecture_id, contest_id=contest_id)
            for ev_path in (run_dir / "evaluations").rglob("*.json"):
                d = json.loads(ev_path.read_text(encoding="utf-8"))
                # ... bulk_create
```

---

## 6. 주의 사항

- **PostgreSQL 직결 SQL 의 `"user"` 따옴표**: `user` 가 예약어라 raw SQL 시 큰따옴표 필수. ORM 사용 시 자동.
- **Django 2.1.7 의 JSONField**: `django.contrib.postgres.fields.JSONField` 사용 (Django 3.1+ 의 `models.JSONField` 안 됨). 이미 DCUCODE 본체가 사용 중 (`utils/models.py JSONField`).
- **subprocess + `python -u` + `PYTHONUNBUFFERED=1`**: 둘 다 빼면 progress 라인이 4KB 채워질 때까지 안 옴. 반드시 둘 다 유지.
- **SSE generator 는 async**: sync 로 만들면 uvicorn/daphne thread pool 고갈로 health check 도 hang. (`07-eval-system-summary.md` §4-5 참조)
- **점수 산식 단일 원천**: 모델 응답 신뢰 X. `rubric.py` 의 `overall_score()` / `partial_score()` 로 무조건 재계산. 학생/교수 노출 점수의 일관성을 보장하는 핵심.
- **AI 사용 가능성은 절대 점수에 반영 X**: 형제 필드로만 저장. UI 에 노출 시 "참고용 · 점수 미반영" 라벨 + `disclaimer` 항상 표기. 부정행위 단독 근거 금지.
- **lecture_signup_class 외 사용자**: 매트릭스에서 본 사이드 프로젝트는 signup_class 명단 + 실제 제출만 한 외부 사용자도 매트릭스 row 에 포함 (드롭아웃 학생, 청강생). DCUCODE 흡수 시 같은 정책 권장.

---

## 7. 참고 — 본 사이드 프로젝트 실측치

| 항목 | 값 |
|---|---|
| 정성평가 1건 LLM 호출 latency (Qwen3.5-35B onprem) | 평균 2~4초 |
| AI-usage 1건 LLM 호출 latency | 평균 2~3초 |
| (사용자가 정성평가만 켤 때) 1 (학생, 문제) 처리 시간 | 평균 ~3초 |
| (정성 + AI-usage 둘 다) 1 (학생, 문제) 처리 시간 | 평균 ~5초 |
| 21명 1문제 (P01) 평가 with concurrency=4, AI-usage on | ~55~65초 |
| 39명 3문제 (P01·P05·P07) 평가 | ~2분 |
| 101명 (전체 7문제, 38명) 평가 | ~5분 (62건 추가, 39건 캐시 적중일 때 ~2.5분) |

DCUCODE 운영 시 강의당 평균 35명 × 7~10 문제 가정 시, 한 contest 일괄 평가 1회당 5~8분, 슬롯 3 가정 시 동시 처리 약 3 contest. 이 정도면 일반적 채점 워크플로에 맞물려 운영 가능.
