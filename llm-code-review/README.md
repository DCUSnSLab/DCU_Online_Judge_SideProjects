# llm-code-review

`lecture-code-review` 가 디스크로 export 한 학생 최종 제출 코드를 입력으로, 온프레미스 LLM(Qwen3.5-35B)을 통해 **정성 평가**를 수행한다. testcase 기반 정량 채점이 0/만점 이분법으로 놓치는 부분(접근법은 맞으나 미완성, 가독성·구조 차이 등)을 보완하기 위함.

> 본 프로젝트는 페이즈 단위로 진행. 진행상황은 [`PHASES.md`](./PHASES.md) 참고.

## 의존성

- `dcu-llm` (path 의존성: `/home/soobin/development/dcucode/sideproject`)
- `python-dotenv`

## 설치

```bash
cd ~/development/dcucode/DCU_Online_Judge_SideProjects/llm-code-review
python3 -m virtualenv .venv     # 또는: python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env             # ONPREM_API_KEY 설정
```

## 사용

```bash
source .venv/bin/activate

# Phase 1 검증: P01 한 학생 (스모크)
llm-code-review \
  --input ../lecture-code-review/out/lecture-388_contest-6181 \
  --problem P01 --username alswo6592

# P01 전체 학생 (21명)
llm-code-review \
  --input ../lecture-code-review/out/lecture-388_contest-6181 \
  --problem P01

# Dry-run (LLM 호출 없이 프롬프트만 prompts/ 에 저장)
llm-code-review --input <run> --problem P01 --dry-run
```

## 출력 (Phase 1)

`out/<input-run-name>/`

```
_meta/
├── rubric.json        # 사용한 4축 정의
├── run_info.json      # 입력/모델/시각/처리수
└── summary.csv        # 학생별·문제별: testcase 결과 + 4축 점수 + overall + 보상 점수
evaluations/<user>/<P01>.json   # raw LLM 응답 + 사용한 메시지
reports/<user>/<P01>.md         # 사람용 마크다운
prompts/<user>/<P01>.md         # --dry-run 일 때만
```

## 평가 루브릭

| 축 | 0–10 의미 |
|---|---|
| `correctness` | 정상 입출력 + 코너케이스 (testcase 결과와 별개의 코드 단위 정합성) |
| `algorithm` | 접근 방식의 적절성·효율성 |
| `readability` | 네이밍·들여쓰기·함수 분리·주석 |
| `problem_understanding` | 요구사항·제약조건 반영도 |

`overall = round(sum(scores) / 40 * 100)` (0~100).
`suggested_partial_score`: 문제의 `total_score` 를 상한으로, 코드 의도가 맞다면 줄 수 있는 부분점수 (정수).

## 약속

- 입력(`lecture-code-review` 의 출력 디렉토리)에는 일체 쓰지 않음. read-only.
- OJ 본체 DB·API에 직접 접속하지 않음 (LLM 호출만).
- `lecture_code_review` 모듈을 import 하지 않음 — 디스크 출력만 소비 (격리 원칙).
