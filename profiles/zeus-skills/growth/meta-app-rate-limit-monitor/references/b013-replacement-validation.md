# B013 replacement validation pitfalls

Use alongside route-pack-05 replacement gates, not as a broader authorization.

- When the exact replacement title and fresh `/me` agree but a non-secret principal-profile note still names the predecessor, correct only that exact profile line in the same item. Preserve every other field by in-memory before/after equality and exact-item readback. Never repair credential values under this metadata exception.
- Tie the current-generation regression to the single active B013 registry entry instead of a historical suffix, so approved replacements do not leave stale assertions. Preserve the immutable item ID and dedicated channel checks.
- Run regressions with the dedicated runner's interpreter. For full DTR cycles exceeding the foreground transport window, use a silent tracked process and consume its result before closure or another writer. A wait-window timeout is not an operation failure; a terminated foreground canary requires absence-of-writer/readback before safe retry.
