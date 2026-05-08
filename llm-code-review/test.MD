# LLM 호출 한 쌍 — 프롬프트 + 응답 예시

대상: lecture 388 / contest 6181 / 문제 P01 / 학생 `kimweple`
모델: `Qwen/Qwen3.5-35B-A3B-FP8` (onprem)
호출 옵션: `temperature=0.2`, `max_tokens=1500`, `extra_body={"chat_template_kwargs":{"enable_thinking":False}}`
LLM latency: 2120 ms

자동 채점 결과 (testcase 기반): **AC**, 20/20점.

---

## 1) 요청 — `messages` 배열 (system 1개 + user 1개)

### 1-1. system

```
당신은 C 프로그래밍 과목의 조교(TA)입니다. 학생이 제출한 코드를 정성적으로 평가하세요. 출력은 반드시 단일 JSON 객체로만 응답하고, JSON 외 다른 텍스트(설명, 마크다운, ``` 펜스 포함)는 절대 포함하지 마세요. 평가 코멘트와 summary는 한국어로 작성하세요.
```

### 1-2. user

````
[문제]
P01 (난이도 Low, 배점 20)
제목: (난이도 하) 홀수번째 입력한 정수들의 최솟값, 최댓값, 평균 구하기 [20점]

설명:
20개의 정수를 입력 받고, 홀수 번째에 입력된 정수들 중 최댓값과 최솟값, 평균을 출력하는 프로그램을 작성하시오. 단, 평균은 소숫점 이하 둘째 자리까지 출력하시오.

입력 형식:
20개의 정수를 입력받는다.

출력 형식:
20개의 정수를 입력받고, 홀수 번째에 입력된 정수들 중 최댓값과 최솟값, 평균을 출력한다. 단, 평균은 소숫점 이하 둘째 자리까지 출력한다.

예제 1:
  입력: 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1
  출력: 0 0 0.00
예제 2:
  입력: 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20
  출력: 1 19 10.00

[자동 채점 결과]
결과: AC   testcase 점수: 20/20
시간: 1 ms   메모리: 1572864 KB

[학생 코드]
사용자: kimweple   언어: C
```c
#include <stdio.h>

int main() {
    int num[20];
    int max, min;
    double total = 0.0;

    scanf("%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d",
        &num[0], &num[1], &num[2], &num[3], &num[4], &num[5],&num[6], &num[7],&num[8], &num[9],&num[10], &num[11],&num[12], &num[13],&num[14], &num[15],&num[16], &num[17],&num[18], &num[19]);

    max = num[0];
    min = num[0];

    for (int j = 0; j < 20; j = j + 2) {
        if (max < num[j]) {
            max = num[j];
        }
        if (min > num[j]) {
            min = num[j];
        }
        total = total + num[j];
    }

    printf("%d %d %0.2f", min, max, total / 10.0);
}
```

[평가 지시]
다음 4개 축에 대해 각각 0~10의 정수 점수를 매기고, 각 축에 1~2문장 한국어 코멘트를 작성하세요.
- correctness: 정상 입출력 + 코너케이스 처리. testcase 통과 여부와 별개의 코드 단위 정합성.
- algorithm: 접근 방식이 문제 의도에 맞는지, 시간/공간 적합성.
- readability: 네이밍·들여쓰기·함수 분리·주석 등 코드 가독성.
- problem_understanding: 요구사항·제약조건 반영도 (입출력 형식, 단위, 정밀도 등).

또한 `suggested_partial_score`를 0 이상 20 이하의 정수로 산출하세요.
이는 testcase 결과와 무관하게, 코드의 의도·접근이 옳다면 줄 수 있는 부분점수입니다.

응답은 다음 JSON 스키마를 따르는 단일 JSON 객체로만 출력하세요. 다른 어떤 텍스트도 출력하지 마세요.

{
  "scores": {
    "correctness": "int in [0,10]",
    "algorithm": "int in [0,10]",
    "readability": "int in [0,10]",
    "problem_understanding": "int in [0,10]"
  },
  "comments": {
    "correctness": "string (1~2 문장 한국어)",
    "algorithm": "string (1~2 문장 한국어)",
    "readability": "string (1~2 문장 한국어)",
    "problem_understanding": "string (1~2 문장 한국어)"
  },
  "overall": "int in [0,100]",
  "summary": "string (한국어 2~3문장 종합 평)",
  "suggested_partial_score": "int in [0,20]"
}
````

---

## 2) 응답 — 모델이 그대로 뱉은 raw 문자열

```json
{
  "scores": {
    "correctness": 10,
    "algorithm": 9,
    "readability": 6,
    "problem_understanding": 10
  },
  "comments": {
    "correctness": "모든 테스트 케이스를 통과하여 정상적으로 작동하며, 정수 입력과 연산 로직이 정확합니다.",
    "algorithm": "20개 입력을 고정적으로 처리하는 방식은 문제의 제약 조건에 부합하며 효율적인 접근입니다.",
    "readability": "scanf 함수에 20개의 인자를 나열하여 가독성이 떨어지며, 변수명도 단순하여 개선이 필요합니다.",
    "problem_understanding": "홀수 번째 인덱스 (0, 2, ...) 를 정확히 처리하고 평균을 소수점 둘째 자리까지 출력하는 요구사항을 완벽히 반영했습니다."
  },
  "overall": 88,
  "summary": "코드는 문제의 모든 요구사항을 정확히 충족하여 만점을 받을 만합니다. 다만, 반복되는 scanf 인자 나열로 인해 코드의 가독성이 다소 떨어지는 단점이 있습니다.",
  "suggested_partial_score": 20
}
```

---

## 3) 파싱 후 저장된 형태 — `evaluations/kimweple/P01.json` 발췌

```json
{
  "submission_id": "a9216ab66ee584171be0540e6d30ab90",
  "username": "kimweple",
  "problem": { "label": "P01", "title": "...", "total_score": 20, "difficulty": "Low" },
  "testcase": { "result": "AC", "score": 20, "time_cost_ms": 1, "memory_cost_kb": 1572864 },
  "evaluation": {
    "scores": { "correctness": 10, "algorithm": 9, "readability": 6, "problem_understanding": 10 },
    "comments": { "...": "위와 동일" },
    "overall": 88,
    "summary": "...",
    "suggested_partial_score": 20,
    "model_used": "<profile-default>",
    "llm_latency_ms": 2120,
    "error": null
  },
  "raw_response": "{ ...위 raw 문자열 그대로... }"
}
```
