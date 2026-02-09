## 1. 프로젝트 정체성과 목표
이 프로젝트는 **이미지 기반 만화/웹툰 AI 번역 서비스(MVP)**다.
OCR, 번역, 인페인팅, 식자(Typesetting) 파이프라인을 자동화해 아래 목표를 달성한다.

- 페이지당 평균 처리 시간: **30초 이내**
- 제품 성격: 단순 번역기가 아니라 **읽기 경험 엔진**
- 품질 우선 원칙: 속도보다 읽기 품질 기준을 우선한다.

## 2. 문서 SSOT와 운영 원칙
이 파일(`AGENTS.md`)은 에이전트 실행 가이드의 단일 기준 문서다.

### 문서 우선순위
1. `docs/specs/PRD.md`
2. `Plans.json`(SSOT), `Plans.md`(파생본)
3. `README.md` (운영 절차/경로 안내 참고)

### 충돌 처리 원칙
- `PRD/Plans`와 상충하면 `PRD/Plans`를 채택한다.
- 과거 참고 문서의 초기 가정(예: 다운로드 제외, 10원/20명)은 자동 승격하지 않는다.

### Plans 문서 운영 원칙
- `Plans.json`이 로드맵 SSOT다.
- `Plans.md`는 `Plans.json`에서 자동 생성되는 파생 문서다.
- `Plans.md`는 직접 수정하지 않는다.

## 3. 성공 기준/게이트
### Hard Gate (차단형, 필수)
- `input_text_count == output_text_count`
- `bbox_overflow == 0`
- `min_font_pt >= 10`

### Soft Gate (샘플링)
- 자연스러움: 골든셋 수동 평가 **90% 통과**
- 정확도: 오역 체크리스트 **5개 중 4개 통과**

### User Gate (cohort_100)
- `CSAT >= 4.0/5.0`
- 무편집 읽기 비율 `>= 90%`

### 게이트 운영 원칙
- Hard Gate 실패 시 **fail-closed** 정책을 적용한다.
- 품질 게이트 통과 전 다음 Phase로 진행하지 않는다.

## 4. 상태 모델/과금 규칙 SSOT
### 상태 모델
- `job_status`: `pending`, `processing`, `completed`, `failed`, `canceled`
- `page_status`: `success`, `partial`, `fail`, `canceled`
- `terminal_non_canceled_pages`: `success`, `partial`, `fail`

### 과금 규칙
- `success = 1.0`
- `partial = 0.5`
- `fail/canceled = 0`

## 5. 기술 스택 강제 사항
아래 스택은 강제 사항이며 임의 프레임워크 변경/제안은 금지한다.

- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS
- **Backend**: FastAPI (Python 3.11+), Pydantic v2
- **Database**: PostgreSQL (SQLAlchemy/Alembic), Redis (Queue 관리)
- **Infrastructure**: Cloudflare R2 (이미지 스토리지), Docker
- **AI Ops**: OpenAI API (메인), Gemini/Vision API (Fallback)

## 6. 개발/테스트 실행 규칙
### 개발 원칙
- 모든 기능은 `RED -> GREEN -> REFACTOR` 순서를 따른다.
- `GREEN`은 최소 구현만 허용하고 구조 개선은 `REFACTOR`에서 수행한다.
- `REFACTOR`에서도 기존 테스트 집합은 유지한 채 통과해야 한다.

### 테스트 정책
- 명령 정책: `example_only`
- 품질 게이트 통과 전 다음 Phase 진행 금지
- E2E는 사용자 여정 + Hard Gate + 주요 오류 코드까지 검증한다.

### 테스트 프레임워크
- Backend: `Pytest`
- Frontend: `Vitest + Testing Library`
- E2E: `Playwright`

### 코딩 규칙
#### 공통
- 모든 주석/문서/커밋 메시지는 한국어로 작성한다.
- 타입 안전성을 강제한다(Frontend `any` 금지, Backend Pydantic 모델 필수).
- 명명 규칙: Python `snake_case`, JS/TS `camelCase`, 클래스 `PascalCase`.

#### Frontend (Next.js)
- 함수형 컴포넌트 + Hooks 패턴만 사용한다.
- 전역 상태는 최소화하고 서버 상태와 분리한다.
- 스타일은 Tailwind 유틸리티를 우선하고 복잡 스타일은 분리한다.

#### Backend (FastAPI)
- Router/Service/CRUD/Schema 계층을 분리한다.
- DB/외부 API 등 I/O는 `async/await`를 사용한다.
- 에러 응답은 HTTP 상태 코드 + 명시적 `app_code`를 함께 반환한다.

## 7. API/에러 처리 규칙(필수)
### 요청 규칙
- 쓰기 API는 `Idempotency-Key`를 필수로 한다.
- 인증 엔드포인트(`signup/login/refresh/logout` 등)는 예외로 둘 수 있다.

### 오류 응답 규칙
- 오류는 HTTP 상태 코드와 `app_code`를 함께 반환한다.
- 정책 차단은 은닉 우선 규칙을 적용한다.

### 핵심 app_code 카테고리
- 입력: `UNSUPPORTED_FILE_TYPE`, `MAX_PAGES_EXCEEDED`, `ARCHIVE_PARSE_FAILED`
- 제한: `TEMPORARILY_BLOCKED`, `DAILY_PAGE_LIMIT_EXCEEDED`, `HOURLY_PAGE_LIMIT_EXCEEDED`, `QUEUE_CAPACITY_EXCEEDED`
- 비용: `COST_DAILY_LIMIT_EXCEEDED`, `FX_RATE_UNAVAILABLE`
- 경합: `ACTIVE_JOB_ALREADY_EXISTS`, `IDEMPOTENCY_IN_PROGRESS`, `PAGE_NOT_EDITABLE`, `PAGE_RETRY_LIMIT_EXCEEDED`

## 8. 보안/운영 제약
- 시크릿은 `.env` 기반으로만 관리한다.
- 인증은 JWT + Refresh 회전 정책을 따른다.
- 권한은 최소 권한(`user/admin`)을 적용한다.
- CORS/CSRF 기본 차단 정책을 유지한다.
- 민감정보 최소 수집, 저장 암호화, 전송 TLS 강제를 따른다.
- 외부 AI 경로는 OpenAI 기본, Gemini fallback을 유지한다.

## 9. 금지사항 및 변경 제한
- API Key/DB 접속 정보 등 민감 정보 하드코딩 금지
- 기존 테스트 삭제 또는 주석 처리 금지
- `prisma/schema.prisma` 무단 수정 금지
- `alembic` 마이그레이션 파일 무단 수정 금지
- `Plans.md` 직접 편집 금지 (`Plans.json` 수정 후 재생성)
- 강제 기술 스택의 임의 변경 금지

## 10. 실행 명령
### 서비스 실행
- Frontend: `npm run dev`
- Backend: `uvicorn app.main:app --reload`

### 테스트 실행
- Backend: `pytest`
- Frontend: `npm run test`

### Plans 문서 동기화/검증
- `python scripts/plans_sync.py validate --input Plans.json`
- `python scripts/plans_sync.py render --input Plans.json --output Plans.md`
- `python scripts/plans_sync.py check --input Plans.json --output Plans.md`
