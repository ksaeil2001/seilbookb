# Plans.md

## 시작 체크리스트 (핵심 5단계)
- [ ] Phase 0에서 개발 환경과 인프라 정합성을 확보한다.
- [ ] Phase 1에서 업로드~OCR~번역~식자 백엔드 파이프라인을 최소 완성한다.
- [ ] Phase 2에서 데이터베이스/스토리지/큐 상태 모델 SSOT를 고정한다.
- [ ] Phase 3에서 업로드, 결과 뷰어, 편집 UX를 연결해 사용자 흐름을 완성한다.
- [ ] Phase 4에서 Hard/Soft Gate를 통과하고 배포 준비를 완료한다.

## 1. 목적 및 요약
이 프로젝트는 Next.js(App Router) 프론트엔드와 FastAPI 백엔드, PostgreSQL/Redis, Cloudflare R2, Docker 기반으로 OCR-번역-인페인팅-식자를 단일 파이프라인으로 자동화해 페이지당 평균 30초 이내 처리와 고품질 읽기 경험(누락 없는 번역, 레이아웃 안정, 최소 편집)을 동시에 달성하는 MVP v1.0을 목표로 한다.

## 2. 진행 상황
진행 규칙: 각 Phase 시작 시 목적/입력 1문장을 기록하고, 종료 시 실행 결과/검증 결과를 1~2문장으로 기록한다. 검증 실패 시 보완 테스트 또는 명세 보강을 즉시 1회 수행한다.

### Phase 0: 환경 설정 & 인프라
- [ ] Next.js(App Router)+TypeScript+Tailwind CSS 프로젝트 초기화 후 `npm run dev` 실행 확인
- [ ] FastAPI(Python 3.11+)+Pydantic v2 기본 앱 구성 후 `uvicorn app.main:app --reload` 실행 확인
- [ ] Backend 계층 구조(`router`, `service`, `crud`, `schema`) 디렉터리 생성
- [ ] `.env.example`에 OpenAI/Gemini/PostgreSQL/Redis/R2 환경 변수 키 정의(값 하드코딩 금지)
- [ ] Docker Compose에 `frontend`, `backend`, `postgres`, `redis` 서비스 초안 작성
- [ ] PostgreSQL 컨테이너 기동 및 백엔드 연결 smoke test 1회 수행
- [ ] Redis 컨테이너 기동 및 큐 연결 smoke test 1회 수행
- [ ] FastAPI `/health` 엔드포인트 구현 및 컨테이너 healthcheck 연결
- [ ] 공통 실행 명령(Frontend/Backend/Test) README 섹션 추가
- [ ] 로컬 개발 환경에서 `pytest`, `npm run test` 실행 경로 문서화

### Phase 1: 핵심 백엔드 로직
- [ ] `POST /jobs` 업로드 API 요청/응답 Pydantic 스키마 정의
- [ ] ZIP 파일 검증 유틸(확장자, 손상 파일, 최대 페이지 수) 구현
- [ ] 업로드 파일 Cloudflare R2 저장 비동기 서비스 함수 구현
- [ ] 업로드 완료 시 `jobs`, `pages` 초기 레코드 생성 CRUD 구현
- [ ] Redis 큐 적재 payload 스키마 정의 및 enqueue 로직 구현
- [ ] Worker `preprocess` 단계(페이지 분리/정렬/메타데이터 수집) 구현
- [ ] OCR 어댑터(OpenAI API 기본 경로) 구현
- [ ] OCR 실패 시 Gemini/Vision fallback 분기 구현
- [ ] OCR 결과 저장 및 `input_text_count` 집계 로직 구현
- [ ] Translation 어댑터(OpenAI API 기본 경로) 구현
- [ ] Translation 실패 시 Gemini fallback 분기 구현
- [ ] 번역 결과 저장 및 `output_text_count` 집계 로직 구현
- [ ] Hard Gate 1차 검사(`input_text_count == output_text_count`) 자동 체크 함수 구현
- [ ] Inpainting/Typesetting 실행 인터페이스 및 스텁 구현
- [ ] 레이아웃 안정성 검사(`bbox_overflow`, `min_font_pt`) 계산 로직 구현
- [ ] 페이지 상태 전이(`success`, `partial`, `fail`, `canceled`) 처리 로직 구현
- [ ] 작업 취소 API 및 워커 취소 처리 로직 구현
- [ ] 실패 페이지 재시도 API(최대 3회) 구현
- [ ] 공통 에러 응답(`HTTP status`, `app_code`, 메시지) 매핑 테이블 구현
- [ ] `GET /jobs/{job_id}` 진행률/상태 조회 API 구현

