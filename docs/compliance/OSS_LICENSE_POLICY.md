# OSS 라이선스 운영 정책

- 문서 버전: 2026-02-09
- 적용 범위: `AGENTS.md`, `Plans.json`, `Plans.md`, `README.md`, `docs/specs/PRD.md`에 명시된 OSS 및 외부의존
- 프로젝트 라이선스: `MIT`

## 1. 최소 게이트(차단형)

아래 항목이 모두 존재하지 않으면 배포를 차단한다.

1. 매니페스트/락파일: `package.json`, `package-lock.json`, `requirements.txt`, `requirements-dev.txt`
2. 라이선스 고지: `LICENSE`, `NOTICE`, `docs/compliance/THIRD_PARTY_NOTICES.md`
3. SBOM 산출물: `docs/compliance/SBOM.spdx.json`, `docs/compliance/SBOM.cyclonedx.json`
4. 버전 고정표: `docs/compliance/DEPENDENCY_VERSION_MATRIX.md`

## 2. 라이선스 분류 정책

- 허용(기본): `MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`, `ISC`
- 조건부 허용: `LGPL-*` (서버사이드 사용, 동적 링크, 소스 수정 없음, 고지 유지)
- 금지(사전 승인 없이는 불가): `GPL-*`, `AGPL-*`, `SSPL`, 출처 불명 라이선스

## 3. 의무 이행 규칙

1. 신규 의존성 추가 시 `DEPENDENCY_VERSION_MATRIX.md`와 `THIRD_PARTY_NOTICES.md`를 같이 수정한다.
2. 배포 전 SBOM 2종을 갱신한다.
3. 라이선스 식별 불가 항목은 `잠정` 상태로 분류하고 릴리즈 전 `확정`으로 전환한다.

## 4. 검증 명령(운영 표준)

```bash
python scripts/plans_sync.py validate --input Plans.json
python scripts/plans_sync.py render --input Plans.json --output Plans.md
python scripts/plans_sync.py check --input Plans.json --output Plans.md
rg -n "MIT|Apache-2.0|LGPL" docs/compliance/DEPENDENCY_VERSION_MATRIX.md docs/compliance/THIRD_PARTY_NOTICES.md
```
