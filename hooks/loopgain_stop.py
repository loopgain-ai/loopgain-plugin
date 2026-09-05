#!/usr/bin/env python3
"""LoopGain Stop hook — govern Claude Code's own agentic loop by convergence.

Claude Code fires a `Stop` hook after each turn. This script:
  1. Does nothing at all unless the current project has been *explicitly armed*
     with a user-owned approval for the exact `.loopgain-goal.json` config
     file (prepared by the plugin's
     `govern-agent-loop` skill). No config -> silent exit 0, zero overhead.
  2. When armed: runs the project's own verify command, extracts an error
     number (e.g. failing-test count), feeds the running trajectory to the real
     `loopgain` library, and asks it the one question a fixed turn-cap can't:
     is this loop still improving, or has it converged / stalled / diverged?
  3. Blocks the stop (Claude keeps working) while LoopGain says "still
     improving"; allows the stop the moment LoopGain says target-met, stalled,
     or diverging — instead of grinding to a guessed number of turns.

It never invents an error signal, never makes a savings claim, and fails OPEN:
any ambiguity (no config, missing library, unparseable verifier output, a hard
turn cap) allows the stop rather than trapping the session in a loop.

Config schema (`.loopgain-goal.json` at the project root):
{
  "verify_command": "pytest -q",       # shell command; its output must contain the error number
  "error_pattern": "(\\d+) failed",    # regex, ONE capture group = the error number
  "no_match_means_zero": true,          # if the pattern doesn't match, treat error as 0 (target met)
  "target_error": 0,                    # the error value that counts as done
  "max_turns": 30,                      # hard safety cap regardless of LoopGain
  "stall_terminate_count": 2            # consecutive STALLING turns before stopping
}
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from goal_approval import is_approved, read_goal

CONFIG_NAME = ".loopgain-goal.json"


def _allow_stop(note: str | None = None) -> None:
    """Let the turn end cleanly.

    Emit NOTHING on stdout: any stdout payload on a Stop hook — including
    `hookSpecificOutput.additionalContext` — makes Claude Code *continue* the
    turn rather than stop. A clean stop is exit 0 with an empty stdout. The
    optional note goes to stderr (diagnostics / transcript), which does not
    affect the stop.
    """
    if note:
        print(note, file=sys.stderr)
    sys.exit(0)


def _block(reason: str) -> None:
    """Prevent the turn from ending; Claude continues, shown `reason`."""
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def _state_path(session_id: str, cwd: str) -> str:
    key = hashlib.sha1(f"{session_id}:{cwd}".encode()).hexdigest()[:16]
    d = os.path.join(tempfile.gettempdir(), "loopgain-goal-hook")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{key}.json")


def main() -> None:
    # 1. Read the Stop event. Any parse failure -> do nothing.
    try:
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    cwd = os.path.realpath(event.get("cwd") or os.getcwd())
    session_id = event.get("session_id") or "default"

    # 2. Fast no-op: unarmed projects exit before importing anything heavy.
    config_file = os.path.join(cwd, CONFIG_NAME)
    if not os.path.isfile(config_file):
        sys.exit(0)

    try:
        raw_config, cfg = read_goal(Path(cwd))
    except Exception as e:
        _allow_stop(f"LoopGain: could not read {CONFIG_NAME} ({e}); not governing this turn.")

    if not is_approved(Path(cwd), raw_config):
        _allow_stop("LoopGain: verifier is not approved for this project/configuration; no command ran. "
                    "Review it and run the installed plugin\'s hooks/approve_goal.py from your terminal.")

    verify_command = cfg.get("verify_command")
    error_pattern = cfg.get("error_pattern")
    if not verify_command or not error_pattern:
        _allow_stop(f"LoopGain: {CONFIG_NAME} is missing verify_command or error_pattern; not governing.")

    no_match_zero = bool(cfg.get("no_match_means_zero", True))
    target_error = float(cfg.get("target_error", 0.0))
    max_turns = int(cfg.get("max_turns", 30))
    stall_count = int(cfg.get("stall_terminate_count", 2))

    # 3. Load the trajectory so far for this session+project.
    state_path = _state_path(session_id, cwd)
    try:
        history = json.loads(open(state_path, encoding="utf-8").read()).get("errors", [])
    except Exception:
        history = []

    # Hard safety cap — never govern past max_turns even if LoopGain would.
    if len(history) >= max_turns:
        try:
            os.remove(state_path)
        except OSError:
            pass
        _allow_stop(
            f"LoopGain: reached the max_turns safety cap ({max_turns}) without hitting "
            f"target error {target_error:g}. Stopping. Best error so far: {min(history):g}."
        )

    # 4. Run the project's own verifier and read the error number out of it.
    try:
        proc = subprocess.run(
            verify_command, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=int(cfg.get("timeout_seconds", 180)),
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        _allow_stop("LoopGain: verify_command timed out; not governing this turn.")
    except Exception as e:
        _allow_stop(f"LoopGain: verify_command failed to run ({e}); not governing this turn.")

    m = re.search(error_pattern, output)
    if m:
        try:
            error = float(m.group(1))
        except (ValueError, IndexError):
            _allow_stop("LoopGain: error_pattern matched but produced no number; not governing this turn.")
    elif no_match_zero:
        error = 0.0
    else:
        _allow_stop(
            "LoopGain: could not find the error number in the verifier output "
            "(error_pattern did not match); not governing this turn."
        )

    # 5. Replay the whole trajectory through the real library — it is
    #    deterministic given the error sequence, so no live object needs saving.
    try:
        from loopgain import LoopGain
    except Exception:
        _allow_stop(
            "LoopGain is not installed in this environment, so the convergence hook "
            "can't run. Install it with `pip install loopgain`, then this turn will be governed."
        )

    history.append(error)
    try:
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump({"errors": history}, f)
    except OSError:
        pass

    lg = LoopGain(
        target_error=target_error,
        max_iterations=max_turns,
        stall_terminate_count=stall_count,
    )
    state = "INIT"
    for e in history:
        state = lg.observe(e, output=None)

    turn = len(history)
    prev = history[-2] if len(history) >= 2 else None
    delta = ""
    if prev is not None:
        arrow = "→"
        delta = f" (error {prev:g} {arrow} {error:g})"

    # 6. Decision. should_continue() is the product thesis in one call.
    if lg.should_continue():
        _block(
            f"Not done yet — keep working toward the target. LoopGain reads the loop as "
            f"{state}{delta}: still improving, so it's worth another pass "
            f"(turn {turn}, target error {target_error:g}). "
            f"Don't stop until the error reaches the target or the loop stops improving."
        )
    else:
        try:
            os.remove(state_path)
        except OSError:
            pass
        r = lg.result
        if r.outcome == "converged":
            _allow_stop(
                f"LoopGain: target reached (error {error:g} ≤ {target_error:g}) after "
                f"{turn} turn(s). Converged — stopping is correct."
            )
        else:
            _allow_stop(
                f"LoopGain: loop is {state} — {r.outcome} after {turn} turn(s){delta}. "
                f"It's no longer improving, so continuing would just burn turns. "
                f"Best error seen was {r.best_error:g} (turn {r.best_index + 1}). "
                f"Stopping here; a different approach or human input is likely needed."
            )


if __name__ == "__main__":
    main()