### Phase 2: 데이터베이스 & 스토리지
- [ ] SQLAlchemy async 엔진/세션 팩토리 구성
- [ ] `users`, `jobs`, `pages` 핵심 모델 정의
- [ ] `idempotency_keys`, `credit_ledger`, `api_cost_events` 모델 정의
- [ ] `reports`, `security_events`, `download_events`, `cohort_100_members` 모델 정의
- [ ] PRD 상태 모델(`job_status`, `page_status`) enum/제약 조건 반영
- [ ] Alembic 마이그레이션 적용 범위 문서화(실제 파일 수정은 사용자 승인 후 진행)
- [ ] CRUD 레이어 비동기 패턴 통일 및 서비스 계층 호출 규칙 고정
- [ ] Idempotency-Key 검사 미들웨어 구현
- [ ] Cloudflare R2 객체 키 네이밍 규칙(원본/중간/결과) 문서화
- [ ] R2 업로드/다운로드/삭제 통합 테스트 케이스 작성
- [ ] 작업/페이지 상태 변경 이벤트 로깅 스키마 구현
- [ ] KPI 집계 쿼리(`success_rate`, `usable_rate`, `fallback_rate`, `cost_per_page`) 초안 작성
- [ ] 일일 비용 상한 차단 및 환율 누락 fail-closed 분기 구현
- [ ] 사용자별 활성 작업 1건 제한 제약(DB+서비스) 구현
- [ ] 데이터 보존/정리 배치 작업 스펙 문서화

### Phase 3: 프론트엔드 구현
- [ ] Next.js App Router `app/` 라우트 골격(로그인/업로드/작업상세) 생성
- [ ] 로그인 상태 확인 및 보호 라우트 훅 구현
- [ ] ZIP 업로드 컴포넌트(드래그앤드롭+유효성 검증) 구현
- [ ] 업로드 API 연동 훅과 진행률 UI 연결
- [ ] 작업 목록 화면(상태 배지+진행률) 구현
- [ ] 작업 상세 화면(페이지 상태 테이블) 구현
- [ ] 결과 뷰어 UI(원본/번역 토글+확대/축소) 구현
- [ ] 번역/식자 편집 패널(페이지별 텍스트 수정 폼) 구현
- [ ] Hard Gate 경고 UI(누락/레이아웃 경고) 표시 컴포넌트 구현
- [ ] 재시도/취소 액션 버튼 및 제약 조건 처리 구현
- [ ] 결과 다운로드 버튼 및 링크 만료 예외 처리 구현
- [ ] 신고(report) 모달 및 제출 흐름 구현
- [ ] `app_code` 기반 오류 메시지 매핑 테이블 프론트 반영
- [ ] React Query 기반 서버 상태 분리(로컬 UI 상태와 분리)
- [ ] Tailwind 반응형/접근성 점검(모바일 포함) 수행
- [ ] 프론트 테스트(`npm run test`) 업로드/상세/편집 3개 케이스 추가

