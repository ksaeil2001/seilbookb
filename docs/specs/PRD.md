# PRD: 만화/웹툰 AI 번역 서비스 (MVP)

- 최종 업데이트: 2026-02-07
- 목표 완료일: PRD 승인일 기준 6주
- 전략: Quick Wins (실사용 가능한 첫 버전)

---

## 문서 운영 원칙

- PRD에는 현재 유효한 제품 요구사항과 검증 기준만 유지한다.
- 상세 변경 이력은 PR/이슈 트래커에서 관리한다.
- 구현 상세(DDL, 에러 매트릭스, 보안 runbook, 운영 체크리스트)는 별도 운영 문서로 분리한다.

---

## Executive Summary

### 제품 정체성

- 제품 정의: 이미지 기반 만화/웹툰 번역 결과물 생성 엔진
- 핵심 가치:
  - 시간적 가치: 페이지당 평균 30초 내 처리
  - 문학적 가치: 레이아웃/말투/용어 일관성을 갖춘 읽기 경험

### North Star (12개월)

- 사용자가 일상적으로 만화/웹툰을 번역해 읽는 반복 사용 도구로 정착한다.

### 성공 정의 (MVP)

- Hard Gate (자동):
  - 누락 없음: input_text_count == output_text_count
  - 레이아웃 안정: bbox_overflow == 0 and min_font_pt >= 10
- Soft Gate (샘플링):
  - 자연스러움: 골든셋 수동 평가 90% 통과
  - 정확도: 오역 체크리스트 5개 중 4개 통과
- 사용자 Gate (cohort_100):
  - CSAT 평균 >= 4.0/5.0
  - 무편집 읽기 비율 >= 90%

### 상태 모델 SSOT

- job_status: pending, processing, completed, failed, canceled
- page_status: success, partial, fail, canceled
- terminal_non_canceled_pages: success, partial, fail
- 과금 규칙: success=1.0, partial=0.5, fail/canceled=0

---

## Problem & Solution

### 문제

- 기존 도구는 품질 편차가 크고 레이아웃/용어 일관성이 낮아 몰입을 해친다.
- 수동 번역은 시간 비용이 높다.

### 솔루션

- OCR + 번역 + 인페인팅 + 식자를 단일 파이프라인으로 자동화한다.
- 품질 우선 원칙을 적용해, 속도 목표보다 읽기 가능 품질을 우선한다.

---

## Target Users

- 1차 타깃: 해외 만화/웹툰을 빠르게 읽고 싶은 개인 사용자
- 콘텐츠 범위: 성인 등급 포함
- 운영 차단 대상: 실존 인물 노출/개인정보 포함 이미지

---

## System Architecture

### 파이프라인

- Preprocess -> Text Detection -> OCR -> Translation -> Inpainting/Typesetting -> Postprocess

### 기술 스택

- Frontend: Next.js + TypeScript
- Backend: FastAPI + Python
- Storage/DB: Cloudflare R2 + PostgreSQL
- Queue: Redis + Worker

### 내결함성

- OpenAI 장애: Gemini fallback
- OCR 신뢰도 저하: Vision fallback
- 인페인팅 실패: 제한적 fallback

---

## Core Features (MVP Scope)

### In Scope

- 회원가입/로그인/세션 유지
- ZIP 업로드 -> 번역 -> 다운로드
- 작업 진행률 및 페이지별 상태 확인
- 결과 인라인 편집(허용 상태만)
- 실패 페이지 재시도(상한 3회)
- 신고(Report) 생성 및 관리자 처리
- 크레딧 차감/원장 기록

### Out of Scope

- 실시간 협업 편집
- 공개 API 제공
- 고급 스타일 편집기

---

## User Flow

1. 사용자는 로그인 후 번역 파일을 업로드한다.
2. 시스템은 작업을 생성하고 큐에서 페이지 단위로 처리한다.
3. 사용자는 진행률/상태를 조회한다.
4. 완료 후 결과물을 다운로드하거나 필요한 페이지를 편집/재시도한다.
5. 이슈가 있으면 신고를 생성한다.

---

## Business Model & Constraints

### 크레딧

- 신규 사용자 기본 크레딧 제공
- 페이지 상태별 차감 규칙 적용

### 운영 제약

- 사용자별 활성 작업 1건 제한
- 일일 비용 상한 초과 시 신규 작업 차단
- 환율 스냅샷 누락 시 fail-closed

### 성능 목표

- 평균 처리 시간: < 30초/페이지
- 페이지 타임아웃: 120초

---

## Content Moderation

