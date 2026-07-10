## App-rate-limit channel scope (B001–B010)

The B001–B010 `app-rate-limit` channels are manager-facing, app-specific operational alert channels. Post only app-specific actionable events there: app role add/remove, token/API/rate-limit/app health, or developer/account failures for that specific app. Do **not** post Zeus internal correction/status notices, broad infra explanations, or monitor changelogs there. Keep those in Zeus/#alerts-infra or the Rodolfo thread unless Rodolfo explicitly asks for a manager-facing broadcast. See `references/app-rate-limit-channel-scope-2026-07-02.md`.
