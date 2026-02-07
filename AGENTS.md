## 1. 프로젝트 정체성 (Identity)
이 프로젝트는 **'이미지 기반 만화/웹툰 AI 번역 서비스 (MVP v1.0)'**입니다.
OCR, 번역, 인페인팅, 식자(Typesetting) 과정을 단일 파이프라인으로 자동화하여 "페이지당 30초 내 처리"와 "고품질 읽기 경험"을 제공하는 것을 목표로 합니다.

## 2. 기술 스택 (Tech Stack) - 강제 사항
AI는 다음 스택을 엄격히 준수해야 하며, 임의로 다른 프레임워크를 제안하지 마십시오.
- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS
- **Backend**: FastAPI (Python 3.11+), Pydantic v2
- **Database**: PostgreSQL (SQLAlchemy/Alembic), Redis (Queue 관리)
- **Infrastructure**: Cloudflare R2 (이미지 스토리지), Docker
- **AI Ops**: OpenAI API (메인), Gemini/Vision API (Fallback)

## 3. 코딩 규칙 (Coding Standards)
### 공통 원칙
- **언어**: 모든 주석, 문서, 커밋 메시지는 **한국어**로 작성한다.
- **타입 안전성**: Frontend(`any` 금지), Backend(Pydantic 모델 필수) 모두 엄격한 타이핑을 적용한다.
- **명명 규칙**: 변수는 `snake_case`(Python) / `camelCase`(JS), 클래스는 `PascalCase`를 따른다.

### Frontend (Next.js)
- **컴포넌트**: 함수형 컴포넌트와 Hooks 패턴만 사용한다 (Class 컴포넌트 금지).
- **상태 관리**: 전역 상태는 최소화하고, 서버 상태(React Query 등)와 분리한다.
- **스타일**: Tailwind CSS 유틸리티 클래스를 사용하며, 복잡한 스타일은 분리한다.

### Backend (FastAPI)
- **아키텍처**: Router, Service, CRUD, Schema 계층을 명확히 분리한다.
- **비동기**: I/O 작업(DB, 외부 API)은 반드시 `async/await`를 사용한다.
- **에러 처리**: HTTP 상태 코드와 함께 명시적인 에러 메시지(App Code 포함)를 반환한다.

## 4. 금지 사항 (Boundaries) - 🚫 Never Do
- **Secrets 노출**: API Key, DB 접속 정보 등 민감 정보는 절대 코드에 하드코딩하지 않는다 (`.env` 사용).
- **테스트 파괴**: 기존 테스트 코드를 임의로 삭제하거나 주석 처리하지 않는다.
- **무단 변경**: `prisma/schema.prisma`나 `alembic` 마이그레이션 파일은 사용자 승인 없이 수정하지 않는다.

## 5. 정의된 명령어 (Commands)
- Frontend 실행: `npm run dev`
- Backend 실행: `uvicorn app.main:app --reload`
- 테스트 실행: `pytest` (Backend), `npm run test` (Frontend)