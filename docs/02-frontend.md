# 02 · Frontend (Vue)

루트: `/home/soobin/development/dcucode/DCU_Online_Judge_Frontend`

원본은 [QingdaoU OnlineJudgeFE](https://github.com/QingdaoU/OnlineJudgeFE) 포크. Vue 2.6 + Webpack 3 + DLL 플러그인. **Node v8.12.0** 환경.

## 페이지 구조

```
src/pages/
├── oj/   (학생 UI)
│   ├── views/  chat container contest general help index.js
│   │           lecture problem qna rank setting submission user
│   ├── components/  btn verticalMenu mixins ...
│   ├── router/  index.js  routes.js
│   ├── api.js   axios baseURL=/api  (Lecture, LLM chat sessions/messages, QnA posts/comments, Token Refresh ...)
│   └── index.js
└── admin/  (관리자 UI)
    ├── views/  contest general Home.vue index.js lecture problem student
    ├── components/  btn
    ├── router.js  (base: /admin/)
    │   Dashboard, Announcement, User, Config, JudgeServer, LLMKeys,
    │   CopyKiller(표절탐지), Problem/Contest CRUD,
    │   Lecture 생성/관리, StudentList, BatchMigrate(슈퍼어드민)
    ├── api.js
    └── index.js
```

## 라우트 요약

### OJ (학생) — `src/pages/oj/router/routes.js`

- `/`, `/login`, `/problem`, `/status`
- `/chat` LLM Chat (requiresAuth)
- `/question` Q&A (requiresAuth)
- `/CourseList` → `/CourseList/:lectureID` → `/CourseList/:lectureID/:contestID` (자식 라우트: problems, submissions, rank, helper, qna ...)
- `/contest/:contestID` General Contest (동일 자식 구조)
- `/acm-rank`, `/oi-rank`
- `/user-home`, `/setting`
- `/container` — Web SSH IDE (xterm.js + ssh2 게이트웨이)

### Admin — `src/pages/admin/router.js` (base `/admin/`)

- Dashboard, Announcement, User, Config, JudgeServer, LLMKeys
- Problem/Contest CRUD, CopyKiller (표절 탐지)
- Lecture 생성/관리, StudentList, BatchMigrate (슈퍼어드민 전용)

## API / Store

### `src/pages/oj/api.js` & `src/pages/admin/api.js`

- axios 기반, `axios.defaults.baseURL = '/api'`
- CSRF 토큰 자동 헤더
- OJ api: Lecture / LLM chat / QnA / Token refresh ...
- Admin api: User / Problem / Contest / Lecture 관리

### Vuex store — `src/store/`

- Root: `website` (config), `modalStatus` (login/register modal)
- Modules: `user.js`, `contest.js`, `theme.js`
- Actions: `getWebsiteConfig()`, `changeDomTitle()` 등

## 빌드 / 의존성

### `package.json` scripts

| script | 내용 |
|---|---|
| `npm run dev` | `build/dev-server.js` (webpack-dev-middleware + HMR, 기본 :8080) |
| `npm run build` | `build/build.js` 프로덕션 빌드 |
| `npm run build:dll` | `webpack.dll.conf.js` (vendor.dll 프리빌드: vue/vuex/axios/moment/raven-js) |

### 주요 dependencies

Vue 2.6, Vue-Router 3, Vuex 3, Element-UI, Bootstrap-Vue, Echarts, Highlight.js, Katex, Xterm (Web SSH), Quill Editor.

> Webpack 3 + Node v8.12.0 → 모던 패키지 호환 어렵다. 강결합 작업은 가급적 기존 패턴 재사용, 새 라이브러리 추가는 신중.

## 보조 스크립트 / 별도 서버

| 파일 | 역할 |
|---|---|
| `server.js` | **WebSocket SSH 게이트웨이** (정적 서빙 아님). xterm.js 클라이언트 ↔ WS ↔ 원격 SSH (`203.250.33.83:32022`) 중계 |
| `update_layout.py` | Problem.vue 4-pane(메뉴/문제/코드/AI힌트) 자동 재배치 |
| `heartbeat.py` | 백엔드 5초 헬스체크 루프, 5회 실패 시 docker 재시작 + 메일 알림 |
| `config/index.js` | 프록시 TARGET (기본 `http://127.0.0.1:8000`), OJ/Admin 진입점 분리 |
| `config/dev.env.js` | `VERSION = YYYYMMDD-커밋해시` 자동 삽입 |
| `config/prod.env.js` | 프로덕션 환경 |

## 사이드 프로젝트 관점 핵심

- **OJ/Admin 완전 분리**: 학생 vs 관리자 페이지가 서로 다른 entry point + 라우터 → 새 UI를 어느 쪽에 추가할지 명확히 분리 가능
- **AI 힌트 4-pane 레이아웃**: `update_layout.py` 가 Problem.vue 를 자동 변환 → 학생 학습 경험 강화 사이드 프로젝트가 손볼 1순위 영역
- **Web IDE**: `server.js` + `/container` 라우트로 분리 가동 → 별도 컨테이너 기반 코딩 환경 실험에 활용 가능
- **Echarts**: 대시보드/시각화 컴포넌트가 이미 있으므로, 데이터 분석 사이드 프로젝트가 강결합으로 들어갈 때 재사용
