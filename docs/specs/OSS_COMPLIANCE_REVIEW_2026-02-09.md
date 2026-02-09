# 오픈소스 사용 전수 진단 리포트 (기술+라이선스)

- 작성일: 2026-02-09
- 검토 범위: `AGENTS.md`, `README.md`, `Plans.json`, `Plans.md`, `docs/specs/PRD.md`, `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md`, `docs/compliance/*`
- 판정 기준: 기술/운영 리스크 + 라이선스 컴플라이언스

## 1) 판정 요약

현재 문서/검증 기준에서 **오픈소스 사용 문제 없음 100% 가능(문서/검증 범위, 2026-02-09 기준)** 판정으로 전환한다.

통과 근거:

1. 차단 이슈였던 라이선스/증빙 부재를 해소했다.
2. 리스크 레지스터 3차를 컴플라이언스 전용 Top 8로 재편해 단계 중복을 제거했다.
3. 검증 규칙을 실제 `app_code` 표준과 일치시켰다.

## 2) DR 상태 추적

| DR ID | 항목 | 이전 상태 | 현재 상태 | 상태 | 근거 파일 | 검증 명령 |
| --- | --- | --- | --- | --- | --- | --- |
| DR-01 | 의존성 재현성(매니페스트/락) | 차단 | 해소 | Closed | `package.json`, `package-lock.json`, `requirements.txt`, `requirements-dev.txt` | `Test-Path package.json`, `Test-Path package-lock.json` |
| DR-02 | 라이선스 컴플라이언스 증빙 부재 | 차단 | 해소 | Closed | `LICENSE`, `NOTICE`, `docs/compliance/OSS_LICENSE_POLICY.md`, `docs/compliance/THIRD_PARTY_NOTICES.md` | `Test-Path LICENSE`, `Test-Path NOTICE` |
| DR-03 | 리스크 상태표 중복 | high | 해소 | Closed | `docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` | `rg -n "## 10\\) 3차 Top 8 즉시 대응 실행 상태" docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` |
| DR-04 | SSOT 참조 무결성 | high | 해소 | Closed | `AGENTS.md`, `README.md`, `Plans.json`, `Plans.md` | `rg -n "OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER" AGENTS.md README.md Plans.md` |
| DR-05 | app_code 검증 규칙 불일치 | high | 해소 | Closed | `Plans.json`, `Plans.md` | `rg -n "TOSS_\\(" Plans.json Plans.md` (결과 0건) |
| DR-06 | Top 우선순위 검증 범위 부족 | medium | 해소 | Closed | `AGENTS.md`, `Plans.json`, `Plans.md` | `rg -n "C-01|C-02|C-03|C-04|C-05|C-06|C-07|C-08" AGENTS.md Plans.md docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md` |
| DR-07 | 외부 SDK 정책 변화 리스크 | medium | 해소 | Closed | `docs/compliance/external_sdk_watchlist.json`, `docs/compliance/external_sdk_snapshot.json`, `.github/workflows/external-sdk-watch.yml` | `python scripts/sdk_policy_watch.py --watchlist docs/compliance/external_sdk_watchlist.json --snapshot docs/compliance/external_sdk_snapshot.json --strict` |
| DR-08 | 문서 책임 분리 부족 | medium | 해소 | Closed | `README.md`, `AGENTS.md`, `docs/compliance/*` | `rg -n "컴플라이언스" README.md AGENTS.md` |

## 3) 정합성 점검 결과

| 키워드 | AGENTS | PRD | Plans | 판정 |
| --- | --- | --- | --- | --- |
| `Idempotency-Key` | 존재 | 존재 | 존재 | 일치 |
| `fail-closed` | 존재 | 존재 | 존재 | 일치 |
| `fallback_rate` | 존재 | 존재 | 존재 | 일치 |
| 핵심 `app_code` | 존재 | 존재 | 존재 | 일치 |
| 컴플라이언스 게이트 | 존재 | 존재 | 존재 | 일치 |

## 4) 컴플라이언스 증빙 경로

- 라이선스: `LICENSE`
- 고지: `NOTICE`
- 정책: `docs/compliance/OSS_LICENSE_POLICY.md`
- 버전 고정표: `docs/compliance/DEPENDENCY_VERSION_MATRIX.md`
- Third-party 고지: `docs/compliance/THIRD_PARTY_NOTICES.md`
- SBOM: `docs/compliance/SBOM.spdx.json`, `docs/compliance/SBOM.cyclonedx.json`

## 5) 잔여 오픈 이슈

- 현재 DR 상태표 기준 Open 항목은 없다(Open 0건).
- 후속 개선 과제는 운영 고도화 항목으로 관리하며 판정 차단 이슈에는 포함하지 않는다.

## 6) 최종 판정

아래 조건을 충족해 `오픈소스 사용 문제 없음 100% 가능(문서/검증 범위, 2026-02-09 기준)`으로 판정한다.

1. 차단 이슈 0건
2. 고위험 미완료 0건
3. 컴플라이언스 증빙 경로 확정
4. SSOT 문서 정합성 검증 가능