- 업로드 전 경고 문구 제공
- 결과 페이지마다 신고 기능 제공
- 신고 상태: open, reviewing, resolved, rejected
- 중복 신고 및 쿨다운 정책 적용

---

## Quality Assurance

### 테스트 원칙

- 골든셋 회귀 테스트를 릴리즈 게이트로 사용
- KPI 계산은 최종 terminal 상태 기준으로 집계

### 최소 게이트

- 성공률 >= 90%
- 사용 가능률 >= 95%
- 회귀세트 기준 품질 임계 충족

---

## Database Schema (요약)

### 핵심 엔터티

- users: 계정/권한/크레딧
- jobs: 작업 단위 상태/진행률
- pages: 페이지 단위 결과/재시도/편집
- idempotency_keys: 쓰기 요청 멱등성
- credit_ledger: 크레딧 감사 원장
- api_cost_events: 외부 API 비용 원장
- reports: 신고 상태머신
- security_events: 보안 이벤트
- download_events, cohort_100_members: KPI 집계 근거

### 제약

- 시간 컬럼은 UTC TIMESTAMPTZ 기준
- append-only 원장 정책 유지
- 상태 전이와 과금 규칙은 PRD SSOT를 따른다

---

## API Endpoints (요약)

### 도메인

- Auth: signup/login/refresh/logout
- Users: me/csat
- Jobs: create/list/detail/cancel/download
- Pages: list/retry/edit/download
- Reports: create
- Admin: report review/resolve/reject

### 공통 규칙

- 쓰기 API는 Idempotency-Key 필수(인증 엔드포인트 예외)
- 표준 app_code로 오류를 분기한다
- 정책 차단은 은닉 우선 규칙을 적용한다

### 주요 app_code

- 입력: UNSUPPORTED_FILE_TYPE, MAX_PAGES_EXCEEDED, ARCHIVE_PARSE_FAILED
- 제한: TEMPORARILY_BLOCKED, DAILY_PAGE_LIMIT_EXCEEDED, HOURLY_PAGE_LIMIT_EXCEEDED, QUEUE_CAPACITY_EXCEEDED
- 비용: COST_DAILY_LIMIT_EXCEEDED, FX_RATE_UNAVAILABLE
- 경합: ACTIVE_JOB_ALREADY_EXISTS, IDEMPOTENCY_IN_PROGRESS, PAGE_NOT_EDITABLE, PAGE_RETRY_LIMIT_EXCEEDED

---

## Security & Privacy (요약)

- JWT 기반 인증 + Refresh 회전
- CSRF/CORS 기본 차단 정책
- RBAC(user/admin) 최소권한 적용
- Rate limiting 및 이상행동 이벤트 기록
- 민감정보 최소수집, 저장 암호화, 전송 TLS 강제
- override는 2인 승인 + 만료시간 + 사후조치 필수

---

## Success Metrics

### 기술 KPI

- success_rate = success / terminal_non_canceled_pages
- usable_rate = (success + partial) / terminal_non_canceled_pages
- no_edit_rate = count(edited=false and page_status=success) / count(page_status=success)
- fallback_rate = fallback_pages / terminal_non_canceled_pages
- cost_per_page = total_external_api_cost_krw / terminal_non_canceled_pages

### 운영 KPI

- DAU/MAU
- 크레딧 소진율
- 유료 전환율(관찰 지표)
- auth_failure_rate = failed_auth_events / total_auth_attempts
- payment_failure_rate = failed_payment_confirms / total_payment_confirms
- queue_depth = pending_queue_items
- hard_gate_fail_rate = hard_gate_failed_pages / terminal_non_canceled_pages

---

## Risk Mitigation

- API 장애: circuit breaker + fallback
- 비용 폭주: 일일 상한/차단/경보
- 과부하: 큐 모니터링 + 동시성 제어
- 정책 위반: 신고/검토/차단 프로세스

### Top 8 Immediate Controls

