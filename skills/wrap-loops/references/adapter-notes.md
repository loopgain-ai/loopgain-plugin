# Framework adapters — always read the installed source, this is a reminder not a spec

Before writing any adapter-specific rewrite, locate the installed package
(`python -c "import loopgain, os; print(os.path.dirname(loopgain.__file__))"` or
`pip show -f loopgain`) and read the real file at
`loopgain/integrations/<name>.py`. The signatures below are reminders of shape, current
as of `loopgain-core`'s source at the time this plugin was written — they can drift.
**If the installed version's constructor differs from what's shown here, trust the
installed source, not this file.**

## LangGraph — `loopgain/integrations/langgraph.py`

```python
LangGraphAdapter(lg: LoopGain, error_fn: ErrorFn, stream_mode: str = "updates")
```
Wraps a compiled graph exposing `stream()`/`astream()`. Each step yielded by
`graph.stream(input, stream_mode="updates")` is one iteration: `error_fn` is called with
the per-step update dict, the returned magnitude feeds `observe()`.

## CrewAI — `loopgain/integrations/crewai.py`

```python
CrewAIAdapter(lg: LoopGain, step_error_fn: Optional[CrewStepFn] = None, task_error_fn: Optional[CrewTaskFn] = None)
```
Requires at least one of `step_error_fn` (fires per agent thought/step) or
`task_error_fn` (fires once per completed Task) — raises `ValueError` if both are
`None`. Installs via `adapter.install(crew)`, not a constructor-time hookup.

## AutoGen (v0.4+) — `loopgain/integrations/autogen.py`

```python
AutoGenAdapter(lg: LoopGain, error_fn: MessageErrorFn, observe_sources: Optional[set[str]] = None)
```
Async. Drives `team.run_stream(task=...)` via `adapter.run(team, task, cancellation_token=...)`.
In a typical verify-revise pattern the Team is a 2-agent rotation
(generator → verifier → generator); the verifier's message carries the error signal.

## LangChain — `loopgain/integrations/langchain.py`

```python
LangChainAdapter(lg: LoopGain, error_fn: ErrorFn)
```
Wraps any agent exposing `stream()`/`astream()` (works with both
`langchain.agents.create_agent()` and older AgentExecutor-style agents). Same
per-chunk-is-one-iteration model as the LangGraph adapter.

## OpenAI Agents SDK — `loopgain/integrations/openai_agents.py`

```python
OpenAIAgentsAdapter(lg: LoopGain, error_fn: EventErrorFn, observe_event_types: Optional[set[str]] = None)
```
Async-first (`adapter.run(agent, input, **run_kwargs)`); a `run_sync` helper wraps it
with `asyncio.run` for synchronous call sites. Drives
`Runner.run_streamed(agent, input)`; `stream_events()` yields several event kinds —
`observe_event_types=None` means observe every event.

## Claude Agent SDK — `loopgain/integrations/claude_agent_sdk.py`

```python
ClaudeAgentSDKAdapter(lg: LoopGain, error_fn: MessageErrorFn, observe_message_types: Optional[Tuple[type, ...]] = ())
```
Async-only, wraps `query(prompt=..., options=...)`'s async message iterator
(`UserMessage`/`AssistantMessage`/`SystemMessage`). The empty-tuple default is a sentinel
for "use the SDK's default message types" — distinct from `None`, which means "observe
everything." Preserve that distinction if proposing a rewrite that touches this param.

## If no framework matches

Fall back to the raw API from the README — always correct, never adapter-specific:
```python
from loopgain import LoopGain

lg = LoopGain(target_error=0.1)
while lg.should_continue():
    errors = verifier.verify(output)
    lg.observe(errors, output=output)
    output = reviser.revise(output, errors)

result = lg.result
```
