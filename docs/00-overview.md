# 00 · 시스템 한눈에 보기

> 본 문서들의 인덱스는 [`README.md`](./README.md). 더 깊은 정보는 [`01-backend.md`](./01-backend.md), [`02-frontend.md`](./02-frontend.md), [`03-judgeserver.md`](./03-judgeserver.md), [`04-deploy.md`](./04-deploy.md), 확장 포인트는 [`05-extension-points.md`](./05-extension-points.md), 프로젝트 격리 가이드는 [`06-project-layout.md`](./06-project-layout.md).

## 구성도 (현재 가동 셋업: dev)

```
HOST (호스트에서 직접 실행, hot-reload)
├── Backend  Django runserver  :8000
│            ~/development/dcucode/DCU_Online_Judge_Backend
│            .venv 활성화, OJ_ENV=dev, JUDGE_SERVER_TOKEN env 주입
└── Frontend Webpack3 dev-server :8080
             ~/development/dcucode/DCU_Online_Judge_Frontend
             Node v8.12.0, TARGET=http://127.0.0.1:8000

DOCKER  (devstack/docker-compose.dev.yml — 인프라만 컨테이너)
├── oj-postgres-dev   127.0.0.1:5432   PostgreSQL 16.3, DB=onlinejudge
├── oj-redis-dev      127.0.0.1:6379   Redis 4.0
└── judge-server-dev  127.0.0.1:12358  snslabdocker/judge_server:latest (gunicorn)
                       BACKEND_URL=http://host.docker.internal:8000/api/judge_server_heartbeat/
                       5초 heartbeat
                       볼륨 ro: ../DCU_Online_Judge_Backend/data/test_case → /test_case

병렬 디렉토리
├── DCU_Online_Judge_Deploy        production용 docker-compose 모음 (현 dev 셋업과 별개)
├── DCU_Online_Judge_SideProjects  본 작업 공간 (git repo, 비어있음)
├── sideproject/dcu_llm            진행 중. OpenAI 호환 LLM 게이트웨이 클라이언트(uv)
└── backupdata/                    onlinejudge_backup_20260419.dump (3.1G)
                                   dcucode-data_20260503.tar (425M)
```

원본은 [QingdaoU OnlineJudge](https://github.com/QingdaoU/OnlineJudge) 포크. **DCU 커스터마이징의 핵심**은 backend의 `lecture` / `qna` / `llm` 앱과 frontend의 동명 모듈, contest 모델의 `llm_hint_enabled` 같은 LMS 지향 확장이다.

## 1차 목적 3축

이번 분석은 다음 세션에서 사이드 프로젝트 후보를 매핑하기 위해 다음 3축을 기준으로 구성되었다.

- **TA·강의 운영 워크플로 개선**
- **데이터/지표 활용**
- **학생 학습 경험 강화**

각 축에 매칭되는 코드 지점은 [`05-extension-points.md`](./05-extension-points.md) 에서 표로 정리.

## 결합도 가이드

| 유형 | 정의 | 작업 위치 |
|---|---|---|
| 강결합 | 본체 코드를 직접 수정. 마이그레이션·UI·API 추가 | `DCU_Online_Judge_Backend/` 또는 `DCU_Online_Judge_Frontend/` 본 repo PR. **Django 2.1.7 / Vue 2.6 / Webpack 3 호환성 필수** |
| 느슨한 결합 | 본체는 그대로 두고 외부에서 API/DB만 소비 | `DCU_Online_Judge_SideProjects/<프로젝트명>/` 새 디렉토리. 독립 패키지 형태 권장 |

> 사이드 프로젝트로 데이터 분석·대시보드를 만들 경우, 운영 DB를 건드리지 않도록 백업 dump를 별도 컨테이너에 복원해 read-only로 쓰는 구조가 가장 안전하다.

## 빠른 헬스체크

```bash
# Backend
curl -fsS http://127.0.0.1:8000/api/website | head

# JudgeServer
curl -fsS http://127.0.0.1:12358/ping

# DB heartbeat 도달 (backend .venv 활성화 후)
python manage.py shell -c "from conf.models import JudgeServer; \
[print(j.hostname, j.status, j.last_heartbeat) for j in JudgeServer.objects.all()]"

# 환경변수
env | grep -E 'LLM_GATEWAY|JUDGE_SERVER_TOKEN'
```