- `D-01` 트리거: 환경별 재현 실패, 관측 지표: bootstrap 실패율, 즉시 조치: 매니페스트/락파일 없는 변경 배포 차단, 복구 조건: 버전 고정 정책 문서와 SSOT 검증 명령 통과
- `O-01` 트리거: 외부 AI 타임아웃 급증, 관측 지표: `fallback_rate`, p95 처리시간, 즉시 조치: 공급자별 서킷브레이커/재시도 분리 적용, 복구 조건: fallback_rate 정상화와 오류율 기준선 회복
- `O-08` 트리거: 테스트 게이트 미구현 또는 우회, 관측 지표: 최소 게이트 누락 항목 수, 즉시 조치: 품질 게이트 미충족 상태에서 다음 Phase 진행 차단, 복구 조건: Auth/Payment/Fallback/Queue/app_code 회귀 게이트 문서 검증 완료
- `D-02` 트리거: Google 스크립트/토큰 검증 실패 증가, 관측 지표: `GOOGLE_ID_TOKEN_INVALID`, `GOOGLE_AUTH_EXCHANGE_FAILED`, 즉시 조치: 대체 로그인 경로 우선 노출, 복구 조건: Google 인증 오류율 정상화
- `D-05` 트리거: 중복 처리/재시도 폭증, 관측 지표: `IDEMPOTENCY_IN_PROGRESS`, `PAGE_RETRY_LIMIT_EXCEEDED`, `QUEUE_CAPACITY_EXCEEDED`, 즉시 조치: 큐 백프레셔와 멱등 키 경합 차단 강화, 복구 조건: 재시도 상한 초과 비율 기준선 회복
- `D-07` 트리거: 결제 무결성 경고 발생, 관측 지표: `PAYMENT_AMOUNT_MISMATCH`, `NOT_FOUND_PAYMENT_SESSION`, 즉시 조치: `amount/orderId` 재검증 실패 거래 승인 차단, 복구 조건: 무결성 실패 0건 유지
- `O-02` 트리거: 비용/환율 스냅샷 이상, 관측 지표: `COST_DAILY_LIMIT_EXCEEDED`, `FX_RATE_UNAVAILABLE`, 즉시 조치: fail-closed로 신규 작업 차단 및 운영 알림 발송, 복구 조건: 환율/비용 신호 정상화와 차단 해제 승인
- `O-04` 트리거: 결제 위젯 키/렌더 실패, 관측 지표: `UNAUTHORIZED_KEY`, `FORBIDDEN_REQUEST`, `NOT_REGISTERED_PAYMENT_WIDGET`, 즉시 조치: 위젯 렌더 실패 시 결제 버튼 비활성 유지, 복구 조건: 키 검증 통과 및 렌더 성공률 회복

---

### OSS License Compliance Controls

- 트리거: 라이선스 고지 파일 누락, 관측 지표: `LICENSE/NOTICE/THIRD_PARTY_NOTICES` 존재성 검증 실패, 즉시 조치: 배포 차단, 복구 조건: 고지 파일 복구와 검증 통과
- 트리거: SBOM 산출물 누락, 관측 지표: `SBOM.spdx.json/SBOM.cyclonedx.json` 존재성 검증 실패, 즉시 조치: 릴리즈 승인 중단, 복구 조건: SBOM 2종 동기화 완료
- 트리거: 매니페스트/락파일 미고정, 관측 지표: exact 버전 정책 위반 탐지, 즉시 조치: 머지 차단, 복구 조건: `package-lock.json` 및 `requirements*` 고정 버전 반영
- 트리거: 금지 라이선스 감지(`GPL/AGPL/SSPL`), 관측 지표: 라이선스 정책 검증 실패, 즉시 조치: 의존성 추가 차단, 복구 조건: 제거 또는 사전 승인 완료

---

### External SDK Policy Drift Control

- 트리거: Google/Toss/OpenAI 공식 문서 해시 변경 또는 fetch 오류
- 관측 지표: `external_sdk_watch_report.changed_items`, `external_sdk_watch_report.fetch_errors`
- 즉시 조치: `external-sdk-watch` 워크플로 실패 처리 + 이슈 자동 생성(권한 없으면 아티팩트만 저장)
- 복구 조건: watchlist/snapshot 재검증 후 `sdk_policy_watch --strict` 통과
- 운영 기준: 문서/검증 범위 100% 판정은 DR Open 0건과 함께 위 통제가 정상 동작해야 유지된다.

---

## Definition of Done (MVP)

### 기능

- E2E 업로드 -> 번역 -> 다운로드 동작
- 상태 모델/과금 규칙 UI/API/DB 일치
- 취소/재시도/편집 제약 규칙 준수
- 신고/권한/오류 코드 정책 검증

### 품질

- 성공률 90% 이상
- 사용 가능률 95% 이상
- 타임아웃/재시도 정책 검증

### 운영

- 환경 분리(dev/staging/prod)
- 로그/알림/비용 통제 동작
- 배포 및 기본 사용자 가이드 준비
- OSS 컴플라이언스 최소 게이트 통과(`LICENSE`, `NOTICE`, `SBOM 2종`, 매니페스트/락파일)
- 컴플라이언스 문서 경로 확정(`docs/compliance/*`) 및 검증 명령 통과

---

> 문서 버전: 현재
> 최종 업데이트: 2026-02-07
