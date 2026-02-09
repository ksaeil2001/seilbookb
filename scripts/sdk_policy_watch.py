#!/usr/bin/env python3
"""
외부 SDK/공식 문서 정책 변화 감시 스크립트.

동작:
1) watchlist URL을 수집
2) 본문 텍스트를 정규화해 SHA-256 해시 계산
3) snapshot과 비교해 변경 감지
4) strict 모드에서 변경/오류 시 non-zero 반환
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/compliance/external_sdk_watch_report.json"


class _VisibleTextExtractor(HTMLParser):
    """HTML에서 화면 텍스트만 추출한다."""

    def __init__(self) -> None:
        super().__init__()
        self._skip_stack: list[str] = []
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()

    def handle_data(self, data: str) -> None:
        if not self._skip_stack:
            self._chunks.append(data)

    def get_text(self) -> str:
        return " ".join(self._chunks)


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError(f"JSON 루트는 object여야 합니다: {path}")
    return loaded


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _extract_text(raw_bytes: bytes, content_type: str | None) -> str:
    charset = "utf-8"
    if content_type:
        match = re.search(r"charset=([\\w\\-]+)", content_type, flags=re.IGNORECASE)
        if match:
            charset = match.group(1)

    decoded = raw_bytes.decode(charset, errors="replace")
    normalized_type = (content_type or "").lower()
    if "html" in normalized_type:
        parser = _VisibleTextExtractor()
        parser.feed(decoded)
        return parser.get_text()
    return decoded


def _normalize_text(text: str) -> str:
    unescaped = html.unescape(text)
    collapsed = re.sub(r"\\s+", " ", unescaped).strip()
    return collapsed


def _fetch_and_hash(url: str, timeout: int, user_agent: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        content_type = response.headers.get("Content-Type")
        status_code = getattr(response, "status", 200)
        body = response.read()
        text = _extract_text(body, content_type)
        normalized = _normalize_text(text)
        if not normalized:
            # 본문이 비어 있으면 바이트 해시로 대체한다.
            normalized = body.hex()
        hashed = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return {
            "status_code": status_code,
            "content_type": content_type,
            "hash": hashed,
            "text_length": len(normalized),
            "fetched_at": _now_iso(),
        }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="외부 SDK 정책 변화 감시")
    parser.add_argument("--watchlist", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--user-agent", default="claude-code-mastery-sdk-watch/1.0")
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    watchlist_path = (REPO_ROOT / args.watchlist).resolve() if not args.watchlist.is_absolute() else args.watchlist
    snapshot_path = (REPO_ROOT / args.snapshot).resolve() if not args.snapshot.is_absolute() else args.snapshot
    report_path = (REPO_ROOT / args.report).resolve() if not args.report.is_absolute() else args.report

    watchlist = _load_json(watchlist_path)
    items = watchlist.get("items", [])
    if not isinstance(items, list) or not items:
        print("[FAIL] watchlist.items가 비어 있습니다.", file=sys.stderr)
        return 1

    current_items: list[dict[str, Any]] = []
    fetch_errors: list[dict[str, str]] = []
    for item in items:
        item_id = str(item.get("id", "")).strip()
        url = str(item.get("url", "")).strip()
        if not item_id or not url:
            fetch_errors.append({"id": item_id or "(missing-id)", "error": "id/url 누락"})
            continue
        try:
            fetched = _fetch_and_hash(url, args.timeout, args.user_agent)
            current_items.append(
                {
                    "id": item_id,
                    "name": item.get("name", ""),
                    "url": url,
                    "domain": urlparse(url).netloc,
                    **fetched,
                }
            )
        except HTTPError as error:
            fetch_errors.append({"id": item_id, "error": f"HTTP {error.code}"})
        except URLError as error:
            fetch_errors.append({"id": item_id, "error": f"URL 오류: {error.reason}"})
        except Exception as error:  # noqa: BLE001
            fetch_errors.append({"id": item_id, "error": str(error)})

    baseline: dict[str, Any] = {}
    if snapshot_path.exists():
        baseline = _load_json(snapshot_path)
    baseline_items = baseline.get("items", []) if isinstance(baseline, dict) else []
    baseline_map = {
        str(entry.get("id")): entry
        for entry in baseline_items
        if isinstance(entry, dict) and entry.get("id")
    }
    current_map = {entry["id"]: entry for entry in current_items}

    changed: list[dict[str, Any]] = []
    for item_id, current in current_map.items():
        previous = baseline_map.get(item_id)
        if not previous:
            changed.append(
                {
                    "id": item_id,
                    "change_type": "added",
                    "old_hash": None,
                    "new_hash": current["hash"],
                    "url": current["url"],
                }
            )
            continue
        if previous.get("hash") != current.get("hash"):
            changed.append(
                {
                    "id": item_id,
                    "change_type": "modified",
                    "old_hash": previous.get("hash"),
                    "new_hash": current.get("hash"),
                    "url": current["url"],
                }
            )

    removed_ids = [item_id for item_id in baseline_map if item_id not in current_map]
    for removed_id in removed_ids:
        previous = baseline_map[removed_id]
        changed.append(
            {
                "id": removed_id,
                "change_type": "removed",
                "old_hash": previous.get("hash"),
                "new_hash": None,
                "url": previous.get("url"),
            }
        )

    snapshot_payload = {
        "watchlist_version": watchlist.get("version"),
        "verified_at": _now_iso(),
        "items": current_items,
    }
    report_payload = {
        "executed_at": _now_iso(),
        "strict": bool(args.strict),
        "update_mode": bool(args.update),
        "watchlist_path": str(watchlist_path.relative_to(REPO_ROOT)),
        "snapshot_path": str(snapshot_path.relative_to(REPO_ROOT)),
        "total_items": len(items),
        "fetched_items": len(current_items),
        "changed_items": changed,
        "fetch_errors": fetch_errors,
        "removed_ids": removed_ids,
    }
    _write_json(report_path, report_payload)

    if args.update:
        if fetch_errors:
            print("[FAIL] update 모드에서 fetch 오류가 있어 snapshot을 갱신하지 않습니다.", file=sys.stderr)
            for fetch_error in fetch_errors:
                print(f"- {fetch_error['id']}: {fetch_error['error']}", file=sys.stderr)
            return 1
        _write_json(snapshot_path, snapshot_payload)
        print(f"[OK] snapshot 갱신 완료: {snapshot_path}")
        return 0

    # update 모드가 아닐 때는 baseline 비교만 수행한다.
    if not snapshot_path.exists():
        print("[FAIL] snapshot 파일이 없습니다. --update로 초기화하세요.", file=sys.stderr)
        return 1

    if changed:
        print("[WARN] 정책 변화 감지")
        for item in changed:
            print(f"- {item['id']}: {item['change_type']}")

    if fetch_errors:
        print("[WARN] fetch 오류 감지")
        for fetch_error in fetch_errors:
            print(f"- {fetch_error['id']}: {fetch_error['error']}")

    if args.strict and (changed or fetch_errors):
        print("[FAIL] strict 모드 실패: 변화 또는 오류가 감지되었습니다.", file=sys.stderr)
        return 1

    print("[OK] sdk_policy_watch 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
