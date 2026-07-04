# REPORT-INFRA: fixed Discord thread routing for cron/checkpoint reports — 2026-06-19

Context: Ares/Openzed-Elena cron reports originally created a new Discord thread for each checkpoint in `#logs-aquisicao`, creating excessive thread list noise. Rodolfo approved consolidating normal alerts/checkpoints into one fixed operational thread while keeping incident/structural-change threads separate.

## Durable pattern

For script-only cron wrappers that post Discord reports:

1. Add/validate a poster mode that accepts an existing thread/channel ID, e.g. `--thread-id <thread_id>`.
2. In dry-run, require structured output showing:
   - `mode=post_existing_thread`
   - `channel_id=<parent channel>`
   - `thread_id=<fixed thread>`
3. Validate the target thread via Discord API using the bot token of the agent that will post:
   - `GET /channels/<thread_id>` returns HTTP 200
   - `parent_id` equals the expected parent channel
   - `thread_metadata.archived=false`
   - `thread_metadata.locked=false`
4. Validate wrapper syntax (`bash -n`) and poster syntax (`py_compile`), then secret-scan the poster/wrappers/skill for obvious token literals.
5. For profile-local wrappers under `/root/.hermes/profiles/<agent>/scripts/`, record SHA/size/mtime in `infra-inventory.json` but do not try to git-add the runtime path.
6. If a profile skill/runbook was updated, sync or copy the runtime skill into `/root/mgs-agent/profiles/<agent>-skills/...`, compare runtime/versioned SHA, and commit only the mirrored skill plus inventory and repo script.
7. Register a `runtime_artifacts[]` entry like `ares-openzed-elena-fixed-operational-thread` with channel/thread/status metadata so future audits know the fixed route is intentional.

## Operational split

Use the fixed operational thread for:
- normal Openzed/Elena checkpoints;
- dry-run recommendations without incident-level anomaly;
- recurring status that would otherwise create thread spam.

Create a separate thread only for:
- technical incident or gateway failure;
- budget/structure/write change requiring explicit approval;
- replacement/creative investigation that needs its own artifact trail;
- critical anomaly requiring push/isolated decision.

## Validated evidence shape

```text
py_compile OK
bash -n OK
poster dry-run: mode=post_existing_thread thread_id=<id>
GET Discord thread: status=200 parent_id=<logs-aquisicao> archived=false locked=false
sha256 poster=<sha> wrappers=<sha1>,<sha2>,<sha3>
```

## Pitfalls

- Do not rely on Hermes scheduler `deliver` to create or choose the right thread for script-only jobs. The wrapper/poster should route the message explicitly and leave stdout controlled/empty as designed.
- Do not validate the thread with Zeus token if Ares is the poster. Use the posting agent's token; access can differ by bot.
- Do not convert all alerts to the fixed thread. High-risk or approval-heavy items need separate threads for auditability and push discipline.
- Do not commit runtime wrappers outside `/root/mgs-agent`; represent them in inventory with hashes instead.
