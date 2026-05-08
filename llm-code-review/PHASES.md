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

## Phase 2: (TBD)

- 후보: 전체 7문제 일괄 / testcase 점수 자동 보정 적용 / 비교 리포트
