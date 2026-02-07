#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_TOP_LEVEL = [
    ("1_Purpose", dict),
    ("2_Testing_Strategy", dict),
    ("3_Progress", list),
    ("4_Decision_Log", list),
    ("5_Validation", list),
    ("6_Risk_Assessment", list),
    ("7_Rollback_Strategy", dict),
    ("8_Progress_Tracking", dict),
]
EXPECTED_CHECKLIST_STEPS = ["RED", "GREEN", "REFACTOR"]
PHASE_STATUS_VALUES = {"pending", "in_progress", "complete"}
RISK_LEVEL_VALUES = {"low", "medium", "high"}
REQUIRED_DOCUMENT_MODE = "future_implementation_roadmap"
REQUIRED_COMMAND_POLICY = "example_only"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _validate_item_done_list(value: Any, prefix: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{prefix}는 array여야 합니다.")
        return
    for index, item in enumerate(value):
        item_prefix = f"{prefix}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix}는 object여야 합니다.")
            continue
        if not isinstance(item.get("item"), str):
            errors.append(f"{item_prefix}.item은 string이어야 합니다.")
        if not isinstance(item.get("done"), bool):
            errors.append(f"{item_prefix}.done은 boolean이어야 합니다.")


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON 파싱 실패: {error}") from error
    except FileNotFoundError as error:
        raise ValueError(f"입력 파일이 없습니다: {path}") from error


