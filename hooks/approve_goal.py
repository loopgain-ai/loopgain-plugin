#!/usr/bin/env python3
"""Explicit terminal approval of one project's exact verifier configuration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from goal_approval import read_goal, write_approval


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("Approval requires an interactive terminal; do not pipe a response.")
    try:
        project = args.project.resolve(strict=True)
        raw, config = read_goal(project)
        print("Project:", json.dumps(str(project)))
        print("Configuration:", json.dumps(config, indent=2, ensure_ascii=True))
        print("This shell command runs with your user permissions after each turn.")
        print("Review the command AND any scripts/tests it executes before approving.")
        if input("Type APPROVE to authorize this exact configuration: ") != "APPROVE":
            print("Not approved.")
            return 1
        # Do not approve a configuration changed while the user was reviewing it.
        current, _ = read_goal(project)
        if current != raw:
            raise ValueError("Configuration changed during review; run approval again.")
        write_approval(project, raw)
        print("Approved. Editing the configuration requires approval again.")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Not approved: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
