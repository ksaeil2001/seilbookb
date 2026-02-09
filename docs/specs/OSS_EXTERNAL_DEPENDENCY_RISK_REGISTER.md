# 오픈소스/외부의존 제약 및 오동작 가능성 리스크 레지스터

- 기준 문서: `AGENTS.md`, `docs/specs/PRD.md`, `Plans.json`, `Plans.md`, `README.md`
- 분석 방식: 문서 기반 리스크 분석(구현 코드/런타임 벤치마크 제외)
- 최신 갱신일: 2026-02-09

## 1) 의존성 인벤토리 (확정)

| 의존성 | 분류 | 역할 | 영향 도메인 |
| --- | --- | --- | --- |
| Next.js (App Router) | OSS | 프론트 UI/라우팅 | UI/Auth/Upload/Download |
| FastAPI | OSS | 백엔드 API 엔드포인트 | Auth/Payment/Pipeline |
| Pydantic v2 | OSS | 요청/응답 스키마 검증 | Auth/Payment/API 계약 |
| SQLAlchemy/Alembic | OSS | DB ORM/스키마 마이그레이션 | Pipeline/Credit/Report |
| PostgreSQL | OSS | 영속 저장소 | Pipeline/KPI/Credit |
| Redis + Worker | OSS | 큐/비동기 처리 | Queue/Pipeline |
| Docker | OSS | 실행 환경 일관성 | 배포/운영 |
| Pytest | OSS | 백엔드 테스트 | 품질 게이트 |
| Vitest + Testing Library | OSS | 프론트 단위 테스트 | UI 회귀 |
| Playwright | OSS | E2E 테스트 | 사용자 여정 검증 |
| OpenAI API | 외부의존 | 기본 AI 경로 | OCR/번역/비용 |
| Gemini/Vision API | 외부의존 | OpenAI 장애 폴백 | OCR/번역/가용성 |
| Google 로그인 (platform.js + g-signin2 계획) | 외부의존 | 소셜 로그인 | Auth/UI |
| TossPayments 위젯 계획 | 외부의존 | 결제 UI/승인 흐름 | Payment/Credit |
| Cloudflare R2 | 외부의존(클라우드) | 이미지 스토리지 | Upload/Download/Pipeline |

## 2) 문서 기반 설계 리스크 (Design Risks)

| ID | 의존성 | 제약사항 | 오동작 가능성 | 심각도 | 가능성 | 탐지 신호(로그/메트릭/app_code) | 완화책 | 선행 작업(테스트/문서/구현) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D-01 | 전체 OSS | 매니페스트/락파일 관리 미흡 시 재현성 저하 | 환경별 버전 드리프트로 동일 코드가 상이 동작 | high | medium | 환경별 재현 불가, CI/로컬 불일치 | exact 버전 정책 고정, lockfile 강제 | `package-lock.json`, `requirements*.txt` 유지 |
| D-02 | Next.js + Google SDK | `platform.js + g-signin2` 경로는 브라우저/정책 변화에 취약 | 로그인 버튼 렌더 실패 또는 토큰 교환 흐름 단절 | high | medium | 로그인 UI 미노출, `GOOGLE_ID_TOKEN_INVALID`, `GOOGLE_AUTH_EXCHANGE_FAILED` | 공식 가이드 점검 루프, 대체 로그인 경로 준비 | Auth RED 테스트 + 브라우저 호환성 체크 |
| D-03 | FastAPI + Pydantic v2 | API 스키마/타입 정책은 있으나 구현 계약 자동검증 장치 부재 | 프론트-백엔드 계약 드리프트, app_code 매핑 불일치 | high | medium | 계약 테스트 실패, app_code 미매핑 로그 | OpenAPI 기반 계약 테스트/스키마 회귀 테스트 | `test_*_schema_contract` 추가 |
| D-04 | OpenAI + Gemini | 기본/폴백 모델 간 출력 포맷·품질 편차 가능 | Hard Gate 기준 미달 급증, 폴백 후 결과 품질 하락 | high | medium | Hard Gate 실패율 상승, `fallback_rate` 급증 | 공통 응답 정규화 계층, 모델별 품질 가중치 | 품질 샘플링 규칙 + 폴백 테스트 |
| D-05 | Redis Queue | 상태 전이 SSOT는 정의됐으나 큐 세부 보장(at-least-once/중복 처리) 미정 | 중복 처리/재시도 폭증으로 과금/KPI 왜곡 | high | medium | `ACTIVE_JOB_ALREADY_EXISTS`, `PAGE_RETRY_LIMIT_EXCEEDED`, `QUEUE_CAPACITY_EXCEEDED` | 멱등 키 범위 확장, 중복소비 방지 설계 | 큐 소비자 상태전이 테스트 보강 |
| D-06 | PostgreSQL + Alembic | 마이그레이션 규칙은 있으나 운영 이행 전략(롤백/락/다운타임) 미정 | 배포 시 스키마 불일치로 API 장애 | high | medium | migration 실패 로그, API 5xx 증가 | preflight/rollback/lock runbook 표준화 | DB 변경 체크리스트/사전 검증 |
| D-07 | TossPayments | redirect 파라미터 신뢰·검증 경계가 설계 단계에만 존재 | 금액 변조/세션 만료/승인 실패 시 UX 단절 | high | medium | `PAYMENT_AMOUNT_MISMATCH`, `NOT_FOUND_PAYMENT_SESSION`, `UNAUTHORIZED_KEY` | 서버 재검증 강제(amount/orderId), 실패 UX 표준화 | 결제 리다이렉트 테스트 |
| D-08 | Cloudflare R2 | R2 접근 권한/서명 URL TTL 정책 미정 | 다운로드 만료/접근 거부/리소스 누락 | medium | medium | 다운로드 실패율 상승, URL 만료 로그 | URL TTL 표준, 재발급 정책, 객체 수명주기 정의 | 스토리지 만료 시나리오 테스트 |

