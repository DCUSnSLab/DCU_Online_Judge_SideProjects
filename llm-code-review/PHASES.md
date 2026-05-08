# 진행상황

> 각 페이즈 시작/완료 시 갱신.

## Phase 1: P01 한 문제 전 학생 정성 평가 — 파이프라인 검증

- 상태: **completed (사용자 confirm 대기)**
- 시작: 2026-05-08
- 완료: 2026-05-08
- 입력: `../lecture-code-review/out/lecture-388_contest-6181` (P01 final 21명)
- 모델: `dcu_llm` onprem 프로필 (`Qwen/Qwen3.5-35B-A3B-FP8`)
- 평가 축: correctness / algorithm / readability / problem_understanding (각 0~10)
- 종합: `overall = round(sum/40*100)` (0~100)
- 부분점수 제안: `suggested_partial_score` (0 ≤ x ≤ problem.total_score)
- 알아낸 사항(중요):
  - Qwen3 thinking mode 가 기본 ON 이라 `message.content` 가 비고 `reasoning_content` 만 옴 → `extra_body={"chat_template_kwargs":{"enable_thinking":False}}` 로 끄면 정상 JSON 응답
  - 본 옵션은 `llm_code_review/llm.py` 의 `_QWEN_NO_THINK_EXTRA` 상수로 항상 적용
- 검증 결과:

| 지표 | 결과 |
|---|---|
| 처리 건수 | 21 / 21 (실패 0) |
| 총 소요 (concurrency=2) | **24.7초** (평균 ~2.3초/건) |
| summary.csv 행 수 | 21 (header 제외) |
| evaluations/\<user\>/P01.json | 21 |
| reports/\<user\>/P01.md | 21 |
| overall 분포 | min=0, max=90, avg=38.0 |
| suggested_partial_score 분포 | min=0, max=20, avg=7.9 |
| overall=0 건수 | 6 (LLM이 코드 자체를 인정 못한 케이스 — 예: `eliuckaa` 의 미초기화 변수, 가변인자 오용) |
| 모든 evaluation의 스키마 (4축/overall/sps/summary/comments) | 키 누락 0 |
| 한두 명 사람 검토 (`alswo6592`, `eliuckaa`) | 코멘트가 코드 결함을 정확히 지목 — 합리적 |

- 다음 페이즈로 넘어가는 조건: 사용자 confirm

## Phase 2: 평가 시스템 개선 (정성 + AI 사용 가능성)

- 상태: **completed (사용자 confirm 대기)**
- 브랜치: `phase2/eval-improvements`
- 시작: 2026-05-08
- 완료: 2026-05-08
- 해결한 4개 구조적 문제:
  - **#1 점수 정합성**: `overall = round(sum/40*100)`, `sps = round(total*(c+p)/20)` 산식을 `rubric.overall_score`/`partial_score`로 단일 원천. 모델 응답값은 `parse_response`에서 산식 값으로 무조건 덮어쓰고, 차이는 `evaluation.recomputed`에 기록.
  - **#2 correctness 모호성**: `rubric.AXIS_CHECKLISTS`에 축별 testcase-독립 체크리스트(변수 초기화·입출력 형식·미정의 동작·코너 케이스 등)를 명시하고 user 프롬프트에 정적 블록으로 주입.
  - **#3 코멘트 추상성**: `comments[axis]`를 `{assessment, suggestion}` nested 객체로 강제. 두 키 비공백 검증 + 프롬프트에 1-shot 예시.
  - **#4 채점자 보조 신호 부재**: 신규 `ai_usage.py` — 별도 LLM 호출, `counter_signals` 필수, `disclaimer` 자동 정규화, `ai_usage_assessment`로 형제 필드 저장. `--no-ai-usage`로 끔.
- 추가 개선:
  - 계층적 프롬프트 (`SYSTEM_PRINCIPLES` + 정적 체크리스트 블록 + 동적 문제·코드·스키마 빌더)
  - 난이도 보정 문구 (입문 문제에 함수 분리 부재를 큰 감점으로 삼지 말 것)
  - 실패 시 `last_raw` 보존하여 디버깅
- 검증 결과:

| 검증 | 결과 |
|---|---|
| **V1 산식 일관성** | 39/39 evaluation에서 `overall`·`sps` 산식 일치 (mismatches=0) |
| **V2 다양성** (P01·P05·P07, 39명) | 평가 39/39 성공, AI-usage 39/39 성공, 코멘트 nested 검증 통과. P01 65.9s + P05 37.5s + P07 11.4s |
| **V3 반복성** (alswo6592 P01, 3회) | 4축 stdev 0.0~0.58, overall stdev 1.15, sps stdev 0.58, ai_likelihood stdev 0.0 — 모두 임계값 안 |
| **V4 reference solution 대조** | refsol P01 ai_likelihood=15 vs 학생 평균 26.2. 깔끔한 사람 코드를 LLM-generated로 잘못 분류하지 않음 (sanity 통과) |
| **V5 회귀** (`--no-ai-usage`) | nested comments 정상, ai_usage_assessment=null, 산식 재계산 동작. Phase 1 출력은 `out_phase1_baseline/`에 백업 보관 |

- 39명 통합 통계:

| 문제 | 난이도 | n | overall avg | sps avg | ai_likelihood avg |
|---|---|---|---|---|---|
| P01 | Low | 21 | 47.4 | 8.9 | 31.7 |
| P05 | High | 14 | 42.9 | 18.1 | 27.9 |
| P07 | Low(상) | 4 | 28.0 | 22.5 | 21.2 |

- 다음 페이즈로 넘어가는 조건: 사용자 confirm 후 `main` 머지

## Phase 3: (TBD)

- 후보: 전체 7문제 일괄, summary 누적 모드(현재는 `--problem` 별 덮어쓰기), 시각화 대시보드, 가중평균 옵션
