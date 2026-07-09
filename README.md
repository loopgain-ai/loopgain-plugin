# loopgain (Claude Code plugin)

Scans your codebase for AI-agent verify-revise loops — literal `for`/`while` loops,
recursive functions, graph-topology cycles, external multi-turn harness loops, and
iterative reasoning/drafting loops — at every nesting level, and proposes
[LoopGain](https://github.com/loopgain-ai/loopgain)-wrapped rewrites one file at a time.

**Nothing is auto-applied.** Every proposed rewrite goes through Claude Code's normal
`Edit`-tool approval flow — you review and approve (or reject) each file individually.

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

## Use

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

This skill runs entirely locally, inside your own Claude Code session — it reads files
from your repo using Claude Code's own tools and never sends your code anywhere. The
only network calls it can ever trigger are the ones you explicitly approve for the
optional dashboard hookup (a link you open yourself in your browser). See
[loopgain.ai/privacy](https://loopgain.ai/privacy) for LoopGain's own privacy policy,
which covers the free hosted-dashboard service.

## Support

Questions, bugs, or feature requests: open an issue at
[github.com/loopgain-ai/loopgain-plugin](https://github.com/loopgain-ai/loopgain-plugin/issues),
or email [hello@loopgain.ai](mailto:hello@loopgain.ai).

## License

Apache-2.0, matching the `loopgain` library.
