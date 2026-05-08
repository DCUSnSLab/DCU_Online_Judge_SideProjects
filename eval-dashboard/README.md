# eval-dashboard

`lecture-code-review` (DB → 디스크) + `llm-code-review` (정성·AI-usage 평가) 결과를 통합해 보여주는 GUI 대시보드. 별도 프로젝트로, 두 기존 프로젝트와는 **CLI subprocess + 디스크/DB read** 로만 결합한다 (Python 모듈 import 안 함).

> 본 프로젝트는 페이즈 단위로 진행. 진행상황은 [`PHASES.md`](./PHASES.md) 참고.

## 스택

- Backend: **FastAPI** + psycopg + sse-starlette (Python 3.10+)
- Frontend: **React 18 + Vite + TypeScript + Tailwind + shadcn/ui** + TanStack Query
- 통신: REST + Server-Sent Events (정성평가 진행)

## 디렉토리

```
eval-dashboard/
├── backend/    FastAPI 앱 — :8001
└── frontend/   Vite dev — :5173
```

각 하위 디렉토리는 자체 의존성 (venv / node_modules) 격리.

## 빠른 시작

```bash
# 1. Backend
cd eval-dashboard/backend
python3 -m virtualenv .venv
.venv/bin/pip install -e .
cp .env.example .env  # PG_DSN, LECTURE_CR_DIR, LLM_CR_DIR 확인
.venv/bin/uvicorn eval_dashboard.main:app --reload --port 8001

# 2. Frontend (다른 터미널)
cd eval-dashboard/frontend
npm install
npm run dev   # http://localhost:5173
```

## 주요 화면

좌측 사이드바(년도/학기/과목/과제 선택) + 메인 매트릭스(학생×문제 점수표) + 우측 슬라이드 패널(클릭한 행/열/셀의 상세). 단일 페이지·페이지 이동 없음.

정성평가는 사이드바의 **'정성평가'** 버튼 → 서버측 subprocess 실행 → SSE 진행률 → 완료 후 매트릭스에 정성·AI-usage 컬럼 채워짐. 이미 평가된 항목은 캐시 재사용. **'재평가'** 버튼은 강제 재실행.

## 약속

- OJ 본체 코드·DB 변경 없음 (DB는 SELECT 만).
- `lecture-code-review` / `llm-code-review` 의 출력 디렉토리는 read-only (단, force 재평가 시 `out_archive/` 로 이동).
- 두 기존 프로젝트의 Python 모듈 import 안 함 — CLI/디스크로만 결합.
