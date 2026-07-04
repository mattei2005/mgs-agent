# SB Utility global rollout + cron review lessons — 2026-07-02

## Trigger

Rodolfo expanded the SB Utility rollout from the original 59 templates to **all active/non-test/non-NAO-USAR Broadcast Templates** in the SmartBidding dashboard, while keeping explicit test/NAO-USAR templates untouched.

## Durable workflow

1. **Always start from live dashboard/API.**
   - For SB dashboard questions, do not answer from cached snapshots or prior CSVs.
   - Use headed/Xvfb Playwright and capture live `/broadcast/Messenger` and `/campaigns/Messenger` responses.
   - For Messenger Page scope, validate the full intended set: `Digital trust` + `Digital trust 2` child publishers. A partial 45-site capture returns stale/incomplete page counts.

2. **Separate Broadcast Template `PAGES` from Page-table reality.**
   - `/broadcast/Messenger` may show a `PAGES` value that is stale or not confirmed by Page rows.
   - For operational “tem página conectada?” answers, join live `Broadcast Template.NAME` against live Page rows by `BROADCAST_TEMPLATE_NAME` and report that count.
   - Example correction: `teste-4-us-cc-es-all-201-zero-width-2chars-approval` showed `PAGES=1` in Broadcast raw, but live Page join showed `0`; answer should be `0 pages live`.

3. **Global Utility rollout inclusion rule.**
   - Include every live Broadcast Template except explicit `NAO USAR` and `teste-*` templates listed by Rodolfo.
   - Keep excluded templates untouched: no message rewrite, no approval run, no schedule edit, no tracker progression.
   - Add newly included active templates to `data/sb-utility-rollout-tracker.json` with current message count as `active_target`, current live Page count, source bank backup path, and next analysis due based on ETA.

4. **Cron review-only contract.**
   - `sb-utility-rollout-cron.sh` runs `sb-utility-rollout-manager.py review-due` and may create a local output even if delivery does not appear in Discord.
   - If Rodolfo says the expected cron report did not arrive, check Hermes cron output under profile cron output, e.g.:
     `/root/.hermes/profiles/zeus/cron/output/<job_id>_<timestamp>.txt`
   - Also check the actual rollout log under:
     `/root/mgs-agent/logs/sb-utility-rollout-YYYYMMDD-HHMMSS.json`
   - If the cron is script-only/no_agent and the report must be follow-up-discussable, ensure the cron has `deliver=origin` and `attach_to_session=true`.

5. **Approval/run sequence.**
   - Review-only output is not an application. It is a proposal for Rodolfo approval.
   - Once Rodolfo approves, run controlled apply with `run-due` or equivalent production-safe path, then validate live counts from `/broadcast/Messenger`.
   - Report: number of templates in tracker, excluded count, counts by message target, missing-in-SB count, and log path.

## Pitfalls observed

- Mixing live dashboard with snapshots creates wrong page counts and erodes trust. Treat snapshots only as historical support, never final evidence for SB.
- A successful cron run can still fail to visibly deliver if delivery/thread attachment is wrong; local cron output is evidence of what happened.
- Do not assume “PAGES” in Broadcast Template equals connected pages. Page-table join is the real operational source for connected pages.
- After adding new templates to the tracker, do not immediately mutate excluded/test templates. Exclusion list wins.

## Useful files from the session

- Live inventory CSV pattern: `work/meta-utility/live-check-YYYYMMDD-full/templates-live-pages.csv`
- Tracker: `data/sb-utility-rollout-tracker.json`
- Cron wrapper: `scripts/sb-utility-rollout-cron.sh`
- Manager: `scripts/sb-utility-rollout-manager.py`
- Rollout logs: `logs/sb-utility-rollout-*.json`
