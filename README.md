# seilbookb

## Plans 문서 운영 규칙

`Plans` 문서는 JSON 원본 + Markdown 파생 형태로 운영한다.

- 원본(SSOT): `Plans.json`
- 파생(리뷰용): `Plans.md`
- 원칙: `Plans.md`는 수동 편집하지 않고 `Plans.json`에서 자동 생성
- 문서 성격: **MVP 6주 미래 구현 로드맵**
- 테스트 명령 정책: **예시 중심(`example_only`)**, 구현 단계에서 구체화

## 문서 경로 맵

- 핵심 운영 문서(루트 유지)
  - `AGENTS.md`
  - `README.md`
  - `Plans.json`
  - `Plans.md`
  - `.markdownlint.json`
  - `LICENSE`
  - `NOTICE`
- 사양 문서(`docs/specs`)
  - `docs/specs/PRD.md`
  - `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md`
  - `docs/specs/OSS_COMPLIANCE_REVIEW_2026-02-09.md`
- 컴플라이언스 문서(`docs/compliance`)
  - `docs/compliance/OSS_LICENSE_POLICY.md`
  - `docs/compliance/DEPENDENCY_VERSION_MATRIX.md`
  - `docs/compliance/THIRD_PARTY_NOTICES.md`
  - `docs/compliance/SBOM.spdx.json`
  - `docs/compliance/SBOM.cyclonedx.json`

### 로컬 작업 순서

1. `Plans.json` 수정
2. `python scripts/plans_sync.py validate --input Plans.json`
3. `python scripts/plans_sync.py render --input Plans.json --output Plans.md`
4. `python scripts/plans_sync.py check --input Plans.json --output Plans.md`
5. 리스크 대응 문서(`AGENTS.md`, `docs/specs/PRD.md`, `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md`) 변경 시 위 2~4 검증을 필수로 재실행
6. 컴플라이언스 문서 변경 시 증빙 존재성 검증 실행
7. 매니페스트 고정 버전과 라이선스 고지를 갱신한 뒤 SBOM 2종을 동기화
8. `python scripts/compliance_gate.py` 실행으로 문서/증빙/판정 조건 일괄 검증
9. `python scripts/sdk_policy_watch.py --watchlist docs/compliance/external_sdk_watchlist.json --snapshot docs/compliance/external_sdk_snapshot.json --strict` 실행으로 DR-07 정책 드리프트 검증

### 컴플라이언스 검증

1. `powershell -Command "Test-Path LICENSE; Test-Path NOTICE; Test-Path package.json; Test-Path package-lock.json; Test-Path requirements.txt; Test-Path requirements-dev.txt; Test-Path docs/compliance/OSS_LICENSE_POLICY.md; Test-Path docs/compliance/DEPENDENCY_VERSION_MATRIX.md; Test-Path docs/compliance/THIRD_PARTY_NOTICES.md; Test-Path docs/compliance/SBOM.spdx.json; Test-Path docs/compliance/SBOM.cyclonedx.json"`
2. `rg -n "MIT|Apache-2.0|LGPL|BSD-3-Clause" docs/compliance/DEPENDENCY_VERSION_MATRIX.md docs/compliance/THIRD_PARTY_NOTICES.md`
3. `rg -n "Idempotency-Key|fail-closed|fallback_rate" AGENTS.md docs/specs/PRD.md Plans.md`
4. `python scripts/compliance_gate.py`
5. `python scripts/sdk_policy_watch.py --watchlist docs/compliance/external_sdk_watchlist.json --snapshot docs/compliance/external_sdk_snapshot.json --strict`

### CI 검증

PR/Push에서 아래가 자동 실행된다.

- `validate`: 스키마/필수 키/로드맵 메타데이터/체크리스트 단계(RED/GREEN/REFACTOR) 검증
- `validate`: 문서 손상 패턴(`??`, `???`) 포함 여부 검증
- `check`: `Plans.json`과 `Plans.md` 동기화 상태 검증
- `compliance-gate`: 문서/증빙/DR 상태(Open 0건) 검증
- `external-sdk-watch`: 외부 SDK 정책 문서 해시 감시(일 1회 + 수동 실행)

동기화가 맞지 않으면 CI는 다음 메시지와 함께 실패한다.

- `Plans.json 수정 후 render 미실행`
- `compliance_gate 실패`
- `External SDK policy drift detected`

### 로드맵 해석 가이드

- `Plans.md`의 테스트 명령은 즉시 실행 강제가 아니라 구현 단계 참고용 예시다.
- 각 Phase는 `목표 기간`, `의존성`, `리스크`, `완료 신호(게이트)`를 기준으로 우선순위를 조정한다.
- 각 Phase는 `품질 게이트(차단형)`를 통과하기 전까지 다음 Phase로 진행하지 않는다.
- `6_Risk_Assessment`는 단계별 리스크를 통합한 요약본이며, `3_Progress[*].risks`와 함께 관리한다.
- `7_Rollback_Strategy`는 Phase 실패 시 되돌릴 기준 상태와 절차를 정의한다.
- `8_Progress_Tracking`은 진행률/시간/블로커를 추적하는 운영 섹션이다.
