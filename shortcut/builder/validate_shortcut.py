#!/usr/bin/env python3
"""Validate Apple Shortcuts binary plist (.shortcut) files for structural correctness."""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

CONTROL_FLOW_IDENTIFIERS = {
    "is.workflow.actions.conditional",
    "is.workflow.actions.choosefrommenu",
    "is.workflow.actions.repeat.each",
}


def validate_shortcut_file(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open("rb") as f:
        data = plistlib.load(f)

    for required_key in (
        "WFWorkflowActions",
        "WFWorkflowMinimumClientVersion",
        "WFWorkflowIcon",
        "WFWorkflowInputContentItemClasses",
    ):
        if required_key not in data:
            errors.append(f"Missing required top-level key: {required_key}")

    actions = data.get("WFWorkflowActions", [])
    if not isinstance(actions, list) or not actions:
        errors.append("WFWorkflowActions must be a non-empty list")
        return errors

    stack: list[tuple[str, str]] = []
    for idx, action in enumerate(actions):
        ident = action.get("WFWorkflowActionIdentifier")
        params = action.get("WFWorkflowActionParameters", {})
        if not ident:
            errors.append(f"Action {idx} missing WFWorkflowActionIdentifier")
            continue

        if ident in CONTROL_FLOW_IDENTIFIERS:
            mode = params.get("WFControlFlowMode")
            gid = params.get("GroupingIdentifier")
            if not gid:
                errors.append(f"Action {idx} ({ident}) missing GroupingIdentifier")
                continue
            if mode == 0:
                stack.append((ident, gid))
            elif mode == 1:
                if not stack or stack[-1] != (ident, gid):
                    errors.append(f"Action {idx} ({ident}) mid-flow mismatch for {gid}")
            elif mode == 2:
                if not stack or stack[-1] != (ident, gid):
                    errors.append(f"Action {idx} ({ident}) end-flow mismatch for {gid}")
                else:
                    stack.pop()
            else:
                errors.append(f"Action {idx} ({ident}) invalid WFControlFlowMode: {mode}")

    if stack:
        errors.append(f"Unclosed control flow blocks: {stack}")

    for q_idx, q in enumerate(data.get("WFWorkflowImportQuestions", [])):
        a_idx = q.get("ActionIndex")
        if a_idx is None or not (0 <= a_idx < len(actions)):
            errors.append(f"Import question {q_idx} has out-of-bounds ActionIndex: {a_idx}")

    return errors


def main() -> int:
    dist_dir = Path(__file__).resolve().parents[1] / "dist"
    files = sorted(dist_dir.glob("*.shortcut"))
    if not files:
        print("No .shortcut files found in shortcut/dist/", file=sys.stderr)
        return 1

    has_err = False
    for path in files:
        errs = validate_shortcut_file(path)
        if errs:
            has_err = True
            print(f"[FAIL] {path.name}:")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"[OK] {path.name} passed structural validation.")
    return 1 if has_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
