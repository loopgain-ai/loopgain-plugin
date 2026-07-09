# Dashboard hookup — a browser flow, not something this skill can automate

## Why this can't be a programmatic call

The free hosted-dashboard signup (`list=individual` in LoopGain's capture backend)
requires solving a Cloudflare Turnstile challenge, and that verification is mandatory
and fail-closed server-side — there is no bypass. A Turnstile token can only be minted
by a real browser solving the widget, so this skill cannot POST a signup on the user's
behalf. Don't try; don't fake a token.

## What to tell the user instead

After proposing wraps, ask once whether they want dashboard visibility. If yes, give
them these three steps verbatim:

1. Open **https://loopgain.ai** and use the "get free hosted-dashboard access" CTA
   (hero section or pricing section).
2. Check your email and click the confirmation link — that's the step that actually
   mints your token.
3. Set both as environment variables (don't hardcode either):
   ```bash
   export LOOPGAIN_TELEMETRY_ENDPOINT="https://telemetry.loopgain.ai/v1/aggregate"
   export LOOPGAIN_TELEMETRY_TOKEN="lgk_..."   # from the confirmation email
   ```

## What to add to each wrapped file

An inert, **commented-out** placeholder — never a live call, never a fake value:

```python
# Optional: watch this loop converge in the free LoopGain dashboard.
# 1) get a token — see https://loopgain.ai ("get free hosted-dashboard access")
# 2) export LOOPGAIN_TELEMETRY_ENDPOINT and LOOPGAIN_TELEMETRY_TOKEN (see README)
# lg.send_telemetry(
#     endpoint=os.environ["LOOPGAIN_TELEMETRY_ENDPOINT"],
#     token=os.environ["LOOPGAIN_TELEMETRY_TOKEN"],
# )
```

Left commented out so nothing sends telemetry until the user has a real token and
deliberately uncomments it — `send_telemetry` is opt-in by design; this skill preserves
that, it doesn't work around it.