### Phase 4: 통합 및 검증
- [ ] Docker Compose 기준 전체 스택 기동 검증
- [ ] 샘플 ZIP 기준 E2E(업로드 -> 번역 -> 다운로드) 자동 테스트 1건 작성
- [ ] 페이지별 처리 시간 측정 로깅 추가 및 평균 `< 30초` 검증
- [ ] 페이지 타임아웃(120초) 시나리오 테스트 수행
- [ ] Hard Gate 자동 검증 리포트(누락 없음, `bbox_overflow == 0`, `min_font_pt >= 10`) 생성
- [ ] Soft Gate 골든셋 샘플링 평가 시트 준비 및 90% 통과 여부 기록
- [ ] 오역 체크리스트(5개 항목) 자동 집계 스크립트 작성 및 4/5 통과 검증
- [ ] 성공률/사용 가능률 집계 쿼리 실행(`>= 90%`, `>= 95%`) 검증
- [ ] fallback_rate, cost_per_page 측정값 기록
- [ ] 권한/RBAC/오류 코드 정책 스모크 테스트 수행
- [ ] OpenAI 장애 모의 후 Gemini fallback 동작 검증
- [ ] staging 배포용 Docker 이미지 빌드 및 기동 확인
- [ ] 운영 체크리스트(로그/알림/비용 통제/차단 정책) 실행
- [ ] MVP 사용자 가이드 초안 작성 및 배포 산출물 포함
- [ ] MVP Go/No-Go 의사결정 문서 작성

## 3. 의사결정 로그
- 기록 템플릿: `YYYY-MM-DD | 결정 | 근거 | 대안 | 영향 범위 | 담당`
- 2026-02-07 | 프로젝트 진행 SSOT 문서를 루트 `Plans.md`로 고정 | 세션 간 컨텍스트 손실 방지와 진행 추적 일원화 필요 | 이슈 트래커 단독 운영 | 전체 개발/검증/운영 문서 흐름 | 팀
- 2026-02-07 | AI Ops 기본 경로를 OpenAI API로 설정하고 Gemini/Vision을 fallback으로 유지 | AGENTS.md 강제 스택 및 PRD 가용성 전략과 일치 | 단일 벤더 사용 | OCR/번역/복구 안정성 | 팀
- 2026-02-07 | 상태 모델을 PRD SSOT(`job_status`, `page_status`)와 1:1 매핑 | KPI 집계와 게이트 검증 정합성 확보 필요 | 임의 상태값 확장 | API/DB/프론트 상태 표시 전 영역 | 팀

## 4. 현재 맥락
현재는 프로젝트 초기화 및 `Plans.md` 생성 단계이며, 구현 코드는 본격 착수 전 상태로 다음 액션은 Phase 0 작업을 순차 실행해 개발 환경과 인프라 정합성을 먼저 확보하는 것이다.

## 5. 검증 계획
1. Phase 0 종료 검증: `npm run dev`, `uvicorn app.main:app --reload`, `pytest`, `npm run test` 기본 실행 성공과 PostgreSQL/Redis 연결 smoke test 통과를 확인한다.
2. Phase 1 종료 검증: 업로드 -> OCR -> 번역 -> 식자 파이프라인의 비동기 처리, 상태 전이, app_code 에러 응답, 취소/재시도 제약(최대 3회)이 API 테스트로 재현되는지 확인한다.
3. Phase 2 종료 검증: DB 모델과 상태 enum이 PRD SSOT와 일치하는지 점검하고, R2 CRUD 테스트 및 idempotency/활성 작업 1건 제한/비용 상한 차단 규칙을 통합 테스트로 검증한다.
4. Phase 3 종료 검증: 업로드, 진행률 조회, 결과 뷰어, 편집, 재시도/취소, 신고 플로우가 UI 테스트에서 끊김 없이 동작하고 모바일 레이아웃이 깨지지 않는지 확인한다.
5. Phase 4 종료 검증(Hard/Soft/User Gate): Hard Gate(`input_text_count == output_text_count`, `bbox_overflow == 0`, `min_font_pt >= 10`) 자동 통과를 확인하고, Soft Gate(골든셋 90%, 오역 4/5)와 KPI(성공률 >= 90%, 사용 가능률 >= 95%, 평균 처리 시간 < 30초/페이지), User Gate(CSAT >= 4.0, 무편집 읽기 비율 >= 90%)를 기준치와 비교해 Go/No-Go를 결정한다.
6. 실패 대응 규칙: 각 Phase 검증 실패 시 즉시 보완 테스트 1건 추가 또는 명세 보강 1건을 수행한 뒤 동일 검증을 1회 재실행한다.
