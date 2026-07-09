# Semantic, structural, and nested loop detection

Not every agent loop is a literal `for`/`while`. This file covers the categories Step 3
of `SKILL.md` scans for, plus how to handle nesting once found (Step 4).

## Recursive functions

A function that calls itself, or two functions that call each other (A→B→A), with an
LLM call somewhere in the cycle, is a loop with no loop keyword:
```python
def refine_answer(question, draft, depth=0):
    verdict = judge.check(draft)
    if verdict.ok or depth > 5:
        return draft
    new_draft = model.invoke(question, feedback=verdict.feedback)
    return refine_answer(question, new_draft, depth + 1)
```
Detect via: grep for a function name appearing both in its own `def` line and in a call
inside its own body (direct recursion), or trace a short call chain (A calls B, B calls
A) for mutual recursion. A recursion depth parameter (`depth`, `retries`, `attempt`)
passed and incremented on each call is the same thing as `detected_cap` for a literal
loop — extract it the same way.

## Graph/topology cycles

LangGraph (and similar graph-based orchestration) expresses a "loop" as an edge that
routes back to an already-visited node, not as Python loop syntax:
```python
graph.add_conditional_edges(
    "verify",
    lambda state: "revise" if state["errors"] else END,
)
graph.add_edge("revise", "verify")   # <- this closes the cycle
```
Detect via: grep for `add_conditional_edges`/`add_edge` calls, build the small
node-name graph they define, and check whether any node is reachable from itself. The
node pair that closes the cycle (here, `verify` ↔ `revise`) is the loop; the conditional
function's branching logic is the stop mechanism to classify in Step 4.

## External/harness loops

A CLI entrypoint, REPL, or agent-runner script that repeatedly invokes the same
generate+verify function across separate top-level calls — the loop may span multiple
files:
```python
# main.py
def main():
    while True:
        task = get_next_task()
        if task is None:
            break
        result = run_agent_once(task)   # defined in agent.py
        save(result)
```
Detect via: tracing the call graph outward from `main()`/CLI entrypoints rather than
grepping one file in isolation — the loop construct and the LLM call it drives may be in
different files entirely.

## Reasoning/drafting loops with no natural numeric error

Iterative critique-and-revise on a plan, document, or analysis (not a code/data
artifact) has no obvious numeric error the way a schema-validation failure count does.
Tag these explicitly as their own sub-category — they route to `verifier-design.md`'s
guidance in Step 5, not a default `target_error` guess.

## Nesting: inner and outer loops are separate candidates with separate signals

When a candidate's body contains, or calls into, another candidate loop, list both
separately with the relationship stated (Step 6's summary format). Example:
```python
def run_plan(plan, max_plan_retries=5):
    for attempt in range(max_plan_retries):          # OUTER
        results = [run_step(step) for step in plan.steps]
        if all(r.ok for r in results):
            return results
        plan = replan(plan, results)

def run_step(step, max_step_retries=3):
    for i in range(max_step_retries):                 # INNER
        output = generate(step.prompt)
        errors = verify(output, step.spec)
        if not errors:
            return output
        step.prompt = revise(step.prompt, errors)
```
`run_plan`'s outer retry and `run_step`'s inner retry are two independent candidates.
Propose two independent `LoopGain` instances — never one instance shared across both,
and never the same error variable reused for both:

- **Inner signal** = per-step correctness (here: `len(errors)` from a single step's
  verify call) — measures whether *this one step* is converging.
- **Outer signal** = task-level/rolled-up completion across the whole plan (e.g. count
  of steps still failing after a full pass, `sum(1 for r in results if not r.ok)`) — a
  genuinely different quantity from any single step's score.

**The concrete anti-pattern to flag**, if found in the user's existing code: the outer
loop reusing the last inner step's error as if it represented overall task completion.
That conflates "the most recent single step converged" with "the whole task is done" —
they are not the same claim, and code that already makes this mistake is worth calling
out even before proposing a LoopGain wrap.

This maps onto LoopGain's own cascade-control framing — inner fast loop, outer slow
loop — for intuition only. **Do not claim** any validated relationship between the two
levels' convergence (e.g. "the inner loop's stability predicts the outer loop's
completion") — that cross-level hypothesis is real, active research, but it is
explicitly unproven and not part of anything this skill ships. This skill's job is
narrower and already-solid: help the user instrument each level independently, with its
own correct signal.
