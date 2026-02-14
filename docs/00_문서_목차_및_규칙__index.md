Owner: Product & Platform
Status: Draft
Version: v0.1
Last Updated: 2026-02-13
Related ADR: adr-0001
Related Tickets: N/A

# 00_문서_목차_및_규칙__index

## 문서 단일 진입점
- 본 저장소의 문서 Canonical 경로는 `docs/*`다.
- 루트 문서(`README.md`, `PRD.md`, `OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md`, `OSS_COMPLIANCE_REVIEW.md`)는 안내문만 유지한다.

## 문서 목차
- [01 요구사항 명세서](./01_요구사항_명세서__prdsrs.md)
- [02 기술 설계서](./02_기술_설계서__architecture-key-design.md)
- [03 일정 계획표](./03_일정_계획표__release-plan.md)
- [04 위험 분석 보고서](./04_위험_분석_보고서__risk-register.md)
- [05 API-인터페이스 계약서](./05_API-인터페이스_계약서__openapi.yaml)
- [06 보안-개인정보 설계](./06_보안-개인정보_설계__threat-model-data-map.md)
- [07 테스트-품질 계획](./07_테스트-품질_계획__quality-plan.md)
- [08 OSS 외부의존 리스크 레지스터](./08_OSS_외부의존_리스크_레지스터__oss-external-dependency-risk-register.md)
- [09 OSS 컴플라이언스 리뷰](./09_OSS_컴플라이언스_리뷰__oss-compliance-review.md)
- [ADR-0001 결정 기록](./adr/adr-0001_결정_기록__adr.md)
- [컴플라이언스 정책/증빙](./compliance)

## 문서 규칙
- RFC 2119 해석 규칙을 적용한다.
- `MUST`: 반드시 충족해야 하는 차단형 요구.
- `SHOULD`: 강하게 권고되는 요구.
- `MAY`: 선택 가능 요구.
- 코드 변경 시 다음 문서를 동기화한다.
- OpenAPI 계약(`docs/05_API-인터페이스_계약서__openapi.yaml`)
- Data Map/AuthZ(`docs/06_보안-개인정보_설계__threat-model-data-map.md`)
- 운영/배포 규칙(`docs/03_일정_계획표__release-plan.md`, `docs/04_위험_분석_보고서__risk-register.md`)
- 모든 문서는 상단 메타데이터 필드를 유지한다.
- external_sdk_snapshot strict 실패는 drift 감지로 처리한다.
- report 확인 후 update를 수행한다.
- strict 재검증 통과 + snapshot-only 커밋으로 마감한다.

## 용어집
- Hard Gate: `input_text_count == output_text_count`, `bbox_overflow == 0`, `min_font_pt >= 10`를 동시에 만족해야 통과하는 차단형 품질 게이트.
- Soft Gate: 샘플링 기반 품질 평가 게이트.
- User Gate: 코호트 사용자 지표 기반 제품 게이트.
- SSOT: 단일 진실 원본(Single Source of Truth).
- fail-closed: 조건 불충족 시 보수적으로 차단하는 운영 정책.
- app_code: 프론트/백엔드 오류 계약의 표준 코드.
- Idempotency-Key: 쓰기 API 중복 처리 방지를 위한 멱등 키.
