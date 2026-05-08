# 05 · 확장 포인트 인덱스

다음 세션에서 사이드 프로젝트 후보를 결정할 때 참고할 표. 1차 목적 3축별로, 본체 어느 지점에 손을 대거나 어느 데이터/엔드포인트를 끌어다 쓸지 미리 짚어둔다.

> 결합도: **강** = 본체 코드 수정/PR 필요, **느슨** = `DCU_Online_Judge_SideProjects/<name>/` 안에서 API/DB 소비. 자세한 구조는 [`06-project-layout.md`](./06-project-layout.md).

## A. TA·강의 운영 워크플로 개선

| 확장 포인트 | 위치 | 결합도 |
|---|---|---|
| `lecture` 앱 모델 (`Lecture` / `signup_class` / `ta_admin_class`) | `Backend/lecture/models.py` | 강 / 느슨 둘 다 |
| 매일 5AM UTC `migrateLecture` 크론 | `Backend/oj/settings.py:61-62` (`utils.DBTasks.migrateLecture`) | 강 |
| `Submission.lecture` FK | `Backend/submission/models.py:47` | 데이터 소비(느슨) |
| 코드 열람 권한 `is_user_in_lecture_ta_admin_class()` | `Backend/submission/models.py:50` | 느슨 (참고) / 강 (확장 시) |
| `qna` 앱 (`Post`/`Comment`, TA·교수 권한 `permit`) | `Backend/qna/models.py`, `Backend/qna/views/`, `Backend/qna/views.py` | 강 / 느슨 둘 다 |
| Admin BatchMigrate (슈퍼어드민) | `Frontend/src/pages/admin/router.js`, 대응 backend 엔드포인트 | 강 |
| Admin CopyKiller (표절 탐지) | 동상 | 강 (확장) / 느슨 (외부 도구로 결과만 임포트) |
| 운영 자동화 출발점 (백업·복원·재시작) | `DCU_Online_Judge_Deploy/scripts/{getDB.sh,rstJudgeserver.sh,qna_restore.sql}`, `devstack/scripts/{start.sh,stop.sh,00_restore_backup.sh}` | 느슨 (운영 도구) |

> **TA 워크플로 사이드 프로젝트 후보 영역**: 강의/수강생/TA 배정 자동화, QnA triage 도구, 표절 탐지 결과 가공/리포트, 학기 일괄 마이그레이션 도구.

## B. 데이터·지표 활용

| 확장 포인트 | 위치 | 결합도 |
|---|---|---|
| `Submission` 테이블 | `Backend/submission/models.py` | DB 직결(읽기) / API |
| `LLMAuditLog` (요청·응답·토큰) | `Backend/llm/models.py` | DB 직결(읽기) |
| `LLMChatSession` / `LLMChatMessage` | 동상 | DB 직결(읽기) |
| Contest 랭킹 / `update_contest_rank()` | `Backend/judge/dispatcher.py` (호출부), `Backend/contest/` | API / DB |
| `Lecture` + `signup_class` 통계 | `Backend/lecture/models.py` | DB / API |
| Frontend echarts 시각화 | `Frontend/src/pages/oj/views/`, `Frontend/src/pages/admin/views/` | 강 (동일 UI 안에 추가) |
| 운영 DB 분리용 백업 dump | `backupdata/onlinejudge_backup_20260419.dump` (3.1G), `backupdata/dcucode-data_20260503.tar` (425M) | 느슨 (분석용 별도 PG에 복원) |

> **데이터 분석 사이드 프로젝트 후보 영역**: 학생 진척도 대시보드, 제출 패턴/언어 분석, LLM 사용량·비용 모니터링, 문제 난이도 데이터 기반 자동 태깅, 컨테스트 후 retro 리포트.
>
> 운영 DB를 직접 read-only로 붙어도 되지만, 백업 dump를 별도 컨테이너에 복원해 사용하는 쪽이 안전하다.

## C. 학생 학습 경험 강화

| 확장 포인트 | 위치 | 결합도 |
|---|---|---|
| LLM 게이트웨이 (시스템 프롬프트, 라우팅, 키 관리) | `Backend/llm/views/oj.py` (`_build_gateway_url` line 53, `_build_gateway_payload` line 169, 게이트웨이 호출 line 339+) | 강 |
| `LLMRouteMap` 모델 (priority/weight 라우팅) | `Backend/llm/models.py` | 강 |
| Contest `llm_hint_enabled` 플래그 | `Backend/contest/models.py:31` | 강 |
| 내부 LLM API 라우트 | `Backend/oj/urls.py:30` `re_path(r"^api/internal/", include("llm.urls.internal"))` | 강 |
| OJ Chat 페이지 + Problem 4-pane 레이아웃 | `Frontend/src/pages/oj/views/chat`, `Frontend/update_layout.py` (Problem.vue 자동 변환) | 강 |
| Web SSH IDE | `Frontend/server.js` (xterm + ssh2 게이트웨이), `Frontend/src/pages/oj/views/container` | 강 / 느슨 (별도 IDE 호스팅 도구) |
| Sample test 즉시 채점 경로 | `Backend/submission/views/oj.py SubmissionAPI.post` (`sample_test_status=True`) | 강 |
| `sideproject/dcu_llm` (CLI + 라이브러리) | `sideproject/dcu_llm/` | 느슨 (재사용 가능) |
| `lecture.aihelper_status` 플래그 | `Backend/lecture/models.py` | 강 |

> **학습 경험 사이드 프로젝트 후보 영역**: AI 힌트 모드 고도화 (단계별 힌트, 코드 리뷰 모드, 오답 패턴 기반 진단), 자동 피드백 루프, 진척도/연속 출석 시각화, 별도 IDE 컨테이너 환경, sample test 결과 enriched 표시.

## 결합도 결정 가이드

| 상황 | 권장 |
|---|---|
| 본체 모델/마이그레이션 변경이 필수 | **강결합** — 본 backend repo PR. Django 2.1.7 호환 주의 |
| 본체 UI 위에서만 동작해야 자연스러움 (예: Problem 페이지 안에 위젯) | **강결합** — Vue 2.6 + Webpack 3 환경 |
| 본체 데이터/이벤트만 소비, 별도 화면/CLI 가능 | **느슨한 결합** — `SideProjects/<name>/` 새 디렉토리, 자체 의존성 |
| 운영 자동화 (백업, 모니터링, 알림) | **느슨한 결합** — 셸/Python 스크립트로 충분 |
| 분석/리포트 | **느슨한 결합** — 백업 dump 복원 후 read-only 분석 |

본체 PR이 동시에 필요한 경우, sideproject 디렉토리에는 클라이언트/도구만 두고 본체 변경은 별도 브랜치에서 진행하는 식의 분리 권장. ([`06-project-layout.md`](./06-project-layout.md))
