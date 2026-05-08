# 06 · 프로젝트 격리 원칙 / 레이아웃 가이드

> 사용자 결정 사항을 영구 문서로 고정. 모든 사이드 프로젝트는 이 원칙을 따른다.

## 원칙

각 사이드 프로젝트는 `DCU_Online_Judge_SideProjects/<프로젝트명>/` 형태로 **새 디렉토리를 만들어 격리 실행한다.**

- 의존성(venv, node_modules, .env, lockfile, 자체 README)은 프로젝트 디렉토리 내부에 자체 보관
- 다른 프로젝트의 의존성을 공유하지 않는다 (lockfile/python venv를 재사용하지 않음)
- 환경변수 충돌을 피하기 위해 각자 `.env` 사용 (글로벌 export 지양)
- `docs/` 는 모든 프로젝트가 공유하는 **참조용 자료** 영역이며, 프로젝트 코드를 두지 않는다
- 본 repo (`DCU_Online_Judge_SideProjects`) 는 git repo이므로 새 프로젝트 디렉토리도 그 안에서 관리. 다만 프로젝트별 큰 산출물(데이터·node_modules·venv)은 `.gitignore` 처리

## 권장 디렉토리 레이아웃

### Python 프로젝트

```
<project-name>/
├── README.md            # 프로젝트 개요, 실행법
├── pyproject.toml       # uv 또는 poetry
├── .python-version      # uv pin 권장
├── .venv/               # gitignore
├── .env.example
├── .env                 # gitignore
├── src/<project_name>/
│   └── ...
├── tests/
└── plan.md              # (이 프로젝트의 plan/할 일 목록)
```

### Node 프로젝트

```
<project-name>/
├── README.md
├── package.json
├── pnpm-lock.yaml or package-lock.json
├── node_modules/        # gitignore
├── .env.example
├── .env                 # gitignore
├── src/
└── plan.md
```

### 운영 스크립트/Shell 도구

```
<project-name>/
├── README.md
├── scripts/<*.sh>
├── crontab.example
└── plan.md
```

## 결합도별 권장 패턴

### 강결합 (본체 변경)

본체 backend/frontend repo PR이 필요한 경우.

- 본체 변경은 각 본 repo 브랜치에서 작업
- `DCU_Online_Judge_SideProjects/<name>/` 디렉토리에는:
  - 본체 PR 링크/브랜치 메모 (`README.md`)
  - 본체에 맞물려 동작하는 보조 도구 (예: 마이그레이션 스크립트, 데이터 생성기, 테스트 클라이언트)
  - 설계 문서/`plan.md`
- 본체 코드를 sideproject 디렉토리에 그대로 복사·수정하지 않는다

### 느슨한 결합 (외부에서 API/DB 소비)

- backend REST API 사용: `axios` / `httpx` / `requests` 로 `http://127.0.0.1:8000/api/...`
- DB 직결 (분석 한정): 가급적 `backupdata/` 의 dump를 별도 PG 컨테이너에 복원해 사용
- LLM 통합: `sideproject/dcu_llm` 라이브러리 재사용 검토 (`from dcu_llm import LLMClient`)
- 인증이 필요한 endpoint는 JWT 토큰 발급 받아 사용 (`/api/login`)

## 참고: `sideproject/dcu_llm` 의 구조

비슷한 형태의 사이드 프로젝트를 만들 때 참고할 수 있는 사례:

```
sideproject/dcu_llm/
├── README.md            # 프로필/CLI/라이브러리 사용법
├── pyproject.toml
├── .env / .env.example  # MINDLOGIC_API_KEY, ONPREM_API_KEY 등
├── .gitignore
├── .venv/
└── src/
    └── dcu_llm/         # CLI 진입점 + LLMClient 라이브러리
```

특징:
- CLI(`dcu-llm`)와 라이브러리 둘 다 노출
- 두 가지 백엔드 프로필 (mindlogic / onprem) 환경변수로 전환
- 본체 OJ에 의존하지 않음 (완전 독립)

## 새 프로젝트 시작 체크리스트

1. 프로젝트명 정하기 (kebab-case 권장)
2. `DCU_Online_Judge_SideProjects/<name>/` 디렉토리 생성
3. `README.md` 에 목적·결합도·실행법 작성
4. 결합도 결정 → 강결합이면 본체 PR 브랜치도 함께 기록
5. 자체 venv/node_modules + `.gitignore` 추가
6. `plan.md` 작성 (본 디렉토리의 [`05-extension-points.md`](./05-extension-points.md) 표를 참고하여 영향 받는 확장 포인트 명시)
7. 구현 → 본 docs/는 읽기 전용 참조로만 사용
