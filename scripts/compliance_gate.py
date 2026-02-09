#!/usr/bin/env python3
"""
문서/검증 범위 컴플라이언스 게이트.

실패 시 즉시 non-zero를 반환해 CI를 차단한다.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
PLANS_SYNC = REPO_ROOT / "scripts" / "plans_sync.py"

REQUIRED_FILES = [
    "LICENSE",
    "NOTICE",
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "requirements-dev.txt",
    "docs/compliance/OSS_LICENSE_POLICY.md",
    "docs/compliance/DEPENDENCY_VERSION_MATRIX.md",
    "docs/compliance/THIRD_PARTY_NOTICES.md",
    "docs/compliance/SBOM.spdx.json",
    "docs/compliance/SBOM.cyclonedx.json",
    "docs/compliance/external_sdk_watchlist.json",
    "docs/compliance/external_sdk_snapshot.json",
    ".github/workflows/compliance-gate.yml",
    ".github/workflows/external-sdk-watch.yml",
]

JSON_REQUIRED_FILES = [
    "package.json",
    "package-lock.json",
    "docs/compliance/SBOM.spdx.json",
    "docs/compliance/SBOM.cyclonedx.json",
    "docs/compliance/external_sdk_watchlist.json",
    "docs/compliance/external_sdk_snapshot.json",
]

LICENSE_POLICY_KEYWORDS = ["GPL", "AGPL", "SSPL", "금지"]
REQUIRED_FINAL_PHRASE = "100% 가능(문서/검증 범위, 2026-02-09 기준)"
DR_OPEN_PATTERN = re.compile(r"\|\s*DR-\d+\s*\|.*\|\s*Open\s*\|")


def run_cmd(command: list[str]) -> tuple[int, str]:
    """명령을 실행하고 표준출력/표준에러를 합쳐 반환한다."""
    process = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (process.stdout or "") + (process.stderr or "")
    return process.returncode, output.strip()


def check_paths(paths: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for relative_path in paths:
        if not (REPO_ROOT / relative_path).exists():
            missing.append(relative_path)
    return missing


def check_json_parse(paths: Iterable[str]) -> list[str]:
    broken: list[str] = []
    for relative_path in paths:
        target = REPO_ROOT / relative_path
        try:
            with target.open("r", encoding="utf-8-sig") as file:
                json.load(file)
        except Exception:
            broken.append(relative_path)
    return broken


def check_license_policy_keywords() -> list[str]:
    policy_path = REPO_ROOT / "docs/compliance/OSS_LICENSE_POLICY.md"
    content = policy_path.read_text(encoding="utf-8")
    missing_keywords = [keyword for keyword in LICENSE_POLICY_KEYWORDS if keyword not in content]
    return missing_keywords


def check_dr_open_rows() -> list[str]:
    review_path = REPO_ROOT / "docs/specs/OSS_COMPLIANCE_REVIEW_2026-02-09.md"
    content = review_path.read_text(encoding="utf-8")
    return [line for line in content.splitlines() if DR_OPEN_PATTERN.search(line)]


def check_required_phrase() -> bool:
    review_path = REPO_ROOT / "docs/specs/OSS_COMPLIANCE_REVIEW_2026-02-09.md"
    content = review_path.read_text(encoding="utf-8")
    return REQUIRED_FINAL_PHRASE in content


def check_dr07_closed_proof() -> bool:
    risk_path = REPO_ROOT / "docs/specs/OSS_EXTERNAL_DEPENDENCY_RISK_REGISTER.md"
    content = risk_path.read_text(encoding="utf-8")
    return all(token in content for token in ["DR-07", "Closed", "자동 감시"])


def main() -> int:
    errors: list[str] = []

    missing_paths = check_paths(REQUIRED_FILES)
    if missing_paths:
        errors.append("필수 파일 누락: " + ", ".join(missing_paths))

    broken_json = check_json_parse(JSON_REQUIRED_FILES)
    if broken_json:
        errors.append("JSON 파싱 실패: " + ", ".join(broken_json))

    missing_policy_keywords = check_license_policy_keywords()
    if missing_policy_keywords:
        errors.append(
            "라이선스 정책 키워드 누락: " + ", ".join(missing_policy_keywords)
        )

    dr_open_rows = check_dr_open_rows()
    if dr_open_rows:
        errors.append("DR 상태표에 Open 항목이 남아 있음: " + " | ".join(dr_open_rows))

    if not check_required_phrase():
        errors.append(f"최종 판정 문구 누락: {REQUIRED_FINAL_PHRASE}")

    if not check_dr07_closed_proof():
        errors.append("DR-07 Closed 근거(자동 감시) 문구가 리스크 레지스터에 없음")

    validate_code, validate_output = run_cmd(
        [sys.executable, str(PLANS_SYNC), "validate", "--input", "Plans.json"]
    )
    if validate_code != 0:
        errors.append("plans_sync validate 실패: " + validate_output)

    check_code, check_output = run_cmd(
        [
            sys.executable,
            str(PLANS_SYNC),
            "check",
            "--input",
            "Plans.json",
            "--output",
            "Plans.md",
        ]
    )
    if check_code != 0:
        errors.append("plans_sync check 실패: " + check_output)

    if errors:
        print("[FAIL] compliance_gate 실패", file=sys.stderr)
        for message in errors:
            print(f"- {message}", file=sys.stderr)
        return 1

    print("[OK] compliance_gate 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
