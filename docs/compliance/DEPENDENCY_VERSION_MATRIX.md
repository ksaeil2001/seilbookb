# 의존성 버전 고정 매트릭스

- 정책: `exact` 고정(semver range 금지)
- 기준일: 2026-02-09

## Frontend

| 패키지 | 버전 | 라이선스 | 비고 |
| --- | --- | --- | --- |
| next | 14.2.18 | MIT | App Router 기준 |
| react | 18.3.1 | MIT | UI 런타임 |
| react-dom | 18.3.1 | MIT | 브라우저 렌더링 |
| typescript | 5.6.3 | Apache-2.0 | 타입 시스템 |
| tailwindcss | 3.4.17 | MIT | 스타일 시스템 |
| vitest | 2.1.8 | MIT | 프론트 테스트 |
| @testing-library/react | 16.1.0 | MIT | 컴포넌트 테스트 |
| @testing-library/jest-dom | 6.6.3 | MIT | DOM assertion |
| @playwright/test | 1.49.1 | Apache-2.0 | E2E 테스트 |

## Backend

| 패키지 | 버전 | 라이선스 | 비고 |
| --- | --- | --- | --- |
| fastapi | 0.115.6 | MIT | API 프레임워크 |
| pydantic | 2.10.5 | MIT | 스키마/검증 |
| sqlalchemy | 2.0.36 | MIT | ORM |
| alembic | 1.14.0 | MIT | 마이그레이션 |
| redis | 5.2.1 | MIT | 큐/캐시 |
| psycopg[binary] | 3.2.3 | LGPL-3.0-or-later | 조건부 허용(서버사이드) |
| uvicorn[standard] | 0.34.0 | BSD-3-Clause | ASGI 서버 |
| httpx | 0.28.1 | BSD-3-Clause | HTTP 클라이언트 |
| python-dotenv | 1.0.1 | BSD-3-Clause | 환경변수 로딩 |
| pytest | 8.3.4 | MIT | 백엔드 테스트 |
| pytest-asyncio | 0.24.0 | Apache-2.0 | 비동기 테스트 |
