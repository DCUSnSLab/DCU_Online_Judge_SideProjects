# lecture-code-review

DCU Online Judge 의 PostgreSQL DB에서 특정 강의·콘테스트의 학생 코드 제출 내역을 직결로 가져와 디스크에 export 하는 CLI. 본체 backend/frontend 코드는 손대지 않고 read-only 로 동작한다 (느슨한 결합).

> 본 프로젝트는 페이즈 단위로 진행한다. 진행상황은 [`PHASES.md`](./PHASES.md) 참고.

## Phase 1 (현재): DB → 디스크 export

| 출력 | 위치 |
|---|---|
| 강의/대회 메타 | `out/<run>/_meta/{lecture,contest}.json` |
| 문제 풀텍스트 | `out/<run>/_meta/problems/<P01>.json` (description, samples, hint, time/memory limit, languages, test_case_score …) |
| 인덱스 CSV | `out/<run>/_meta/{problems,students,submissions,final_submissions}.csv` |
| 통계 | `out/<run>/_meta/summary.json` (총 제출수·최종 제출수·결과별 분포 등) |
| 모든 제출 코드 | `out/<run>/codes/<username>/<problem>/<timestamp>_<short_id>__<RESULT>.<ext>` |
| **학생별 문제별 최종 코드** | `out/<run>/final_codes/<username>/<problem>.<ext>` (Phase 2 평가 입력) |

`<run>` = `lecture-<L>_contest-<C>`. 최종 제출은 `(user_id, problem_id)` 그룹에서 `create_time DESC` 가장 최신 1건. PENDING/JUDGING(`--include-pending` 미사용 시 제외)도 final 후보에서 제외.

## 설치

```bash
cd ~/development/dcucode/DCU_Online_Judge_SideProjects/lecture-code-review
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env  # 필요 시 DSN 수정
```

## 사용

```bash
source .venv/bin/activate

# 기본
lecture-code-review --lecture-id 388 --contest-id 6181

# DSN 직접 지정
lecture-code-review -L 388 -C 6181 \
  --dsn "postgresql://onlinejudge:onlinejudge@127.0.0.1:5432/onlinejudge"

# 출력 경로 변경
lecture-code-review -L 388 -C 6181 --out /tmp/lcr-out
```

옵션:

- `-L/--lecture-id INT` (필수)
- `-C/--contest-id INT` (필수 — Phase 1 범위)
- `--dsn STR` — 미지정 시 `.env` 의 `LCR_PG_DSN`, 그것도 없으면 기본 DSN
- `--out PATH` — 기본 `./out`
- `--include-pending` — `PENDING/JUDGING` 상태도 export (기본 off)
- `-v/--verbose`

## 약속

- DB 작업은 SELECT 만. 데이터 변경 없음.
- Backend repo import 하지 않음 (JudgeStatus 등은 자체 enum 으로 복제).
- 실행 결과(`out/`)는 `.gitignore` 처리되어 repo에 들어가지 않음.

## 다음 페이즈

Phase 1 검증이 끝나면 [`PHASES.md`](./PHASES.md) 에 결과를 기록하고, Phase 2 (검토 자동화) 의 plan 을 별도 작성한다.
