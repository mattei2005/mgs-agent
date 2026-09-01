# Rollback wrapper import-provenance proof

Use this when a Hermes cutover claims an older checkout/launcher is the rollback route.

A wrapper shebang pointing into an old venv is not proof that the old code will run. Editable-install metadata inside that venv can point `hermes_cli` or other modules at the current active checkout; even `wrapper --version` may therefore report the active install.

## Required proof

1. Start from a neutral cwd outside every Hermes checkout.
2. Run the rollback venv's Python directly and record only non-secret provenance:
   - `sys.executable`
   - `hermes_cli.__file__`
   - package metadata version
3. Require `sys.executable` under the rollback venv **and** every critical module path under the rollback checkout.
4. Inspect the venv's editable `.pth`/finder mapping when provenance points elsewhere; do not repair it implicitly during a read-only audit.
5. Run the rollback wrapper and require its reported install directory/version to match the rollback checkout.
6. Keep old runtimes protected until one rollback path passes this independent import proof. A source tree whose venv imports the active checkout is historical storage, not a functioning rollback.
7. During candidate construction, use a dedicated venv whose editable mapping targets only the candidate. After cutover, preserve the previous active checkout plus its self-pointing venv and re-run this probe before calling rollback ready.

This proof complements launcher `readlink`, shebang, hashes, and service checks; none of those alone establish Python import provenance.
