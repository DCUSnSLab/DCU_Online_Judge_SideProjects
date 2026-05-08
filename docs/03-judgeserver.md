# 03 · JudgeServer / 채점 흐름

루트: `/home/soobin/development/dcucode/DCU_Online_Judge_JudgeServer`

배포 형태: snslabdocker/judge_server:latest 컨테이너, gunicorn(Flask). 현재 dev에서 `judge-server-dev` 로 떠있음, 호스트 `127.0.0.1:12358 → 컨테이너 :8080`.

## HTTP 엔드포인트 (12358)

| 엔드포인트 | 역할 |
|---|---|
| `POST /judge` | 실제 채점 수행 (소스 컴파일 + testcase 실행) |
| `POST /ping` | 상태 체크 |
| `POST /compile_spj` | Special Judge 컴파일 |

모두 `X-Judge-Server-Token` 헤더(SHA256 해시) 인증.

## 컴포넌트

```
JudgeServer/server/
├── server.py          # Flask 앱 진입, JudgeServer 클래스 (judge / ping / compile_spj)
├── judge_client.py    # JudgeClient: multiprocessing 기반 testcase 병렬 실행
├── compiler.py        # 언어별 컴파일 (Compiler)
├── service.py         # heartbeat 루프 (JudgeService.heartbeat())
├── config.py          # 언어/실행 환경 설정
├── exception.py       # 커스텀 예외
├── unbuffer.c         # 스트림 unbuffer 헬퍼
├── utils.py           # 공통 유틸
├── entrypoint.sh      # 컨테이너 진입 스크립트
└── __init__.py
```

내부적으로 `_judger` (C 확장, seccomp sandbox)을 호출하여 별도 사용자(code/spj)에서 프로세스를 실행한다. 파일 시스템 접근, 네트워크, 시스템콜을 제한.

## Heartbeat

`server/service.py JudgeService.heartbeat()` 가 5초마다 backend로 POST.

- 호출 대상: `BACKEND_URL` 환경변수 (현 셋업에서 `http://host.docker.internal:8000/api/judge_server_heartbeat/`)
- 백엔드 수신: `conf/views.py:132` `JudgeServerHeartbeatAPI`
- DB 갱신: `conf.models.JudgeServer` (`judger_version`, `cpu_core`, `memory_usage`, `service_url`, `ip`, `last_heartbeat`)
- 6초 이상 미수신 시 status=abnormal

devstack compose에서 entrypoint:

```yaml
entrypoint:
  - /bin/sh
  - -c
  - |
    (while true; do cd /code && python3 service.py >> /log/heartbeat.log 2>&1; sleep 5; done) &
    exec /code/entrypoint.sh
```

## 채점 시퀀스

```
[사용자] POST /api/submission
   ↓
SubmissionAPI.post  (Backend/submission/views/oj.py)
   ↓ Submission.objects.create(...)
JudgeDispatcher().judge()                         # 일반 제출 (현재 동기 호출)
JudgeDispatcher.judge(sample_test_status=True)    # Sample test
   ↓
ChooseJudgeServer  (judge/dispatcher.py:42)
   ↓ task_number ≤ cpu_core × 2 인 서버 선택, F('task_number')+1
   ↓ 서버 없으면 Redis CacheKey.waiting_queue 에 저장 후 return
DispatcherBase._request(server.service_url + "/judge")
   X-Judge-Server-Token = sha256(SysOptions.judge_server_token)
   ↓
JudgeServer.judge  (server/server.py)
   ↓ InitSubmissionEnv → /judger/run/{submission_id}
   ↓ Compiler.compile (필요시)
   ↓ SPJ 사용 시 /judger/spj/ 에서 executable 로드
   ↓ JudgeClient.run  (multiprocessing 기반 병렬)
       ↓ _judger (C, seccomp) 로 testcase 실행
       ↓ SPJ 모드: _spj() → exit code 0=AC, 1=WA, -1=Error
       ↓ 표준 모드: MD5 기반 output 비교
   ↓ 결과 list 반환
   ↓
JudgeDispatcher._compute_statistic_info()
   ↓ 최대 시간/메모리, OI 점수 계산
   ↓ ACM: 모두 정답이면 AC, 하나라도 오류면 첫 오류
   ↓ OI: 모두 정답=AC, 모두 오류=첫 오류, 그 외=Partial AC
   ↓
update_problem_status() / update_contest_rank() / updateLecturePersonalInfo()
   ↓
JudgeServer.task_number -= 1  (dispatcher.py:54)
process_pending_task()  # 대기 큐 비움
```

## 데이터 위치

| 종류 | 위치 |
|---|---|
| 테스트케이스 | `Backend/data/test_case/{test_case_id}/` (input/output 파일 + `info` JSON). devstack에선 컨테이너 `/test_case` 로 ro 마운트 |
| SPJ 소스 | `/judger/spj/{spj_version}.cpp` |
| SPJ 바이너리 | `/judger/spj/` (컴파일 결과) |
| 채점 작업 디렉토리 | `/judger/run/{submission_id}/` |
| 로그 | 컨테이너 `/log/`, 호스트 `devstack/data/judge_server/log/` |

## 인증 & 토큰

- env `JUDGE_SERVER_TOKEN` → `options/options.py:91` 에서 읽어 `SysOptions.judge_server_token` 에 저장
- JudgeServer side: env `TOKEN` 으로 같은 값을 받음 (현 dev: `devtoken_change_me_32chars_xxxxxxxxxxxx`)
- 양쪽 모두 SHA256 해시로 비교. 토큰 회전 시 양쪽 모두 갱신 필요.

## 사이드 프로젝트 관점 핵심

- **`Submission` 모델은 채점 후 update 되는 풍부한 로그**: 언어, 결과, 시간/메모리, info(테스트케이스별 결과). 데이터 분석 1순위 소스.
- **dramatiq 비동기 vs 동기 호출 혼재**: 일반 제출이 현재 동기로 도는 부분이 있으므로(원래는 dramatiq), 부하·지연 관련 사이드 프로젝트 시 점검 포인트.
- **테스트케이스 디렉토리가 Backend repo 안에 있음** (`Backend/data/test_case/`): 사이드 프로젝트가 테스트케이스를 자동 생성하거나 분석할 때 직접 접근 가능. 컨테이너에서는 ro 마운트.
- **heartbeat는 6초가 한계**: judge-server 추가 모니터링 사이드 프로젝트가 있다면 이 임계값 기준으로 알람.
