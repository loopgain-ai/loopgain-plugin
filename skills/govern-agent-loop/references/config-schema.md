<!-- provenance | canonical: https://github.com/loopgain-ai/loopgain-plugin -->

# `.loopgain-goal.json` — full schema

Placed at a project root, this file proposes a verifier for the plugin's `Stop` hook.
Absent = silent no-op. Present but unapproved = no command execution and stop allowed.
The trusted installed `hooks/approve_goal.py` requires explicit interactive terminal
approval. User-owned records outside the repository bind the canonical project path
and SHA-256 of the exact config bytes; any edit requires approval again. The hook
never creates an approval record. Approval does not sandbox the verifier or pin the
contents of scripts/tests it runs.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `verify_command` | string | *(required)* | Shell command run in the project root after each turn. Its combined stdout+stderr must contain the error number. |
| `error_pattern` | string (regex) | *(required)* | Regex with exactly **one capture group** that is the error number. Applied to the verifier output with `re.search`. |
| `no_match_means_zero` | bool | `true` | If the pattern doesn't match: `true` → treat error as `0` (done); `false` → treat as "can't measure" and allow the stop without governing this turn. |
| `target_error` | number | `0` | The error value that counts as converged. |
| `max_turns` | int | `30` | Hard safety cap. The loop always ends by this many governed turns, regardless of LoopGain's state. |
| `stall_terminate_count` | int | `2` | Consecutive `STALLING` turns before the hook stops the loop. |
| `timeout_seconds` | int | `180` | Max seconds to wait for `verify_command`. On timeout the hook allows the stop (fails open). |

## Choosing `error_pattern`

The regex must capture a single number. Examples:

| Verifier | Typical output line | `error_pattern` |
|---|---|---|
| `pytest -q` | `3 failed, 40 passed` | `(\\d+) failed` |
| `npm test` (jest) | `Tests: 2 failed, 18 passed` | `(\\d+) failed` |
| `tsc --noEmit` | `Found 5 errors.` | `Found (\\d+) error` |
| `ruff check .` | `Found 7 errors.` | `Found (\\d+) error` |
| `go test ./...` | count `FAIL` lines yourself | wrap in a command that prints a count, e.g. `sh -c 'go test ./... 2>&1 \| grep -c ^FAIL'` with pattern `(\\d+)` |

When "all good" produces **no** matching line (pytest prints no "N failed" when green),
keep `no_match_means_zero: true` so a clean run reads as `error = 0` → converged.

## Fail-open guarantees

The hook allows the stop (never traps the session) when any of these hold: no config
file, absent/invalid/mismatched local approval, malformed config, missing `verify_command`/`error_pattern`, `loopgain` not
importable, verifier errors or times out, a non-matching pattern with
`no_match_means_zero: false`, or `max_turns` reached. Governing only ever *blocks* a
stop when it has a real number and LoopGain says the loop is still improving.
