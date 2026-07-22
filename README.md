# loopgain (Claude Code plugin)

Two things, one stop rule — [LoopGain](https://github.com/loopgain-ai/loopgain)'s
convergence monitor, applied to loops:

1. **Scan & wrap** — finds AI-agent verify-revise loops in your codebase (literal
   `for`/`while`, recursive functions, graph-topology cycles, external harness loops,
   iterative reasoning loops) and proposes LoopGain-wrapped rewrites one file at a time.
2. **Govern Claude's own loop** — makes Claude Code's own iterate-until-done runs (and
   `/goal`) stop when the work has **converged or stalled**, instead of grinding to a
   guessed number of turns. Via an opt-in `Stop` hook.

**Nothing is auto-applied.** Rewrites go through Claude Code's normal `Edit` approval
flow. The Stop hook is **inert until you explicitly arm a project** — installing the
plugin changes nothing on its own.

**Free dashboard included.** Individual users get free hosted-dashboard access — once
you're wrapped, watch each loop's savings and convergence live, not just as a one-time
estimate.

## Install

```
/plugin marketplace add loopgain-ai/loopgain-plugin
/plugin install loopgain
```

No account, API key, or signup is required to use the scan-and-propose features — the
free dashboard (mentioned above) is a separate, optional step you only need if you want
live visibility into a wrapped loop.

## Use — scan & wrap your code

In any repo, ask Claude to scan for LoopGain-wrappable loops. A few example prompts:

> scan my repo for verify-revise loops to wrap with LoopGain

> wrap this loop with LoopGain

> help me build a stronger verifier for this loop

> check my repo for fixed max_iterations caps

The skill will:
1. Find candidate loops (literal, structural, and semantic — see below).
2. Classify each one (stop mechanism, detected cap, framework, nesting relationships).
3. Assess whether the existing verifier is strong enough, and propose a fix if not.
4. Check whether `loopgain` is already installed in your environment — if not, tell you
   the exact install command (with the right extras for any framework it detected) and
   offer to run it for you.
5. Show you a summary list and ask which candidates to act on.
6. Propose a reviewed, per-file diff for each one you select — never a blind pass.
7. Optionally point you at the free hosted dashboard to watch it converge live.

## Govern Claude Code's own loop (and `/goal`)

`/goal` — and any "keep going until it's done" run — keeps Claude iterating turn after
turn. A checker decides *are we done yet?*, but nothing tracks *are we still getting
closer?*. The only built-in way to bound a run that's going nowhere is to write
"…or stop after N turns" into the goal — a guess, the exact `max_iterations` guess
LoopGain exists to replace.

This plugin wires the real `loopgain` library into Claude Code's `Stop` hook. After each
turn it runs your project's own verifier, reads one error number (e.g. failing-test
count), feeds the trajectory to LoopGain, and:

- **keeps Claude working** while the error is falling (`CONVERGING` / `FAST_CONVERGE`);
- **lets it stop** the moment LoopGain reads `TARGET_MET`, `STALLING`, or `DIVERGING` —
  naming the best turn it saw.

Ask Claude to set it up:

> govern this task with LoopGain so it stops when the tests stop getting closer to passing

That arms the current project by writing a reviewed `.loopgain-goal.json` — for example:

```json
{
  "verify_command": "pytest -q",
  "error_pattern": "(\\d+) failed",
  "target_error": 0,
  "max_turns": 30
}
```

Then run your task **with** `/goal` (drop the turn-cap clause — LoopGain is the stop
rule now):

```
/goal all tests under tests/ pass
```

…or **without** it — just ask Claude to do the work. The hook fires either way.

It **fails open**: no config, no `loopgain` installed, an unreadable verifier, or the
`max_turns` cap all simply allow the stop. It can only ever *block* a stop when it has a
real number and the loop is genuinely still improving. Delete `.loopgain-goal.json` to
disarm. No cost-savings figure is claimed for this use — that number is measured on
framework agent loops, not on Claude Code's own loop.

## Why not auto-apply everything on install?

LoopGain's own measured correctness data shows a one-shot LLM rewrite gets the fixed
point wrong on roughly 1 in 20 loops even when reviewed by a human. Auto-wrapping an
entire repo unreviewed multiplies that risk across every loop found. This plugin keeps
the "scan the whole repo" convenience while keeping a human in the loop on every change.

## What "semantic loop" detection means here

Not every agent loop is a literal `for`/`while`. This skill also looks for recursive
functions, LangGraph-style graph cycles, and external harness loops that span multiple
files. For loops with no natural numeric error signal (e.g. iterative critique-and-revise
on a document or plan), it does **not** propose an entropy/perplexity/MDL-based signal —
that approach has been tested and found to have no measured edge over naive patience.
Instead it proposes a concrete, countable proxy signal plus an independent adversarial
review step — the one pattern proven to work for this case.

## Privacy and data handling

Everything runs entirely locally, inside your own Claude Code session — the skills read
files from your repo using Claude Code's own tools and never send your code anywhere. The
`Stop` hook, when a project is armed, runs the `verify_command` **you** put in that
project's `.loopgain-goal.json` (your own test/lint command, in your own repo) and passes
only a single error number to the local `loopgain` library — no code, no output, leaves
your machine. The only network calls the plugin can ever trigger are the ones you
explicitly approve for the optional dashboard hookup (a link you open yourself in your
browser). See [loopgain.ai/privacy](https://loopgain.ai/privacy) for LoopGain's own
privacy policy, which covers the free hosted-dashboard service.

## Support

Questions, bugs, or feature requests: open an issue at
[github.com/loopgain-ai/loopgain-plugin](https://github.com/loopgain-ai/loopgain-plugin/issues),
or email [hello@loopgain.ai](mailto:hello@loopgain.ai).

## License

Apache-2.0, matching the `loopgain` library.