## 3) 운영 리스크 (Operational Risks)

| ID | 의존성 | 제약사항 | 오동작 가능성 | 심각도 | 가능성 | 탐지 신호(로그/메트릭/app_code) | 완화책 | 선행 작업(테스트/문서/구현) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| O-01 | OpenAI/Gemini | 외부 API rate limit/장애 | 처리 지연, 대량 실패, fallback 연쇄 | high | high | 타임아웃 증가, fallback_rate 급증, 처리시간 p95 증가 | 타임아웃/재시도/서킷브레이커 세분화 | 외부 API 장애 주입 테스트 |
| O-02 | 비용 정책 + 환율 스냅샷 | fail-closed 정책으로 비용/환율 이상 시 신규 처리 차단 | 전체 처리 중단에 가까운 가용성 저하 | high | medium | `COST_DAILY_LIMIT_EXCEEDED`, `FX_RATE_UNAVAILABLE` 급증 | 비용 버짓 분리(하드/소프트), 환율 캐시 fallback 계층 | 비용/환율 장애 테스트 |
| O-03 | Google 로그인 스크립트 | 브라우저 정책/차단기/네트워크로 외부 스크립트 로드 실패 | 로그인 불가(초기 진입 실패) | high | medium | 로그인 버튼 렌더 실패 비율, Auth 시작률 하락 | 대체 진입 경로 유지, 로드 상태 모니터링 | 스크립트 실패 E2E |
| O-04 | TossPayments 위젯 | 키 불일치/등록 문제/렌더 타이밍 이슈 | 결제 페이지 렌더 실패, 결제 승인 실패 | high | medium | `UNAUTHORIZED_KEY`, `FORBIDDEN_REQUEST`, `NOT_REGISTERED_PAYMENT_WIDGET` | 키 관리 체크리스트 + 렌더 전 버튼 비활성 | 결제 위젯 렌더/승인 E2E |
| O-05 | Redis | 큐 적체/worker 중단 | 처리 지연, retry 상한 초과 증가 | high | medium | 큐 길이 증가, `QUEUE_CAPACITY_EXCEEDED`, `PAGE_RETRY_LIMIT_EXCEEDED` | 큐 백프레셔/동시성 자동조정 | 큐 모니터링 대시보드 |
| O-06 | PostgreSQL | 연결 풀 고갈/락 경합 | API 지연 및 실패, 상태 전이 누락 | high | medium | DB wait time 증가, 5xx 증가 | 풀 정책/쿼리 타임아웃 표준화 | DB 성능 회귀 테스트 |
| O-07 | Playwright | E2E flaky | 릴리즈 게이트 지연/오판단 | medium | high | 재시도 의존 증가, 테스트 통과율 변동 | 고정 fixture/격리 환경, flaky 격리 실행 | E2E 안정성 지표 도입 |
| O-08 | Vitest/Pytest | 테스트 명령은 정의됐으나 실제 테스트 파일 미구현 구간 존재 | 품질 게이트가 문서상으로만 존재 | high | high | 테스트 커버리지 공백, 회귀 누락 | 최소 필수 테스트 세트 우선 구현 | Phase별 RED 최소셋 강제 |
| O-09 | Hard Gate | 기준이 엄격하여 업스트림 품질 변동 시 실패율 급증 | 사용자 체감 가용성 하락(결과 미노출 증가) | medium | medium | Hard Gate 실패율, `failed` 상태 비중 증가 | Soft Gate + 수동검토 큐 설계 | 실패 데이터 샘플링 분석 |
| O-10 | app_code 매핑 | 백엔드/프론트 메시지 테이블 드리프트 가능 | 동일 장애를 다른 메시지로 안내 | medium | medium | app_code 미매핑 로그, CS 문의 증가 | app_code 단일 맵 소스 + UI snapshot 테스트 | 오류 매핑 회귀 테스트 |

