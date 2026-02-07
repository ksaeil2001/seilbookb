# seilbookb

## Plans 문서 운영 규칙

`Plans` 문서는 JSON 원본 + Markdown 파생 형태로 운영합니다.

- 원본(SSOT): `Plans.json`
- 파생(리뷰용): `Plans.md`
- 원칙: `Plans.md`는 수동 편집하지 않고 `Plans.json`에서 자동 생성
- 문서 성격: **MVP 6주 미래 구현 로드맵**
- 테스트 명령 정책: **예시 중심(`example_only`)**, 구현 단계에서 구체화

### 로컬 작업 순서

1. `Plans.json` 수정
2. `python scripts/plans_sync.py validate --input Plans.json`
3. `python scripts/plans_sync.py render --input Plans.json --output Plans.md`
4. `python scripts/plans_sync.py check --input Plans.json --output Plans.md`

### CI 검증

PR/Push에서 아래가 자동 실행됩니다.

- `validate`: 스키마/필수 키/로드맵 메타데이터/체크리스트 단계(RED/GREEN/REFACTOR) 검증
- `check`: `Plans.json`과 `Plans.md` 동기화 상태 검증

동기화가 맞지 않으면 CI는 다음 메시지와 함께 실패합니다.

- `Plans.json 수정 후 render 미실행`

### 로드맵 해석 가이드

- `Plans.md`의 테스트 명령은 즉시 실행 강제가 아니라 구현 단계 참고용 예시다.
- 각 Phase는 `목표 기간`, `의존성`, `리스크`, `완료 신호(게이트)`를 기준으로 우선순위를 조정한다.
- 각 Phase는 `품질 게이트(차단형)`를 통과하기 전까지 다음 Phase로 진행하지 않는다.
- `6_Risk_Assessment`는 단계별 리스크를 통합한 요약본이며, `3_Progress[*].risks`와 함께 관리한다.
- `7_Rollback_Strategy`는 Phase 실패 시 되돌릴 기준 상태와 절차를 정의한다.
- `8_Progress_Tracking`은 진행률/시간/블로커를 추적하는 운영 섹션이다.
