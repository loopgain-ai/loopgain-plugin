<!-- provenance | canonical: https://github.com/loopgain-ai/loopgain-plugin -->

# Picking the error signal for a governed loop

The Stop hook reads exactly one number per turn. Getting that number right is the
whole job — LoopGain measures the *trajectory* of whatever you feed it, so a signal
that doesn't track "distance to done" produces confident nonsense.

## What makes a good signal

A good signal **monotonically approaches `target_error` as the work actually gets
closer to done**, and is **cheap and deterministic** to compute each turn.

- **Failing-test count** — the canonical one. `target_error: 0`. Distance to done is
  literally how many tests still fail.
- **Type-checker / linter error count** — `tsc --noEmit`, `mypy`, `ruff`. Same shape.
- **Build error count** — for "make it compile" tasks.
- **Schema/contract validation failures** — count of records or fields failing a
  validator.
- **A real numeric distance** — e.g. an optimization where you can compute a residual.

## What to refuse

- **An LLM grading its own output** ("rate how done this is 0–10"). It has no
  independent anchor; it will happily report improvement that isn't there. LoopGain
  can't fix a signal that lies.
- **Perplexity / entropy / MDL / "the text stopped changing much"** as the error.
  These were tested for the no-numeric-signal case and showed no measured edge over
  naive patience. Do not wire them in.
- **Output-diffing** ("stop when the answer stops changing"). Diverging loops change a
  lot; oscillating loops alternate; slow-real-convergence looks identical to a stall
  under an equality check. You need the error trajectory, not output deltas.

If a task genuinely has no countable signal (pure open-ended drafting/critique), say so
plainly and don't arm it — an ungoverned loop with a human checkpoint beats a governed
loop on a meaningless number.

## Building the command + pattern

Prefer a command whose output already prints a count, and a regex that captures it:

- `pytest -q` → `(\\d+) failed`
- `tsc --noEmit` → `Found (\\d+) error`
- When you need to count yourself, wrap it: `sh -c 'RUFF=$(ruff check . 2>&1); echo "$RUFF" | tail -1'` and match the printed number.

Test the command by hand once in the repo before writing the config, so you know the
exact line it prints and can write a pattern that matches it. A wrong pattern doesn't
crash — it fails open (allows the stop) — but then you simply aren't governing.