## 4) 1차 우선순위 Top 8 (즉시 대응 완료)

1. D-01 의존성 매니페스트/락파일 부재
2. O-01 외부 AI API rate limit/장애
3. O-08 테스트 게이트 문서-구현 격차
4. D-02 Google 로그인 SDK 경로 취약성
5. D-05 Redis 중복 처리/상태 전이 왜곡 위험
6. D-07 결제 리다이렉트 검증 경계 취약성
7. O-02 비용/환율 fail-closed로 인한 가용성 저하
8. O-04 결제 위젯 키/렌더 실패

## 4-1) 1차 리스크 묶음 병행 실행 그룹 (완료)

- 묶음 A 재현성/의존성: `D-01`
- 묶음 B 외부 AI/비용 가용성: `O-01`, `O-02`
- 묶음 C 인증/결제 외부 SDK 안정성: `D-02`, `D-07`, `O-04`
- 묶음 D 큐/멱등/상태전이: `D-05`
- 묶음 E 테스트 게이트 실체화: `O-08`

## 5) 2차 우선순위 Top 8 (즉시 대응 완료)

1. D-03 API 스키마/계약 자동검증 부재
2. D-04 OpenAI/Gemini 출력 포맷·품질 편차
3. D-06 PostgreSQL/Alembic 마이그레이션 운영 이행 전략 미정
4. O-05 Redis 큐 적체/워커 중단
5. O-06 PostgreSQL 연결 풀 고갈/락 경합
6. O-03 Google 로그인 스크립트 로드 실패 잔여 리스크
7. O-09 Hard Gate 변동성으로 결과 미노출 증가
8. O-07 E2E flaky로 릴리즈 게이트 신뢰도 저하

## 5-1) 2차 리스크 묶음 병행 실행 그룹 (완료)

- 묶음 A 계약/오류 규약 일관성: `D-03`
- 묶음 B AI 품질 안정화: `D-04`, `O-09`
- 묶음 C 데이터 계층/배치 안정성: `D-06`, `O-05`, `O-06`
- 묶음 D 인증 진입/릴리즈 신뢰도: `O-03`, `O-07`

## 6) 3차 우선순위 Top 8 (컴플라이언스 전용, 즉시 대응 완료)

1. C-01 `LICENSE` 부재
2. C-02 `NOTICE` 부재
3. C-03 SPDX SBOM 부재
4. C-04 CycloneDX SBOM 부재
5. C-05 Third-party 고지 매핑 부재
6. C-06 매니페스트/락파일 부재
7. C-07 금지 라이선스 정책 부재
8. C-08 검증 루프/소유권 부재

## 6-1) 3차 리스크 묶음 병행 실행 그룹 (완료)

- 묶음 A 라이선스 기본 증빙: `C-01`, `C-02`, `C-05`
- 묶음 B SBOM 추적성: `C-03`, `C-04`
- 묶음 C 재현성/버전 통제: `C-06`
- 묶음 D 정책/거버넌스: `C-07`, `C-08`

## 7) 실행 가능한 대응 백로그 (4차 준비)

### 지금 당장 가능한 조치 (문서/정책)

- 계약 테스트 기준(OpenAPI 계약 + `app_code` 매핑)을 SSOT로 고정한다.
- AI 출력 정규화 규칙과 Hard Gate 전처리 기준을 문서로 고정한다.
- DB migration preflight/rollback/lock runbook을 운영 규칙으로 정의한다.
- `queue_depth`, `db_wait_time` 임계치를 운영 지표로 정의한다.
- R2 presigned URL TTL/재발급 정책을 문서로 고정한다.
- 라이선스 드리프트 대응을 위해 SBOM 2종 갱신 절차를 운영 체크리스트에 포함한다.

