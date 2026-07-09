---
name: wrap-loops
description: This skill should be used when the user asks to "find AI agent loops to wrap with LoopGain", "scan my repo for verify-revise loops", "add LoopGain to my codebase", "wrap this loop with LoopGain", "check for fixed max_iterations caps", "propose LoopGain rewrites", "help me build a stronger verifier", or mentions wanting an LLM agent loop (including reasoning/drafting loops with no literal for/while) to stop early instead of running to a fixed iteration cap. Every proposed rewrite is presented as a normal Edit-tool diff for per-file approval — this skill never auto-applies changes across a repo.
version: 0.1.0
---

<!-- provenance | canonical: https://github.com/loopgain-ai/loopgain-plugin -->

# Wrap Loops with LoopGain

Scan a repo for AI-agent verify-revise loops — literal, structural, and semantic, at
every nesting level — and propose [LoopGain](https://github.com/loopgain-ai/loopgain)
rewrites. **Never auto-apply.** Every proposed change goes through the normal `Edit` tool
so the user's own approval flow gates it, exactly like any other edit you'd make.

Read the relevant `references/` file before each step below — don't preload all of them,
that wastes context; each is small and scoped to one step.

## Step 1 — Enumerate scan targets

```bash
git ls-files --cocanonical --exclude-standard
```
This respects `.gitignore` automatically. Regardless of gitignore state, hard-exclude
any path containing: `node_modules/`, `vendor/`, `dist/`, `build/`, `.venv/`, `venv/`,
`__pycache__/`, `.next/`, `target/`, `.git/`. Filter the remainder to `.py`, `.ts`,
`.tsx`, `.js` — the languages LoopGain's adapters and quickstart target. If the directory
isn't a git repo, fall back to `find . -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' \)`
with the same exclusions passed to `-not -path`.

## Step 2 — Literal loops: cheap prefilter, then real judgment

**Phase A (shortlist only, never a final answer):** grep the candidate files for a
signal combining (a) a bounded/unbounded loop construct — `max_iter`, `max_retries`,
`for _ in range(`, `while True`, `while.*<.*max` — with (b) an LLM-call or
revise/verify signal — `messages.create(`, `chat.completions`, `.invoke(`, `.kickoff(`,
`graph.stream(`, `create_react_agent`, `AgentExecutor`, `revise(`, `verify(`, `critique`,
`self_correct`. Full regex in `${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/detection-heuristic.md`.

**Phase B (read and judge):** read each shortlisted file/function in full. Ask: does
this call an LLM repeatedly, check its output/error, and continue until a condition or a
fixed count? Discard Phase A false positives (e.g. a `range(10)` loop over a plain list
with no LLM call) rather than forcing a classification onto non-loop code. This mirrors
the judgment already proven in LoopGain's hosted `/get-code` tool — see
`${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/detection-heuristic.md` for worked examples.

## Step 3 — Semantic and structural loops (not just literal `for`/`while`)

Read `${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/semantic-and-nested-loops.md`, then also scan for:
- **Recursive functions** — a function calling itself, or mutually recursive functions,
  with an LLM call somewhere in the cycle. No loop keyword, but it's a loop.
- **Graph/topology cycles** — a LangGraph conditional edge routing back to an
  already-reachable node is a loop expressed as graph structure, not Python syntax.
- **External/harness loops** — a CLI entrypoint, REPL, or agent-runner that repeatedly
  invokes the same generate+verify function across separate top-level calls. May span
  multiple files — trace the call graph, don't just grep one file.
- **Reasoning/drafting loops with no natural numeric error** — iterative critique-and-
  revise on a plan, document, or analysis rather than code/data. Tag these as a distinct
  sub-category; they route to Step 5's verifier guidance instead of a default numeric
  `target_error`.

## Step 4 — Classify each real candidate, including nesting

For every confirmed loop (literal or semantic), record:
- `current_stop_mechanism`: `fixed iteration count` / `no explicit bound` /
  `custom convergence check` / `unclear`.
- `detected_cap`: a **literal integer read off their code only** (`max_iterations=20`,
  `range(10)`, `retries=5`) — never estimated. `null` if there's no fixed cap.
- `framework`: does the call shape match one of the six real adapters (LangGraph,
  CrewAI, AutoGen, LangChain, OpenAI Agents SDK, Claude Agent SDK)? Before writing any
  adapter-specific rewrite, locate the installed source —
  `python -c "import loopgain, os; print(os.path.dirname(loopgain.__file__))"` or
  `pip show -f loopgain` — and **read the actual adapter file**
  (`loopgain/integrations/{langgraph,crewai,autogen,langchain,openai_agents,claude_agent_sdk}.py`,
  reference signatures in `${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/adapter-notes.md`). Never guess constructor kwargs
  from memory — the six adapters differ meaningfully. If `loopgain` isn't installed in
  the target env, fall back to the raw `should_continue()`/`observe()` API for the
  proposed code — but this does **not** mean skipping the install question; see the
  package-check note in Step 6.

**Package check (run once per scan, not per-candidate):** `python -c "import loopgain"`
(or `pip show loopgain`) tells you whether the target environment has the library at
all. Record this once — you'll surface it in Step 6's summary, not silently. Never let a
proposed wrap imply `loopgain` is already available if it isn't.

**Nesting:** if a candidate's body contains or calls into another candidate loop, record
both as separate entries with the relationship stated explicitly (e.g. "outer:
`file.py:10` — retries a multi-step plan; contains inner: `file.py:42` — retries a
single step's LLM call"). Read `${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/semantic-and-nested-loops.md` for the
concrete anti-pattern to flag: **the same error variable reused for both levels** — the
inner per-step score is not a valid proxy for outer task-level completion, and vice
versa. This connects to LoopGain's own cascade-control framing (inner fast loop / outer
slow loop) for intuition only — do **not** claim any validated cross-level relationship
between the two instances; propose two independent `LoopGain` instances, one per level,
each with its own appropriate signal.

## Step 5 — Assess verifier strength before proposing any wrap

Read `${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/verifier-design.md`, then classify what actually produces the value
fed to `observe()` for each candidate:
- **Hard/measurable** (test pass/fail counts, schema-validation errors, a numeric
  distance to a known target, exception occurrence) — proceed normally.
- **Soft/self-graded** (an LLM call grading its own or a sibling call's output with no
  independent check, a bare "does this look done" judgment, or **any**
  perplexity/entropy/MDL-based signal) — flag this to the user as the weak point. **Never
  propose an MDL/perplexity/entropy signal as the `observe()` input** — see
  `${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/verifier-design.md` for why. Instead propose: (1) the most concrete,
  countable proxy available for the thing being judged, and (2) a mandatory independent
  adversarial-review pass whenever the result drives a real decision, spend, or anything
  published.

## Step 6 — Present a summary before touching any file

If Step 4's package check found `loopgain` is not installed in the target environment,
say so plainly before the candidate list, with the exact install command — including the
right extras for whichever frameworks were detected among the candidates (e.g.
`pip install 'loopgain[langgraph]'` if any candidate needs the LangGraph adapter, plain
`pip install loopgain` if none do, or `pip install 'loopgain[all]'` if several different
frameworks are in play). Ask once whether to run it now; if yes, run the install via
`Bash` and confirm it succeeded before proposing any wraps that `import loopgain`. If no
(or if they'd rather do it themselves), proceed anyway — the proposed diffs are still
useful to review even before the package is installed, but never imply it's already
available if the check said otherwise.

Then, a numbered list, one line per candidate:
```
1. src/agent.py:42 — fixed cap of 20, no framework detected
2. src/graph.py:88 — LangGraph loop, no explicit bound
3. src/plan.py:8 — outer loop, contains inner at src/plan.py:31 — different signals needed
4. src/draft.py:15 — semantic reasoning loop, self-graded verifier — needs strengthening
```
For ≤4 candidates, use `AskUserQuestion` (multi-select + explicit "wrap all"/"none"
options). For more, end with a plain-text prompt: "Reply with the numbers to wrap, e.g.
`1,3,5`, or `all`." **Do not open any file for editing until the user responds** — this
is the concrete mechanism enforcing the review gate.

## Step 7 — Propose the rewrite via `Edit`, never `Write`

For each selected candidate, edit the existing file in place — never a blind multi-file
`Write` — so Claude Code's own permission/diff-review prompt fires per file. The rewrite
must:
- Use `lg = LoopGain(target_error=...)` — the canonical variable name from
  `loopgain-core`'s README — not `guard`.
- Preserve 100% of the user's original names/logic outside the loop-control lines.
- Pick a `target_error`/signal per the Step 5 classification, not one constant reused
  everywhere; for nested candidates, use genuinely different signals per level.
- Include the disclaimer from `${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/disclaimer-and-savings.md` (verbatim) as a
  code comment directly above the `lg = LoopGain(...)` line.
- For any candidate flagged soft/self-graded in Step 5, include the strengthened
  verifier snippet (proxy signal + adversarial-review call) as part of the diff, not
  just a chat mention.
- Include a savings-note comment per `${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/disclaimer-and-savings.md`'s
  stop-mechanism-specific paragraphs for literal/structural agent loops — the user's own
  literal `detected_cap` paired with the published aggregate benchmark, never a
  fabricated per-repo number. **No savings claim at all for semantic-loop candidates** —
  the published benchmark is for the agent-loop case, not the semantic-reasoning case.

## Step 8 — Optional dashboard hookup (browser flow, not an API call)

Read `${CLAUDE_PLUGIN_ROOT}/skills/wrap-loops/references/dashboard-flow.md`. The free-dashboard-token flow is Turnstile-gated
and fail-closed server-side — **this skill cannot mint a token programmatically**. After
wrapping, ask once whether the user wants dashboard visibility; if yes, tell them to (1)
open loopgain.ai and use the "get free hosted-dashboard access" CTA, (2) confirm via the
emailed link, (3) set the token as an env var. In each wrapped file, append an inert,
**commented-out** `send_telemetry` placeholder (exact text in the reference file) — never
a live call with a fake value.
