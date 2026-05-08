# DCUCODE 사이드 프로젝트 — 시스템 분석 문서

이 디렉토리는 `~/development/dcucode/` 의 DCU Online Judge(이하 OJ) 위에서 운영할 사이드 프로젝트들을 위한 **참조용 시스템 지도**다. 모든 사이드 프로젝트가 공유하는 자료 영역이며, 프로젝트 코드와 섞지 않는다.

> **프로젝트 격리 원칙** — 각 사이드 프로젝트는 `DCU_Online_Judge_SideProjects/<프로젝트명>/` 하위에 새 디렉토리를 만들어 진행한다. 의존성(venv, node_modules, .env, lockfile, README 등)은 프로젝트 디렉토리 안에 자체 보관한다.

## 문서 인덱스

| 파일 | 내용 |
|---|---|
| [`00-overview.md`](./00-overview.md) | 시스템 한눈에 보기 — 호스트/Docker 구성도, 컴포넌트 위치, 1차 목적 3축, 결합도 가이드 |
| [`01-backend.md`](./01-backend.md) | Django 앱 구성, DCU 커스텀(`lecture`/`qna`/`llm`), 설정·의존성, 채점 디스패치, LLM 게이트웨이 |
| [`02-frontend.md`](./02-frontend.md) | Vue 프로젝트 OJ/Admin 분리, 라우트, API 모듈, 빌드, WebSSH 게이트웨이, 보조 스크립트 |
| [`03-judgeserver.md`](./03-judgeserver.md) | JudgeServer HTTP API, 토큰 인증, heartbeat, 채점 시퀀스, 테스트케이스/SPJ, sandbox |
| [`04-deploy.md`](./04-deploy.md) | Deploy compose 비교, 현재 가동 중인 devstack 셋업, scripts, sideproject/dcu_llm, backupdata |
| [`05-extension-points.md`](./05-extension-points.md) | 1차 목적 3축별 확장 포인트 인덱스 — 파일경로 + 결합도 표기 |
| [`06-project-layout.md`](./06-project-layout.md) | 사이드 프로젝트 격리 원칙과 권장 디렉토리 레이아웃 |

## 1차 목적 3축 (사이드 프로젝트 후보 매핑용)

- **TA·강의 운영 워크플로 개선** — 강의/과제/QnA/배치 관리 등 운영 효율화
- **데이터/지표 활용** — submission 로그, LLM 감사 로그, 랭킹 데이터 분석·시각화
- **학생 학습 경험 강화** — AI 힌트 고도화, 자동 피드백, 진척도 시각화, Web IDE 등

## 다음 세션 가이드

1. [`05-extension-points.md`](./05-extension-points.md) 의 확장 포인트 표를 보고 운영하고 싶은 사이드 프로젝트 N개를 결정한다.
2. 각 프로젝트마다 결합도(강결합 / 느슨한 결합)를 정한다 — [`06-project-layout.md`](./06-project-layout.md) 참고.
3. `DCU_Online_Judge_SideProjects/<프로젝트명>/` 새 디렉토리를 만들고, 그 안에 자체 README와 plan 문서를 작성하면서 진행한다.
4. 본 `docs/` 는 읽기 전용 참조 자료로 사용 — 프로젝트별 결정/구현 내용은 각 프로젝트 디렉토리 안에 보관한다.
