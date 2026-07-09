# Literal-loop detection heuristic

## Phase A regex (shortlist only)

Loop-construct signal (any of):
```
max_iter|max_iteration|max_retries|max_steps
for\s+_?\w*\s+in\s+range\(
while\s+True
while\s+\w+\s*[<>]=?\s*\w*max
```

LLM-call / revise-verify signal (any of):
```
messages\.create\(
chat\.completions
\.invoke\(
\.kickoff\(
graph\.stream\(
create_react_agent
AgentExecutor
revise\(
verify\(
critique
self_correct
```

A file only becomes a candidate for Phase B if it matches **at least one from each
group**. This is deliberately loose — Phase A exists to build a shortlist to *read*, not
to make a final decision. Over-matching here is fine; under-matching means missing a
real loop.

## Phase B judgment — genuine loop vs. false positive

Read the shortlisted file (or the enclosing function, if the file is large) and ask: is
this code calling an LLM repeatedly, checking its output/error each time, and continuing
until some condition or fixed count is reached?

**Genuine examples:**
```python
for i in range(max_iterations):
    output = generate(prompt)
    errors = verifier.check(output)
    if not errors:
        return output
    prompt = revise_prompt(prompt, errors)
```
```python
while True:
    draft = model.invoke(state)
    score = judge.evaluate(draft)
    if score > 0.9:
        break
    state = refine(state, draft, score)
```

**False positives — do not classify these as loops:**
```python
for i in range(10):          # no LLM call in the body — a plain data loop
    total += data[i]
```
```python
for chunk in response.iter_lines():   # streaming a single response, not
    print(chunk)                       # repeating a generate+verify cycle
```
```python
for doc in documents:        # batch processing N independent items, not
    result = model.invoke(doc)   # one item being iteratively refined
    results.append(result)
```
The distinguishing question: is the SAME piece of work being refined across iterations
(loop), or are independent items each getting one pass (batch/map, not a loop LoopGain
can help with)?

When in doubt, prefer under-classifying to forcing a wrap onto code that isn't really an
iterative verify-revise loop — a wrong classification here produces a nonsensical
rewrite, which is worse than skipping a real candidate that gets caught on a future scan.
