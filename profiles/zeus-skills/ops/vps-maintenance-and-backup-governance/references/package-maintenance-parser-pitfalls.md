# Package maintenance parser pitfalls

Use these guards during controlled APT and Node/Corepack maintenance.

- Validate rollback `.deb` identity with separate commands: `dpkg-deb -f file.deb Package` and `dpkg-deb -f file.deb Version`. A combined multi-field query can emit labels or a version-dependent shape; positional parsing can falsely reject a valid archive and trigger unnecessary payload fallbacks.
- For a zero-error journal gate, use `journalctl -q` or explicitly discard the informational `-- No entries --` line before counting output. Preserve the command return code separately.
- Treat `npm view --json` and `npm pack --json` as shape-variable across npm versions. Accept documented object/list variants, pack into an isolated empty directory, require exactly one `.tgz`, and verify its published shasum/integrity before installation.
- After a mutating command returns nonzero, read back the actual package/tool version before retrying; the side effect may already have succeeded.
