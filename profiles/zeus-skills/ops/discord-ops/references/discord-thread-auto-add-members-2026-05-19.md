# Session note — Restore Atena thread auto-add members (2026-05-19)

## Context

Rodolfo pointed to thread `1506185551840284752` and asked what was wrong. Import showed the thread was created by Atena, renamed successfully, and answered correctly, but only had two members: Atena + Rodolfo. Raquel was missing.

## Evidence shape

```text
Thread ID     | 1506185551840284752
Parent        | #atena-content-agent / 1496267571543019653
Owner         | Atena / 1496306920494202950
member_count  | 2 before repair; 3 after manual add
Missing user  | Raquel Oliveira / 1496254952501280974
```

The apparent `[sem texto]` message was the Discord technical thread-reference/creation event, not the bug. The rename event message was also normal.

## Root cause

The current Atena `channel_prompts` only performed rename-on-create. The older bootstrap behavior that discovered/added members had been removed during prompt slimming. Hermes core auto-thread creates the thread but does not add arbitrary additional members by default.

## Applied repair pattern

1. Patch Atena `channel_prompts` to keep `rename-on-create, then freeze` but include an auto-add bootstrap for new threads only.
2. Include explicit required thread users:
   - Raquel Oliveira: `1496254952501280974`
   - Rodolfo Mattei: `344196393512075265`
3. Bootstrap uses one `execute_code` script:
   - `PATCH /channels/{THREAD_ID}` to rename.
   - `PUT /channels/{THREAD_ID}/thread-members/{USER_ID}` for each required user.
4. Patch both live and versioned configs:
   - `/root/.hermes/profiles/atena/config.yaml`
   - `/root/mgs-agent/profiles/atena-config.yaml`
   - same pattern for Zeus config, but Zeus currently only requires Rodolfo.
5. Validate YAML.
6. Restart affected gateway (`atena-gateway`) and confirm `Connected as Atena#2956` + `Gateway running with 1 platform(s)`.
7. For the already-created broken thread, manually add Raquel with the same `PUT thread-members` endpoint and verify count changed to 3.

## Durable lesson

For MGS agent threads, “people who are inside the channel” should be implemented as an explicit per-agent membership policy, not a broad guild/channel scrape. For Atena/content threads that means Raquel + Rodolfo. This avoids accidentally adding unrelated guild members while preserving the operational expectation that Raquel sees Atena work threads.
