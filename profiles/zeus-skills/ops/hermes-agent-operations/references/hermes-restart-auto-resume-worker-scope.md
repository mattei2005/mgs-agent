# Restart auto-resume — worker scope and durable patch validation

Use when an interrupted gateway session resumes with a generic error, repeated continuation events, or a traceback inside the nested executor worker.

## Failure class

`GatewayRunner._run_agent_inner()` defines a nested synchronous `run_sync` worker. That worker receives normalized turn data such as `message`, but does **not** automatically receive the outer Discord `MessageEvent` object. Referencing `event` inside `run_sync` can compile successfully and then fail only during startup auto-resume with:

```text
NameError: name 'event' is not defined
```

`py_compile` does not catch this class because undefined names are runtime errors.

The user-facing Discord text (`Sorry, I encountered an unexpected error`) is not a root-cause signature. Different incidents can render the same generic message—for example, an ownership race and later an undefined worker-scope name. Re-open the journal traceback for every recurrence instead of assuming the previous cause returned.

A failed resume turn may intentionally leave `resume_pending` set because the interrupted work is still incomplete. If the resume branch itself is broken, every follow-up can re-enter the same bad line and emit the same error repeatedly. Diagnose both the first exception and the state-retention mechanism that explains repetition.

## Correct invariant

Detect an internal startup continuation from the explicit transport marker already carried in `message`, for example:

```python
_internal_auto_resume = bool(
    isinstance(message, str)
    and message.startswith("[Internal continuation event:")
)
```

Use that boolean throughout the nested worker. Do not reach back to an outer `event` object that is outside the worker's lexical/runtime contract.

## Diagnostic sequence

1. Read the exact journal traceback and distinguish this from provider failure or startup-agent ownership races.
2. Inspect the current source at the traceback line and the nested function signature.
3. Search the runtime, patch artifact, and patch guard for every use of the suspect variable; fixing only the live line leaves the updater able to reintroduce the bug.
4. Add a regression test that asserts the nested `run_sync` AST contains no loaded `event` name, plus behavior tests for internal continuation text consumption and chronological resume.
5. Run `py_compile`, the restart-resume test file, patch reverse-check, and patch guard.
6. Load the fix through the detached safe restart flow; never restart Zeus from an active foreground tool chain.
7. After restart, verify the service start timestamp, Discord connection, zero new matching traceback entries, and one real continuation turn.

## Durable artifact rule

A local runtime fix is incomplete until all three layers agree:

- live `gateway/run.py`;
- canonical `.patch` artifact used by controlled updates;
- `ensure-hermes-mgs-patches.sh` invariant/repair path.

When editing a unified diff manually, update hunk line counts and run both forward/reverse `git apply --check` as appropriate. A textually correct patch can still be syntactically corrupt or fail because trailing whitespace/context differs.

## Patch-guard repair pattern

For an already-patched runtime containing the bad reference, a whole-patch reapply may fail because every other hunk is already present. The guard may perform one exact, count-checked replacement of the broken marker, then verify positive invariants and explicitly reject the forbidden reference. Fail if the broken marker count is not exactly one.

## Reporting

State the actual error class and separate it from the prior incident. Report targeted tests, patch-artifact validation, current-process journal evidence, and any remaining live-traffic observation window. Do not claim that a generic user-facing interruption was a provider issue without the traceback.