### 구현 단계 선행조건 (테스트/코드)

- Contract: `test_*_schema_contract` + `app_code` 매핑 회귀 테스트 추가
- AI: `test_fallback_strategy` + 골든셋 품질 드리프트 테스트 추가
- DB/Queue: 마이그레이션 preflight, 큐 백프레셔, 워커 헬스체크 테스트 추가
- Storage: presigned URL 만료/재발급 시나리오 테스트 추가
- Compliance: 라이선스 스캔 자동화와 배포 파이프라인 증빙 첨부 자동화

## 8) 1차 Top 8 즉시 대응 실행 상태 (완료)

| 리스크 ID | 상태 | 즉시 통제 규칙 | 탐지 신호 | 문서 반영 위치 | 완료 신호 |
| --- | --- | --- | --- | --- | --- |
| D-01 | 완료(문서/정책, 2026-02-09) | 의존성 매니페스트 표준과 버전 고정 정책을 SSOT 문서에 명시한다. | CI/로컬 재현성 불일치, 부트스트랩 실패 로그 | `AGENTS.md`, `Plans.json`, `Plans.md` | `rg -n "매니페스트|버전 고정 정책" AGENTS.md Plans.md` 결과가 1건 이상이다. |
| O-01 | 완료(문서/정책, 2026-02-09) | OpenAI/Gemini 타임아웃, 재시도, 서킷브레이커를 분리 운영하고 fallback 경보를 강제한다. | `fallback_rate` 급증, 처리시간 p95 증가 | `AGENTS.md`, `docs/specs/PRD.md`, `Plans.md` | `rg -n "fallback_rate|서킷브레이커|타임아웃" AGENTS.md docs/specs/PRD.md Plans.md` 결과가 1건 이상이다. |
| O-08 | 완료(문서/정책, 2026-02-09) | 최소 테스트 게이트(Auth/Payment/Fallback/Queue/app_code 매핑)를 문서상 차단 규칙으로 고정한다. | 테스트 커버리지 공백, 게이트 우회 | `AGENTS.md`, `Plans.json`, `Plans.md` | `AGENTS.md`에 `Top 8 최소 테스트 게이트`가 존재하고 `plans_sync check`가 통과한다. |
| D-02 | 완료(문서/정책, 2026-02-09) | Google 로그인 실패 코드를 표준화하고 대체 로그인 경로를 운영 기본값으로 둔다. | `GOOGLE_ID_TOKEN_INVALID`, `GOOGLE_AUTH_EXCHANGE_FAILED` 증가 | `AGENTS.md`, `docs/specs/PRD.md`, `Plans.md` | `rg -n "GOOGLE_ID_TOKEN_INVALID|GOOGLE_AUTH_EXCHANGE_FAILED|GOOGLE_CLIENT_ID_NOT_CONFIGURED" AGENTS.md docs/specs/PRD.md Plans.md` 결과가 1건 이상이다. |
| D-05 | 완료(문서/정책, 2026-02-09) | 쓰기 API 멱등 키와 큐 중복소비 방지, 재시도 상한 규칙을 함께 강제한다. | `IDEMPOTENCY_IN_PROGRESS`, `PAGE_RETRY_LIMIT_EXCEEDED`, `QUEUE_CAPACITY_EXCEEDED` | `AGENTS.md`, `docs/specs/PRD.md`, `Plans.md` | `rg -n "Idempotency-Key|PAGE_RETRY_LIMIT_EXCEEDED|QUEUE_CAPACITY_EXCEEDED" AGENTS.md docs/specs/PRD.md Plans.md` 결과가 1건 이상이다. |
| D-07 | 완료(문서/정책, 2026-02-09) | 결제 `amount/orderId` 서버 재검증과 세션 만료 처리 기준을 고정한다. | `PAYMENT_AMOUNT_MISMATCH`, `NOT_FOUND_PAYMENT_SESSION` | `AGENTS.md`, `docs/specs/PRD.md`, `Plans.md` | `rg -n "PAYMENT_AMOUNT_MISMATCH|NOT_FOUND_PAYMENT_SESSION|amount/orderId" AGENTS.md docs/specs/PRD.md Plans.md` 결과가 1건 이상이다. |
| O-02 | 완료(문서/정책, 2026-02-09) | 환율/비용 이상 시 fail-closed를 유지하고 장애 알림을 의무화한다. | `COST_DAILY_LIMIT_EXCEEDED`, `FX_RATE_UNAVAILABLE` | `AGENTS.md`, `docs/specs/PRD.md`, `Plans.md` | `rg -n "fail-closed|COST_DAILY_LIMIT_EXCEEDED|FX_RATE_UNAVAILABLE" AGENTS.md docs/specs/PRD.md Plans.md` 결과가 1건 이상이다. |
| O-04 | 완료(문서/정책, 2026-02-09) | 결제 위젯 키 검증과 렌더 완료 전 결제 버튼 비활성 규칙을 운영 기본값으로 둔다. | `UNAUTHORIZED_KEY`, `FORBIDDEN_REQUEST`, `NOT_REGISTERED_PAYMENT_WIDGET` | `AGENTS.md`, `docs/specs/PRD.md`, `Plans.md` | `rg -n "UNAUTHORIZED_KEY|FORBIDDEN_REQUEST|NOT_REGISTERED_PAYMENT_WIDGET" AGENTS.md docs/specs/PRD.md Plans.md` 결과가 1건 이상이다. |

