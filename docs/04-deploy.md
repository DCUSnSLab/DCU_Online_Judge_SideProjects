# 04 · 배포 / 보조 디렉토리

## 디렉토리 매트릭스

| 위치 | 용도 | git |
|---|---|---|
| `DCU_Online_Judge_Deploy/` | 공식 배포(QingdaoU 포크) — production용 docker-compose 모음 | YES |
| `devstack/` | **현재 가동 중인 dev 셋업** (인프라만 컨테이너) | NO |
| `sideproject/` (정확히는 `sideproject/dcu_llm/`) | 진행 중. OpenAI 호환 LLM 게이트웨이 클라이언트 | NO |
| `backupdata/` | 백업 dump 저장소 | NO |
| `DCU_Online_Judge_SideProjects/` | **본 작업 공간** (지금 우리가 있는 곳) | YES |

## DCU_Online_Judge_Deploy

| 파일 | 의도 |
|---|---|
| `docker-compose.yml` | **Production.** 6개 서비스 풀스택 (oj-redis, oj-postgres, judge-server, oj-backend, oj-frontend, nginx). 이미지: snslabdocker |
| `docker-compose-develop.yml` | **사내 harbor 기반 dev.** LLM Gateway 포함, frontend 컨테이너는 주석 처리, pgadmin4 포함, SSH 터널(5555) + backend 8000 노출 |
| `docker-compose-develop_webssh.yml` | webssh 컨테이너 포함 dev |
| `scripts/getDB.sh` | postgres 컨테이너에서 pg_dump 실행 |
| `scripts/rstJudgeserver.sh` | judge-server 컨테이너 재시작 |
| `scripts/qna_restore.sql` | QnA Post 테이블 복구용 SQL |
| `README.md` | Linux/Windows 셋업 안내, 초기 admin `root/rootroot` |

> 현재 가동 중 dev 셋업은 위 파일들이 아니라 `devstack/docker-compose.dev.yml` 이다. (인프라만 컨테이너, backend/frontend는 호스트)

## devstack — 현재 가동 셋업

### `docker-compose.dev.yml`

3개 서비스만 포함:

```yaml
services:
  oj-redis:        redis:4.0-alpine                                     127.0.0.1:6379
  oj-postgres:     junhp1234/postgresql-16.3-alpine-huge-pages:latest   127.0.0.1:5432
  judge-server:    snslabdocker/judge_server:latest                     127.0.0.1:12358
```

- judge-server `BACKEND_URL=http://host.docker.internal:8000/api/judge_server_heartbeat/`
- judge-server `extra_hosts: ["host.docker.internal:host-gateway"]`
- 볼륨: `../DCU_Online_Judge_Backend/data/test_case → /test_case (ro)`, `./data/judge_server/{log,run}`
- entrypoint: heartbeat 루프 + judge entrypoint 동시 실행

### `.env`

`JUDGE_SERVER_TOKEN` 등 dev 토큰 보관.

### `scripts/`

| 스크립트 | 용도 |
|---|---|
| `start.sh` | docker-compose up + backend/frontend 로컬 실행 가이드 |
| `stop.sh` | 컨테이너 정지 |
| `00_restore_backup.sh` | `backupdata/` 의 dump/tar 복원 자동화 |

### `data/`

호스트 볼륨 마운트 디렉토리 (postgres/redis/judge_server 데이터).

## sideproject/dcu_llm — 진행 중인 사이드 프로젝트 (참고)

| 항목 | 값 |
|---|---|
| 패키지 매니저 | uv (`pyproject.toml`, `.venv/`) |
| 형태 | CLI(`dcu-llm`) + 라이브러리(`from dcu_llm import LLMClient`) |
| 빌트인 프로필 | `mindlogic` (Mindlogic API Gateway, 기본 모델 `claude-sonnet-4-6`) / `onprem` (`https://code.cu.ac.kr/llm/v1`, 기본 모델 `Qwen/Qwen3.5-35B-A3B-FP8`) |
| 환경변수 | `<P>_API_KEY`, `<P>_BASE_URL`, `<P>_DEFAULT_MODEL` (`<P>` = `MINDLOGIC` / `ONPREM`), 기본 프로필 `DCU_LLM_PROFILE` (default `onprem`) |
| 스트리밍 지원 | `client.stream(...)` |

> **격리 원칙의 참고 사례**: dcu_llm은 OJ 본체에 손대지 않고 외부에서 LLM 게이트웨이를 호출하는 느슨한 결합 도구다. 비슷한 형태의 사이드 프로젝트는 `DCU_Online_Judge_SideProjects/<name>/` 에 같은 패턴으로 구성하면 된다. ([`06-project-layout.md`](./06-project-layout.md) 참고)

## backupdata

| 파일 | 크기 | 형태 |
|---|---|---|
| `onlinejudge_backup_20260419.dump` | 3.1 GB | PostgreSQL pg_dump (custom format) |
| `dcucode-data_20260503.tar` | 425 MB | test_case + config 등 backend 데이터 |

복원: `devstack/scripts/00_restore_backup.sh` 가 자동화. 데이터 분석 사이드 프로젝트는 운영 DB 대신 이 dump를 별도 PG 컨테이너에 복원해 read-only로 사용 권장.

## production vs 현재 dev 비교

| 영역 | production (`Deploy/docker-compose.yml`) | 현재 dev (`devstack/docker-compose.dev.yml`) |
|---|---|---|
| Backend | 컨테이너 (oj-backend) | 호스트 `.venv` + `runserver` |
| Frontend | 컨테이너 (oj-frontend) | 호스트 `npm run dev` |
| Postgres | 컨테이너 (`oj-postgres`) | 컨테이너 (`oj-postgres-dev`, 16.3) |
| Redis | 컨테이너 | 컨테이너 |
| Judge-server | 컨테이너 | 컨테이너 (`host.docker.internal` 통해 backend 접근) |
| Nginx | 포함 | 없음 (직접 :8000/:8080) |
| LLM Gateway | (production은 별도, develop compose에는 포함) | 없음 (개발 시 외부 게이트웨이 호출 또는 비활성) |
