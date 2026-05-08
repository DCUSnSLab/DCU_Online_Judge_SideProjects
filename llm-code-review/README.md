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

# 스모크: 한 학생
llm-code-review \
  --input ../lecture-code-review/out/lecture-388_contest-6181 \
  --problem P01 --username alswo6592

# 한 문제 전체 학생 (정성평가 + AI-usage 평가 둘 다 수행)
llm-code-review \
  --input ../lecture-code-review/out/lecture-388_contest-6181 \
  --problem P01

# AI-usage 평가 끄기 (LLM 호출 ~절반)
llm-code-review --input <run> --problem P01 --no-ai-usage

# 반복성 측정 (한 제출에 대해 N회 평가)
python tools/repeatability.py \
  --input ../lecture-code-review/out/lecture-388_contest-6181 \
  --problem P01 --username alswo6592 --repeat 3

# 산식 일관성 검증
python tools/verify_consistency.py out/lecture-388_contest-6181

# Dry-run
llm-code-review --input <run> --problem P01 --dry-run
```

## 출력 (Phase 2)

`out/<input-run-name>/`

```
_meta/
├── rubric.json            # 4축 정의 + 체크리스트 + 산식
├── run_info.json          # 입력/모델/시각/처리수/AI-usage 통계
└── summary.csv            # 학생-문제별: testcase + 4축 + overall + sps + AI-usage 컬럼
evaluations/<user>/<P>.json    # 평가 raw + 파싱 결과 + ai_usage_assessment 형제 필드
reports/<user>/<P>.md          # 사람용 마크다운 (점수표 + 축별 assessment/suggestion + AI-usage 섹션)
prompts/<user>/<P>.md          # --dry-run 일 때만
```

## 평가 루브릭 (Phase 2)

4개 축 (각 0~10) + 축별 체크리스트(`rubric.AXIS_CHECKLISTS`):

| 축 | 의미 |
|---|---|
| `correctness` | 변수 초기화·입출력 형식·미정의 동작·경계 케이스 — **testcase 통과와 독립적** |
| `algorithm` | 접근 적절성·복잡도 |
| `readability` | 네이밍·들여쓰기·구조·주석 (난이도가 낮으면 함수 분리 부재를 큰 감점으로 삼지 않음) |
| `problem_understanding` | 입출력 형식·단위·정밀도·특수 조건 반영 |

각 축 코멘트는 `{assessment, suggestion}` 두 필드 모두 비공백 강제.

산식 (`rubric.py` 단일 원천, 후처리에서 모델값을 산식값으로 무조건 덮어씀):

```
overall = round( (correctness + algorithm + readability + problem_understanding) / 40 * 100 )

suggested_partial_score = round( total_score * (correctness + problem_understanding) / 20 )
```

`sps`는 의도·접근 정합성을 보는 두 축의 함수. `algorithm`/`readability`는 부분점수 결정 변수 아님.

## AI 사용 가능성 평가 (Phase 2)

별도 LLM 호출. 결과는 `ai_usage_assessment` 형제 필드에 저장되며 점수 계산에 영향 X.

스키마: `likelihood_score(0-100)` + `confidence(low|medium|high)` + `signals[]` + **필수 `counter_signals[]`** + `summary` + `disclaimer`.

마크다운 리포트에는 **"참고용 · 점수 미반영"** 라벨 + disclaimer 노출.

## 약속

- 입력(`lecture-code-review` 의 출력 디렉토리)에는 일체 쓰지 않음. read-only.
- OJ 본체 DB·API에 직접 접속하지 않음 (LLM 호출만).
- `lecture_code_review` 모듈을 import 하지 않음 — 디스크 출력만 소비 (격리 원칙).