## 9) 2차 Top 8 즉시 대응 실행 상태 (완료)

| 리스크 ID | 상태 | 즉시 통제 규칙 | 탐지 신호 | 문서 반영 위치 | 완료 신호 |
| --- | --- | --- | --- | --- | --- |
| D-03 | 완료(문서/정책, 2026-02-09) | OpenAPI 계약과 `app_code` 매핑을 단일 SSOT 기준으로 고정한다. | 계약 테스트 실패, app_code 미매핑 | `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` | `rg -n "D-03|OpenAPI|app_code 매핑" docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` 결과가 1건 이상이다. |
| D-04 | 완료(문서/정책, 2026-02-09) | 모델별 출력 정규화와 Hard Gate 전처리 기준을 운영 규칙으로 고정한다. | Hard Gate 실패율 상승, 폴백 편차 증가 | `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` | `rg -n "D-04|출력 정규화|Hard Gate 전처리" docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` 결과가 1건 이상이다. |
| D-06 | 완료(문서/정책, 2026-02-09) | 마이그레이션 preflight/rollback/lock runbook을 필수 운영 절차로 고정한다. | DB migration 실패 로그, API 5xx 증가 | `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` | `rg -n "D-06|preflight|rollback|lock runbook" docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` 결과가 1건 이상이다. |
| O-05 | 완료(문서/정책, 2026-02-09) | 큐 백프레셔와 워커 헬스체크를 기본 운영 규칙으로 고정한다. | `QUEUE_CAPACITY_EXCEEDED`, 큐 길이 급증 | `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` | `rg -n "O-05|큐 백프레셔|워커 헬스체크" docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` 결과가 1건 이상이다. |
| O-06 | 완료(문서/정책, 2026-02-09) | 커넥션 풀과 DB wait time 임계치 기준을 운영 지표로 고정한다. | DB wait time 증가, 5xx 증가 | `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` | `rg -n "O-06|db_wait_time|커넥션 풀" docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` 결과가 1건 이상이다. |
| O-03 | 완료(문서/정책, 2026-02-09) | 로그인 스크립트 로드 실패 시 대체 진입 UX를 표준 운영 동선으로 고정한다. | 로그인 버튼 렌더 실패, Auth 시작률 하락 | `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` | `rg -n "O-03|대체 진입 UX|스크립트 로드 실패" docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` 결과가 1건 이상이다. |
| O-09 | 완료(문서/정책, 2026-02-09) | Hard Gate 변동성 대응을 위해 실패 샘플링/수동검토 큐 운영 기준을 고정한다. | Hard Gate 실패율, `failed` 비중 증가 | `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` | `rg -n "O-09|수동검토 큐|Hard Gate 실패율" docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` 결과가 1건 이상이다. |
| O-07 | 완료(문서/정책, 2026-02-09) | E2E flaky 분리 실행과 quarantine 정책을 릴리즈 게이트 규칙으로 고정한다. | 재시도 의존 증가, 통과율 변동 | `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` | `rg -n "O-07|flaky|quarantine" docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` 결과가 1건 이상이다. |

