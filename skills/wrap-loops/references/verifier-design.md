# Verifier design: what makes a signal strong enough for LoopGain to act on

LoopGain is only as good as the error signal fed to `observe()`. This file is the
guidance to give users when a candidate loop's existing verifier looks weak, and the
concrete pattern to propose instead.

## Classify what actually produces the value fed to `observe()`

**Hard/measurable** — proceed normally, this is the strong case:
- Test pass/fail counts, schema-validation errors, linter/type-checker error counts.
- A numeric distance to a known target (e.g. a score against a rubric with fixed,
  external criteria).
- Exception occurrence, non-zero exit codes, contract violations.

**Soft/self-graded** — flag this to the user as the weak point in their loop, not just a
detail to wrap around:
- An LLM call grading its own (or a sibling call's) output with no independent check.
- A bare "does this look done" judgment with no concrete criteria behind it.
- Any perplexity/entropy/information-theoretic ("how surprised is the model by its own
  output") measure of convergence.

## Do not propose perplexity/entropy/MDL-based signals

This project ran a dedicated internal validation effort specifically testing whether a
model-surprise-based signal (perplexity/entropy of the generated text) could serve as a
convergence signal for loops that lack a natural hard error — the exact "semantic loop"
case. The result: no measurable improvement over simply continuing for a fixed number of
extra iterations, and the signal itself was not repeatable enough across runs of the same
task to be trustworthy. That path is closed — do not propose it, and do not imply
LoopGain has a semantic/entropy-based verifier mode. If a user asks for one, say plainly
that it's been tried and didn't hold up, rather than improvising one.

## What to propose instead, for a loop with no natural hard error

Two concrete additions, together — proposing only the first without the second is not
sufficient:

1. **Replace a vibes-based judgment with the most concrete, countable proxy available
   for the thing actually being judged.** Not "does this feel complete", but something
   with a literal count: unresolved open questions, unmet acceptance criteria, unaddressed
   TODOs, failing assertions in a checklist, number of unresolved review comments. The
   proxy doesn't have to be a perfect measure of quality — it has to be **legible and
   hard to game by construction**, which a raw "grade your own homework" call is not.

   ```python
   # Weak — self-graded, no independent check, easy to rubber-stamp:
   verdict = model.invoke(f"Is this draft done? {draft}")
   done = "yes" in verdict.lower()

   # Stronger — a concrete, countable proxy:
   open_items = extractor.find_unresolved_items(draft)   # a real, inspectable list
   error_signal = len(open_items)
   ```

2. **Add an independent adversarial-review pass whenever the result will drive a real
   decision, spend, or anything published.** A fresh-context call (no shared
   conversation/session history with the call that produced the draft) whose only job is
   to try to refute the primary judgment — not confirm it. This catches the case where
   the primary signal itself is being computed by the same process that's trying to
   satisfy it (a real, common failure mode for self-graded loops).

   ```python
   # After the primary loop converges on `open_items == 0`:
   review = independent_reviewer.refute(draft, claimed_done=True)
   if review.found_issues:
       open_items = review.issues            # don't trust the primary signal alone
   ```

   Never let a self-review pass as independent — if there's no facility for a truly
   separate call/context, label the check honestly as a self-review rather than implying
   it's adversarial.

## For nested loops

See `semantic-and-nested-loops.md` for the inner/outer relationship — the same
hard-vs-soft classification applies independently at each level. A common mistake this
step should catch: an outer loop that's "hard" only because it's reusing an inner loop's
already-hard per-step signal as if it also measured whole-task completion. That's still
a soft signal at the outer level even though the inner number itself was solid — the
outer level needs its own, genuinely task-level measure.
