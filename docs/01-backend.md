# 01 · Backend (Django)

루트: `/home/soobin/development/dcucode/DCU_Online_Judge_Backend`

## Django 앱 일람

| 앱 | 역할 | 핵심 파일 |
|---|---|---|
| `account` | 사용자/권한 (REGULAR_USER / ADMIN / TA_ADMIN / SUPER_ADMIN) | `account/models.py` |
| `problem` | 문제·태그 정의 | `problem/models.py` |
| `contest` | 대회/과제/실습. ACM·OI rule_type. **`llm_hint_enabled`(BooleanField, contest/models.py:31)** | `contest/models.py` |
| `submission` | 제출 레코드. **`lecture` FK (submission/models.py:47)**, `is_user_in_lecture_ta_admin_class()` (line 50) | `submission/models.py` |
| `judge` | 채점 dispatcher / dramatiq actor | `judge/dispatcher.py`, `judge/tasks.py` |
| `conf` | `JudgeServer` 모델, heartbeat 수신 | `conf/models.py`, `conf/views.py` |
| `lecture` | **DCU 커스텀.** Lecture / signup_class / ta_admin_class. 연도·학기·AI조교(`aihelper_status`) | `lecture/models.py`, `lecture/views/`, `lecture/urls/` |
| `qna` | **DCU 커스텀.** Post / Comment. Submission/Problem/Contest 참조, TA·교수 권한 | `qna/models.py`, `qna/views.py`, `qna/views/` |
| `llm` | **DCU 커스텀.** `LLMApiKey` / `LLMRouteMap` / `LLMAuditLog` / `LLMChatSession` / `LLMChatMessage` | `llm/models.py`, `llm/views/oj.py` |
| `announcement`, `options`, `heartbeat`, `fps` | 공지·옵션·헬스체크·문제 파서 | (보조) |

## 설정 파일

### `oj/settings.py`