def _validate_schema(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["루트 객체는 JSON object여야 합니다."]

    expected_keys = [item[0] for item in EXPECTED_TOP_LEVEL]
    actual_keys = list(data.keys())
    if actual_keys != expected_keys:
        errors.append(
            "Top-level 키/순서가 올바르지 않습니다. "
            f"기대: {expected_keys}, 실제: {actual_keys}"
        )

    for key, expected_type in EXPECTED_TOP_LEVEL:
        value = data.get(key)
        if not isinstance(value, expected_type):
            errors.append(f"`{key}` 타입 오류: {expected_type.__name__} 이어야 합니다.")

    purpose = data.get("1_Purpose", {})
    if isinstance(purpose, dict):
        if not isinstance(purpose.get("main_objective"), str):
            errors.append("`1_Purpose.main_objective`는 string이어야 합니다.")
        if not isinstance(purpose.get("hard_gate_definition"), str):
            errors.append("`1_Purpose.hard_gate_definition`는 string이어야 합니다.")
        if not isinstance(purpose.get("tdd_execution_principle"), str):
            errors.append("`1_Purpose.tdd_execution_principle`는 string이어야 합니다.")
        document_mode = purpose.get("document_mode")
        if not isinstance(document_mode, str):
            errors.append("`1_Purpose.document_mode`는 string이어야 합니다.")
        elif document_mode != REQUIRED_DOCUMENT_MODE:
            errors.append(
                "`1_Purpose.document_mode` 값 오류: "
                f"`{REQUIRED_DOCUMENT_MODE}` 이어야 합니다."
            )
        horizon_weeks = purpose.get("horizon_weeks")
        if not isinstance(horizon_weeks, int) or horizon_weeks <= 0:
            errors.append("`1_Purpose.horizon_weeks`는 0보다 큰 int여야 합니다.")

    testing = data.get("2_Testing_Strategy", {})
    if isinstance(testing, dict):
        if "frameworks" in testing and not isinstance(testing["frameworks"], dict):
            errors.append("`2_Testing_Strategy.frameworks`는 object여야 합니다.")
        if "principles" in testing and not _is_string_list(testing["principles"]):
            errors.append("`2_Testing_Strategy.principles`는 string array여야 합니다.")
        if "test_commands" in testing and not _is_string_list(testing["test_commands"]):
            errors.append("`2_Testing_Strategy.test_commands`는 string array여야 합니다.")
        if "temporary_assumptions" in testing and not _is_string_list(testing["temporary_assumptions"]):
            errors.append("`2_Testing_Strategy.temporary_assumptions`는 string array여야 합니다.")
        command_policy = testing.get("command_policy")
        if not isinstance(command_policy, str):
            errors.append("`2_Testing_Strategy.command_policy`는 string이어야 합니다.")
        elif command_policy != REQUIRED_COMMAND_POLICY:
            errors.append(
                "`2_Testing_Strategy.command_policy` 값 오류: "
                f"`{REQUIRED_COMMAND_POLICY}` 이어야 합니다."
            )

    phase_ids: set[int] = set()
    progress = data.get("3_Progress", [])
    if isinstance(progress, list):
        for index, phase in enumerate(progress):
            prefix = f"`3_Progress[{index}]`"
            if not isinstance(phase, dict):
                errors.append(f"{prefix}는 object여야 합니다.")
                continue

            phase_id = phase.get("phase_id")
            if not isinstance(phase_id, int):
                errors.append(f"{prefix}.phase_id는 int여야 합니다.")
            elif phase_id in phase_ids:
                errors.append(f"{prefix}.phase_id 중복: {phase_id}")
            else:
                phase_ids.add(phase_id)

            if not isinstance(phase.get("feature"), str):
                errors.append(f"{prefix}.feature는 string이어야 합니다.")
            if not isinstance(phase.get("details"), str):
                errors.append(f"{prefix}.details는 string이어야 합니다.")
            if not isinstance(phase.get("target_window"), str):
                errors.append(f"{prefix}.target_window는 string이어야 합니다.")
            if not _is_string_list(phase.get("dependencies")):
                errors.append(f"{prefix}.dependencies는 string array여야 합니다.")
            if not _is_string_list(phase.get("risks")):
                errors.append(f"{prefix}.risks는 string array여야 합니다.")
            if not isinstance(phase.get("exit_signal"), str):
                errors.append(f"{prefix}.exit_signal는 string이어야 합니다.")

            estimated_hours = phase.get("estimated_hours")
            if not _is_number(estimated_hours):
                errors.append(f"{prefix}.estimated_hours는 number여야 합니다.")
            elif estimated_hours <= 0:
                errors.append(f"{prefix}.estimated_hours는 0보다 커야 합니다.")

            status = phase.get("status")
            if not isinstance(status, str):
                errors.append(f"{prefix}.status는 string이어야 합니다.")
            elif status not in PHASE_STATUS_VALUES:
                errors.append(
                    f"{prefix}.status 값 오류: {PHASE_STATUS_VALUES} 중 하나여야 합니다."
                )

            if not _is_string_list(phase.get("acceptance_criteria_mapping")):
                errors.append(f"{prefix}.acceptance_criteria_mapping는 string array여야 합니다.")
            if not _is_string_list(phase.get("edge_case_coverage")):
                errors.append(f"{prefix}.edge_case_coverage는 string array여야 합니다.")
            if not _is_string_list(phase.get("test_commands")):
                errors.append(f"{prefix}.test_commands는 string array여야 합니다.")
            if not _is_string_list(phase.get("result_examples")):
                errors.append(f"{prefix}.result_examples는 string array여야 합니다.")
            if "notes" in phase and not _is_string_list(phase.get("notes")):
                errors.append(f"{prefix}.notes는 string array여야 합니다.")

            checklist = phase.get("checklist")
            if not isinstance(checklist, list):
                errors.append(f"{prefix}.checklist는 array여야 합니다.")
            else:
                if len(checklist) != 3:
                    errors.append(f"{prefix}.checklist 길이는 3이어야 합니다.")
                steps: list[str] = []
                for item_index, item in enumerate(checklist):
                    item_prefix = f"{prefix}.checklist[{item_index}]"
                    if not isinstance(item, dict):
                        errors.append(f"{item_prefix}는 object여야 합니다.")
                        continue
                    step_value = item.get("step")
                    if not isinstance(step_value, str):
                        errors.append(f"{item_prefix}.step은 string이어야 합니다.")
                    else:
                        steps.append(step_value)
                    if not isinstance(item.get("desc"), str):
                        errors.append(f"{item_prefix}.desc는 string이어야 합니다.")
                    if not isinstance(item.get("done"), bool):
                        errors.append(f"{item_prefix}.done은 boolean이어야 합니다.")
                if steps and steps != EXPECTED_CHECKLIST_STEPS:
                    errors.append(
                        f"{prefix}.checklist.step 순서 오류: "
                        f"기대 {EXPECTED_CHECKLIST_STEPS}, 실제 {steps}"
                    )

            gate = phase.get("quality_gate")
            gate_prefix = f"{prefix}.quality_gate"
            if not isinstance(gate, dict):
                errors.append(f"{gate_prefix}는 object여야 합니다.")
            else:
                if gate.get("blocking") is not True:
                    errors.append(f"{gate_prefix}.blocking은 true여야 합니다.")
                if not isinstance(gate.get("stop_message"), str):
                    errors.append(f"{gate_prefix}.stop_message는 string이어야 합니다.")
                _validate_item_done_list(gate.get("tdd_compliance"), f"{gate_prefix}.tdd_compliance", errors)
                _validate_item_done_list(gate.get("build_and_tests"), f"{gate_prefix}.build_and_tests", errors)
                _validate_item_done_list(gate.get("code_quality"), f"{gate_prefix}.code_quality", errors)
                _validate_item_done_list(
                    gate.get("security_and_performance"),
                    f"{gate_prefix}.security_and_performance",
                    errors,
                )
                _validate_item_done_list(gate.get("documentation"), f"{gate_prefix}.documentation", errors)
                _validate_item_done_list(gate.get("manual_testing"), f"{gate_prefix}.manual_testing", errors)
                if not _is_string_list(gate.get("validation_commands")):
                    errors.append(f"{gate_prefix}.validation_commands는 string array여야 합니다.")

    decision_log = data.get("4_Decision_Log", [])
    if isinstance(decision_log, list):
        for index, item in enumerate(decision_log):
            prefix = f"`4_Decision_Log[{index}]`"
            if not isinstance(item, dict):
                errors.append(f"{prefix}는 object여야 합니다.")
                continue
            if not isinstance(item.get("decision"), str):
                errors.append(f"{prefix}.decision은 string이어야 합니다.")
            if not isinstance(item.get("reason"), str):
                errors.append(f"{prefix}.reason은 string이어야 합니다.")

    validation = data.get("5_Validation", [])
    if isinstance(validation, list):
        for index, item in enumerate(validation):
            if not isinstance(item, str):
                errors.append(f"`5_Validation[{index}]`는 string이어야 합니다.")

    risk_assessment = data.get("6_Risk_Assessment", [])
    if isinstance(risk_assessment, list):
        for index, item in enumerate(risk_assessment):
            prefix = f"`6_Risk_Assessment[{index}]`"
            if not isinstance(item, dict):
                errors.append(f"{prefix}는 object여야 합니다.")
                continue
            if not isinstance(item.get("risk"), str):
                errors.append(f"{prefix}.risk는 string이어야 합니다.")
            probability = item.get("probability")
            if not isinstance(probability, str) or probability not in RISK_LEVEL_VALUES:
                errors.append(f"{prefix}.probability는 {RISK_LEVEL_VALUES} 중 하나여야 합니다.")
            impact = item.get("impact")
            if not isinstance(impact, str) or impact not in RISK_LEVEL_VALUES:
                errors.append(f"{prefix}.impact는 {RISK_LEVEL_VALUES} 중 하나여야 합니다.")
            if not isinstance(item.get("mitigation_strategy"), str):
                errors.append(f"{prefix}.mitigation_strategy는 string이어야 합니다.")

    rollback = data.get("7_Rollback_Strategy", {})
    if isinstance(rollback, dict):
        phase_rollbacks = rollback.get("phase_rollbacks")
        if not isinstance(phase_rollbacks, list):
            errors.append("`7_Rollback_Strategy.phase_rollbacks`는 array여야 합니다.")
        else:
            for index, item in enumerate(phase_rollbacks):
                prefix = f"`7_Rollback_Strategy.phase_rollbacks[{index}]`"
                if not isinstance(item, dict):
                    errors.append(f"{prefix}는 object여야 합니다.")
                    continue
                if not isinstance(item.get("phase_id"), int):
                    errors.append(f"{prefix}.phase_id는 int여야 합니다.")
                if not isinstance(item.get("trigger"), str):
                    errors.append(f"{prefix}.trigger는 string이어야 합니다.")
                if not _is_string_list(item.get("steps")):
                    errors.append(f"{prefix}.steps는 string array여야 합니다.")
                if not isinstance(item.get("restore_target"), str):
                    errors.append(f"{prefix}.restore_target는 string이어야 합니다.")

    tracking = data.get("8_Progress_Tracking", {})
    if isinstance(tracking, dict):
        phase_status = tracking.get("phase_status")
        if not isinstance(phase_status, list):
            errors.append("`8_Progress_Tracking.phase_status`는 array여야 합니다.")
        else:
            for index, item in enumerate(phase_status):
                prefix = f"`8_Progress_Tracking.phase_status[{index}]`"
                if not isinstance(item, dict):
                    errors.append(f"{prefix}는 object여야 합니다.")
                    continue
                if not isinstance(item.get("phase_id"), int):
                    errors.append(f"{prefix}.phase_id는 int여야 합니다.")
                status = item.get("status")
                if not isinstance(status, str) or status not in PHASE_STATUS_VALUES:
                    errors.append(f"{prefix}.status는 {PHASE_STATUS_VALUES} 중 하나여야 합니다.")
                progress_percent = item.get("progress_percent")
                if not isinstance(progress_percent, int) or not (0 <= progress_percent <= 100):
                    errors.append(f"{prefix}.progress_percent는 0~100 int여야 합니다.")

        overall_progress_percent = tracking.get("overall_progress_percent")
        if not isinstance(overall_progress_percent, int) or not (0 <= overall_progress_percent <= 100):
            errors.append("`8_Progress_Tracking.overall_progress_percent`는 0~100 int여야 합니다.")

        time_tracking = tracking.get("time_tracking")
        if not isinstance(time_tracking, list):
            errors.append("`8_Progress_Tracking.time_tracking`는 array여야 합니다.")
        else:
            for index, item in enumerate(time_tracking):
                prefix = f"`8_Progress_Tracking.time_tracking[{index}]`"
                if not isinstance(item, dict):
                    errors.append(f"{prefix}는 object여야 합니다.")
                    continue
                if not isinstance(item.get("phase_id"), int):
                    errors.append(f"{prefix}.phase_id는 int여야 합니다.")
                if not _is_number(item.get("estimated_hours")):
                    errors.append(f"{prefix}.estimated_hours는 number여야 합니다.")
                actual_hours = item.get("actual_hours")
                if actual_hours is not None and not _is_number(actual_hours):
                    errors.append(f"{prefix}.actual_hours는 number|null이어야 합니다.")
                variance_hours = item.get("variance_hours")
                if variance_hours is not None and not _is_number(variance_hours):
                    errors.append(f"{prefix}.variance_hours는 number|null이어야 합니다.")

        if not _is_string_list(tracking.get("notes_and_learnings")):
            errors.append("`8_Progress_Tracking.notes_and_learnings`는 string array여야 합니다.")

        blockers = tracking.get("blockers")
        if not isinstance(blockers, list):
            errors.append("`8_Progress_Tracking.blockers`는 array여야 합니다.")
        else:
            for index, item in enumerate(blockers):
                prefix = f"`8_Progress_Tracking.blockers[{index}]`"
                if not isinstance(item, dict):
                    errors.append(f"{prefix}는 object여야 합니다.")
                    continue
                if not isinstance(item.get("title"), str):
                    errors.append(f"{prefix}.title은 string이어야 합니다.")
                if not isinstance(item.get("resolution"), str):
                    errors.append(f"{prefix}.resolution은 string이어야 합니다.")

    return errors


def _bool_to_checkbox(value: bool) -> str:
    return "[x]" if value else "[ ]"


def _render_list(lines: list[str], title: str, values: list[str]) -> None:
    lines.append(f"### {title}")
    if not values:
        lines.append("- (없음)")
    else:
        for value in values:
            lines.append(f"- {value}")
    lines.append("")


def _render_item_done_list(lines: list[str], title: str, values: list[dict[str, Any]]) -> None:
    lines.append(f"#### {title}")
    if not values:
        lines.append("- (없음)")
    else:
        for value in values:
            lines.append(f"- {_bool_to_checkbox(bool(value.get('done')))} {value.get('item', '')}")
    lines.append("")


def _render_markdown(data: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Plans")
    lines.append("")
    lines.append("> 이 문서는 `Plans.json`에서 자동 생성되는 **MVP 6주 로드맵 문서(예시 명령 포함)** 입니다.")
    lines.append("> 직접 수정하지 말고 `python scripts/plans_sync.py render --input Plans.json --output Plans.md`를 실행하세요.")
    lines.append("> 테스트 명령은 즉시 실행 강제가 아닌 구현 단계 구체화를 위한 예시입니다.")
    lines.append("> ⚠️ Phase 게이트 통과 전 다음 단계 진행 금지")
    lines.append("")

    purpose = data["1_Purpose"]
    lines.append("## 1. 문서 목적")
    ordered_purpose_keys = [
        "document_mode",
        "horizon_weeks",
        "main_objective",
        "hard_gate_definition",
        "tdd_execution_principle",
    ]
    for key in ordered_purpose_keys:
        if key in purpose:
            lines.append(f"- **{key}**: {purpose[key]}")
    for extra_key in sorted(key for key in purpose.keys() if key not in set(ordered_purpose_keys)):
        lines.append(f"- **{extra_key}**: {purpose[extra_key]}")
    lines.append("")

    strategy = data["2_Testing_Strategy"]
    lines.append("## 2. 테스트 전략")
    if "command_policy" in strategy:
        lines.append(f"- **command_policy**: {strategy['command_policy']}")
    lines.append("")
    frameworks = strategy.get("frameworks", {})
    lines.append("### 프레임워크")
    if frameworks:
        for key in sorted(frameworks.keys()):
            lines.append(f"- **{key}**: {frameworks[key]}")
    else:
        lines.append("- (없음)")
    lines.append("")
    _render_list(lines, "원칙", strategy.get("principles", []))
    _render_list(
        lines,
        "예시 테스트 명령",
        [f"`{value}`" for value in strategy.get("test_commands", [])],
    )
    if "temporary_assumptions" in strategy:
        _render_list(lines, "임시 가정", strategy.get("temporary_assumptions", []))

    lines.append("## 3. 로드맵 진행")
    lines.append("")
    for phase in data["3_Progress"]:
        lines.append(f"## Phase {phase['phase_id']}: {phase['feature']}")
        lines.append(f"- **목표 기간**: {phase.get('target_window', '')}")
        lines.append(f"- **예상 소요 시간**: {phase.get('estimated_hours', '')}h")
        lines.append(f"- **상태**: {phase.get('status', '')}")
        lines.append(f"- **목표**: {phase.get('details', '')}")
        lines.append(f"- **완료 신호(게이트)**: {phase.get('exit_signal', '')}")
        lines.append("")
        _render_list(lines, "산출물/수용 기준", phase.get("acceptance_criteria_mapping", []))
        _render_list(lines, "의존성", phase.get("dependencies", []))
        _render_list(lines, "주요 리스크", phase.get("risks", []))
        _render_list(lines, "엣지 케이스 범위", phase.get("edge_case_coverage", []))
        lines.append("### 개발 원칙 체크리스트 (RED/GREEN/REFACTOR)")
        step_map = {
            item["step"]: item
            for item in phase.get("checklist", [])
            if isinstance(item, dict) and "step" in item
        }
        for step in EXPECTED_CHECKLIST_STEPS:
            entry = step_map.get(step, {"desc": "(누락)", "done": False})
            lines.append(f"- {_bool_to_checkbox(bool(entry.get('done')))} **{step}**: {entry.get('desc', '')}")
        lines.append("")

        gate = phase.get("quality_gate", {})
        lines.append("### 품질 게이트 (차단형)")
        lines.append(f"- **blocking**: {gate.get('blocking', False)}")
        lines.append(f"- **stop_message**: {gate.get('stop_message', '')}")
        lines.append("")
        _render_item_done_list(lines, "TDD 준수", gate.get("tdd_compliance", []))
        _render_item_done_list(lines, "빌드/테스트", gate.get("build_and_tests", []))
        _render_item_done_list(lines, "코드 품질", gate.get("code_quality", []))
        _render_item_done_list(lines, "보안/성능", gate.get("security_and_performance", []))
        _render_item_done_list(lines, "문서화", gate.get("documentation", []))
        _render_item_done_list(lines, "수동 검증", gate.get("manual_testing", []))
        _render_list(
            lines,
            "품질 게이트 검증 명령(예시)",
            [f"`{value}`" for value in gate.get("validation_commands", [])],
        )

        _render_list(
            lines,
            "예시 테스트 명령",
            [f"`{value}`" for value in phase.get("test_commands", [])],
        )
        _render_list(lines, "예상 결과 예시", phase.get("result_examples", []))
        if "notes" in phase:
            _render_list(lines, "비고", phase.get("notes", []))

    lines.append("## 4. 의사결정 로그")
    decision_log = data["4_Decision_Log"]
    if not decision_log:
        lines.append("- (없음)")
    else:
        for item in decision_log:
            lines.append(f"- **결정**: {item.get('decision', '')}")
            lines.append(f"- **근거**: {item.get('reason', '')}")
    lines.append("")

    lines.append("## 5. 검증 계획")
    for command in data["5_Validation"]:
        lines.append(f"- {command}")
    lines.append("")

    lines.append("## 6. 리스크 평가")
    risk_assessment = data["6_Risk_Assessment"]
    if risk_assessment:
        lines.append("| 리스크 | 확률 | 영향 | 완화 전략 |")
        lines.append("|---|---|---|---|")
        for item in risk_assessment:
            lines.append(
                f"| {item.get('risk', '')} | {item.get('probability', '')} | {item.get('impact', '')} | {item.get('mitigation_strategy', '')} |"
            )
    else:
        lines.append("- (없음)")
    lines.append("")

    lines.append("## 7. 롤백 전략")
    rollbacks = data["7_Rollback_Strategy"].get("phase_rollbacks", [])
    if rollbacks:
        for rollback in rollbacks:
            lines.append(f"### Phase {rollback.get('phase_id', '')}")
            lines.append(f"- **트리거**: {rollback.get('trigger', '')}")
            lines.append(f"- **복구 목표**: {rollback.get('restore_target', '')}")
            lines.append("- **롤백 단계**:")
            for step in rollback.get("steps", []):
                lines.append(f"- {step}")
            lines.append("")
    else:
        lines.append("- (없음)")
        lines.append("")

    lines.append("## 8. 진행률 추적")
    tracking = data["8_Progress_Tracking"]
    lines.append(f"- **overall_progress_percent**: {tracking.get('overall_progress_percent', 0)}%")
    lines.append("")
    lines.append("### Phase 상태")
    phase_status = tracking.get("phase_status", [])
    if phase_status:
        for item in phase_status:
            lines.append(
                f"- Phase {item.get('phase_id', '')}: status={item.get('status', '')}, progress={item.get('progress_percent', 0)}%"
            )
    else:
        lines.append("- (없음)")
    lines.append("")
    lines.append("### 시간 추적")
    time_tracking = tracking.get("time_tracking", [])
    if time_tracking:
        lines.append("| Phase | Estimated | Actual | Variance |")
        lines.append("|---|---:|---:|---:|")
        for item in time_tracking:
            actual = "-" if item.get("actual_hours") is None else item.get("actual_hours")
            variance = "-" if item.get("variance_hours") is None else item.get("variance_hours")
            lines.append(
                f"| {item.get('phase_id', '')} | {item.get('estimated_hours', '')} | {actual} | {variance} |"
            )
    else:
        lines.append("- (없음)")
    lines.append("")
    _render_list(lines, "노트/학습", tracking.get("notes_and_learnings", []))
    lines.append("### 블로커")
    blockers = tracking.get("blockers", [])
    if blockers:
        for blocker in blockers:
            lines.append(f"- **{blocker.get('title', '')}**: {blocker.get('resolution', '')}")
    else:
        lines.append("- (없음)")
    lines.append("")

    return "\n".join(lines)


def _handle_validate(input_path: Path) -> int:
    try:
        data = _load_json(input_path)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    errors = _validate_schema(data)
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("검증 통과")
    return 0


def _handle_render(input_path: Path, output_path: Path) -> int:
    try:
        data = _load_json(input_path)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    errors = _validate_schema(data)
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    rendered = _render_markdown(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"렌더 완료: {output_path}")
    return 0


def _normalize_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized


def _handle_check(input_path: Path, output_path: Path) -> int:
    try:
        data = _load_json(input_path)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    errors = _validate_schema(data)
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    rendered = _normalize_text(_render_markdown(data))
    if not output_path.exists():
        print("Plans.json 수정 후 render 미실행: Plans.md 파일이 없습니다.", file=sys.stderr)
        return 1
    current = _normalize_text(output_path.read_text(encoding="utf-8"))
    if rendered != current:
        print("Plans.json 수정 후 render 미실행: Plans.md가 Plans.json과 동기화되어 있지 않습니다.", file=sys.stderr)
        print(
            "동기화 명령: python scripts/plans_sync.py render --input Plans.json --output Plans.md",
            file=sys.stderr,
        )
        return 1

    print("동기화 확인 통과")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Plans.json 동기화 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="JSON 스키마 검증")
    validate_parser.add_argument("--input", required=True, type=Path)

    render_parser = subparsers.add_parser("render", help="JSON을 Markdown으로 렌더")
    render_parser.add_argument("--input", required=True, type=Path)
    render_parser.add_argument("--output", required=True, type=Path)

    check_parser = subparsers.add_parser("check", help="JSON과 Markdown 동기화 확인")
    check_parser.add_argument("--input", required=True, type=Path)
    check_parser.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "validate":
        return _handle_validate(args.input)
    if args.command == "render":
        return _handle_render(args.input, args.output)
    if args.command == "check":
        return _handle_check(args.input, args.output)
    print("알 수 없는 명령입니다.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