## 10) 3차 Top 8 즉시 대응 실행 상태 (완료)

| 리스크 ID | 상태 | 즉시 통제 규칙 | 탐지 신호 | 문서 반영 위치 | 완료 신호 |
| --- | --- | --- | --- | --- | --- |
| C-01 | 완료(문서/정책, 2026-02-09) | `LICENSE`를 루트 필수 파일로 고정한다. | LICENSE 존재성 검증 실패 | `LICENSE`, `AGENTS.md` | `Test-Path LICENSE`가 `True`다. |
| C-02 | 완료(문서/정책, 2026-02-09) | `NOTICE`를 배포 필수 고지로 고정한다. | NOTICE 존재성 검증 실패 | `NOTICE`, `AGENTS.md` | `Test-Path NOTICE`가 `True`다. |
| C-03 | 완료(문서/정책, 2026-02-09) | SPDX SBOM 생성을 필수 증빙으로 고정한다. | SPDX SBOM 누락 | `docs/compliance/SBOM.spdx.json` | `Test-Path docs/compliance/SBOM.spdx.json`가 `True`다. |
| C-04 | 완료(문서/정책, 2026-02-09) | CycloneDX SBOM 생성을 필수 증빙으로 고정한다. | CycloneDX SBOM 누락 | `docs/compliance/SBOM.cyclonedx.json` | `Test-Path docs/compliance/SBOM.cyclonedx.json`가 `True`다. |
| C-05 | 완료(문서/정책, 2026-02-09) | Third-party 고지 문서를 단일 경로로 고정한다. | 의존성-라이선스 매핑 누락 | `docs/compliance/THIRD_PARTY_NOTICES.md` | `rg -n "Next.js|FastAPI|psycopg" docs/compliance/THIRD_PARTY_NOTICES.md` 결과가 1건 이상이다. |
| C-06 | 완료(문서/정책, 2026-02-09) | 매니페스트/락파일과 exact 버전 정책을 고정한다. | 재현성 검증 실패 | `package.json`, `package-lock.json`, `requirements*.txt`, `docs/compliance/DEPENDENCY_VERSION_MATRIX.md` | 존재성 검증과 버전 매트릭스 검증이 통과한다. |
| C-07 | 완료(문서/정책, 2026-02-09) | 금지 라이선스 정책을 문서로 고정한다. | 정책 부재 또는 금지군 유입 | `docs/compliance/OSS_LICENSE_POLICY.md` | `rg -n "GPL|AGPL|SSPL|금지" docs/compliance/OSS_LICENSE_POLICY.md` 결과가 1건 이상이다. |
| C-08 | 완료(문서/정책, 2026-02-09) | 컴플라이언스 검증 루프와 문서 소유 경로를 SSOT에 고정한다. | 검증 명령 누락, 책임 경계 불명확 | `AGENTS.md`, `README.md`, `Plans.json`, `Plans.md` | plans_sync 3종 + 컴플라이언스 검증 명령이 문서에 존재한다. |

## 11) 분석 한계 및 가정

- 현재 저장소는 문서 중심이며 실제 애플리케이션 코드는 후속 구현 단계다.
- 본 리포트는 문서에 명시된 스택/SDK 기준으로 작성했으며, 구현 단계에서 위험도는 재평가한다.
- 외부의존(OpenAI/Gemini/Google/Toss/R2)은 OSS가 아니지만, 장애 가능성 분석 범위에 포함한다.
- 3차 컴플라이언스 완료 상태는 코드 구현 완료가 아니라 문서/증빙 기준 충족을 의미한다.

## 12) DR-07 외부 SDK 정책 변화 리스크 상태 (Closed)

| 항목 | 값 |
| --- | --- |
| 리스크 ID | DR-07 |
| 상태 | Closed (문서/검증 범위, 2026-02-09) |
| 통제 방식 | 공식 문서 해시 자동 감시(`sdk_policy_watch --strict`) |
| 근거 파일 | `docs/compliance/external_sdk_watchlist.json`, `docs/compliance/external_sdk_snapshot.json`, `.github/workflows/external-sdk-watch.yml` |
| 차단 정책 | 변경/오류 감지 시 fail-closed로 워크플로 실패 처리 |
| 완료 신호 | `python scripts/sdk_policy_watch.py --watchlist docs/compliance/external_sdk_watchlist.json --snapshot docs/compliance/external_sdk_snapshot.json --strict` 통과 |
