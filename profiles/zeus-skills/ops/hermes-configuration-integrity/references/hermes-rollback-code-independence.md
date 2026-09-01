# Hermes rollback code-independence probe

Use this check before calling an older checkout a valid rollback or deleting an even older runtime.

## Invariant

A launcher with an old shebang is not proof of rollback isolation. Editable-install `.pth` metadata can make that Python import `hermes_cli` and critical modules from the active or candidate checkout. In that state, `wrapper --version` exercises the wrong code and the rollback is unusable.

## Required proof

Run the retained rollback Python directly from a neutral cwd and verify, without exposing credentials:

1. `sys.executable` is inside the retained rollback venv.
2. `hermes_cli.__file__` and every critical module inspected are inside the retained rollback checkout.
3. Package metadata/version belongs to that checkout.
4. The wrapper and an isolated one-shot smoke both exit successfully while resolving the same rollback tree.
5. The active/candidate checkout does not appear in import paths or editable mappings.

If any import resolves across checkouts, block cutover and runtime cleanup. Rebuild an isolated rollback environment, repeat the path probes and smoke, and only then reconsider deleting older runtimes. Do not repair the evidence by changing cwd or `PYTHONPATH` until the stale editable mapping has been identified; repository cwd can shadow the finder and produce false confidence.