| 항목 | 위치 | 비고 |
|---|---|---|
| 환경 분기 (`OJ_ENV`) | `oj/settings.py` 상단 | dev / production 분기 |
| Cron (`migrateLecture` 매일 5AM UTC) | `oj/settings.py:61-62` | `utils.DBTasks.migrateLecture` 호출, `>> /mnt/log/cron_log.log` |
| CACHES (Redis DB#1) | `oj/settings.py:238-240` | `utils.cache.MyRedisCache`, `redis_config(db=1)` |
| Sessions | `oj/settings.py` | `cache` 백엔드, default alias |
| DRAMATIQ_BROKER (Redis DB#4) | `oj/settings.py:245-260` | `dramatiq.brokers.redis.RedisBroker` |
| DRAMATIQ_RESULT_BACKEND (Redis DB#4) | `oj/settings.py:261-269` | RedisBackend |
| Sentry | `oj/settings.py:272+` | `SENTRY_DSN` env, production_env에서만 활성 |
| Secret key 파일 | `/data/config/secret.key` 읽음 | (init_db.sh가 생성) |
| JWT | simplejwt | 액세스 15분, 리프레시 14일 |

### `oj/dev_settings.py`

- Postgres `localhost:5432`, DB/USER `onlinejudge`
- Redis `127.0.0.1:6379`

### `oj/production_settings.py`

- 환경변수 기반: `POSTGRES_HOST` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `REDIS_HOST` / `REDIS_PORT`
- `/data` 경로 사용

## 의존성 (req.txt)

핵심:

- `Django==2.1.7` (구버전, 호환성 주의)
- `djangorestframework==3.8.2` + `djangorestframework-simplejwt==4.7.2`
- `django-dramatiq==0.5.0` + `dramatiq==1.3.0` (작업 큐)
- `django-redis==4.10.0`, `redis==3.2.0`
- `psycopg2-binary==2.7.7`
- `APScheduler==3.6.3`, `django-crontab` (스케줄)
- `pandas==1.0.3`, `numpy==1.18.2`, `XlsxWriter==1.1.5` (분석/엑셀)
- `pycryptodome==3.20.0`, `qrcode==6.1`, `otpauth==1.0.1`

## 채점 디스패치

### `judge/dispatcher.py`

- `class JudgeDispatcher` — submission을 JudgeServer에 전송
- `class ChooseJudgeServer` (context manager, line 42–54)
  - `JudgeServer.objects.select_for_update().filter(is_disabled=False).order_by("task_number")`
  - `task_number ≤ cpu_core × 2` 인 서버를 선택, 트랜잭션 보호하에 `task_number += 1`
  - 사용 후 `task_number -= 1` (line 54)
- `class DispatcherBase._request()` — `X-Judge-Server-Token` 헤더 인증
- 토큰: `hashlib.sha256(SysOptions.judge_server_token.encode("utf-8")).hexdigest()` (`dispatcher.py:59`)
- 호출: `urljoin(server.service_url, "/judge")` (line 170), `compile_spj` (line 86)

### `judge/tasks.py`

- dramatiq actor `judge_task(submission_id, problem_id)` → `JudgeDispatcher.judge()`
- Redis DB#4 큐 사용

### Heartbeat 수신

- `conf/views.py:132` `class JudgeServerHeartbeatAPI(CSRFExemptAPIView)`
- 토큰 검증: `hashlib.sha256(SysOptions.judge_server_token...).hexdigest() != client_token` (line 138)
- 갱신 필드: `judger_version`, `cpu_core`, `memory_usage`, `service_url`, `ip`, `last_heartbeat` (line 150)
- 신규 등록: `last_heartbeat=timezone.now()` (line 159)

### 토큰 저장

- `options/options.py:91` — env `JUDGE_SERVER_TOKEN` 읽음
- `OptionKeys.judge_server_token` (line 103) → `SysOptions.judge_server_token` getter/setter (line 241–246)
- `deploy/entrypoint_dev.sh` 가 env → DB 저장

## LLM 게이트웨이 통합

### `llm/views/oj.py`

| 함수/위치 | 내용 |
|---|---|
| `_read_gateway_api_key()` (line 41) | `LLM_GATEWAY_API_KEY_FILE` (기본 `$DATA_DIR/config/llm_gateway_api_key`) → 없으면 `LLM_GATEWAY_API_KEY` env |
| `_build_gateway_url()` (line 53) | `LLM_GATEWAY_CHAT_COMPLETIONS_URL` 우선, 없으면 `LLM_GATEWAY_BASE_URL` (기본 `http://dcucode-llm-gateway:18000`) + `/llm/v1/chat/completions` |
| 기본 모델 (line 62) | `LLM_DEFAULT_MODEL_FILE` (기본 `$DATA_DIR/config/llm_gateway_model`) |
| `_build_gateway_payload()` (line 169) | session/data/mode 기반 payload 생성 |
| 게이트웨이 호출 (line 339–363) | `Authorization: Bearer <key>`, timeout `LLM_GATEWAY_TIMEOUT_SEC` (기본 300) |

### URL 라우팅

- `oj/urls.py:30` — `re_path(r"^api/internal/", include("llm.urls.internal"))` (내부 통신 전용)
- 외부용 라우트는 `llm/urls/oj.py`

### LLM 모델 (`llm/models.py`)

| 모델 | 역할 |
|---|---|
| `LLMApiKey` | UUID 기반 API 키, scope/status/만료/사용량 추적 |
| `LLMRouteMap` | 모델명 → upstream_url 매핑 (priority/weight 기반 라우팅) |
| `LLMAuditLog` | 요청·응답·토큰 통계 — **데이터 분석 출발점으로 적합** |
| `LLMChatSession` | 사용자별 채팅 세션 |
| `LLMChatMessage` | role(user/assistant/system), 토큰 통계 |

## 초기화

| 스크립트 | 용도 |
|---|---|
| `init_db.sh` | Docker(postgres:10, redis:4.0)로 local 개발환경 구성, `secret.key` 생성, migrate |
| `deploy/entrypoint_dev.sh` | env → DB(`SysOptions.judge_server_token`) 저장 후 migrate, root/rootroot 초기 계정 생성 |
| `deploy/supervisord.conf` | gunicorn(WEB) + dramatiq(WORKER) 프로세스 관리 |

## DCU 커스텀 모델 인용 (간단)

```python
# lecture/models.py
class Lecture(...):
    year, semester, aihelper_status, ...

class signup_class(...):
    # 수강생
class ta_admin_class(...):
    # TA
    @staticmethod
    def is_user_ta(user, lecture): ...

# qna/models.py
class Post(...):
    submission, problem, contest, lecture FK
    @property
    def permit(self): ...   # TA·교수 권한 결정
class Comment(...): ...

# contest/models.py:31
llm_hint_enabled = models.BooleanField(default=False)

# submission/models.py:47
lecture = models.ForeignKey(Lecture, null=True, on_delete=models.CASCADE)
```
