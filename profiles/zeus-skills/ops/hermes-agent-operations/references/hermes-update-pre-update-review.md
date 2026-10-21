# Read-only Hermes Change and Capability Review

## Purpose

Use for an update-worthiness decision, an explanation of applied commits, or discovery of Hermes capabilities for the company. Review evidence without installing, enabling, restarting, changing config, or silently creating a new production operating model.

## 1. Freeze the correct question and range

1. Identify the branch: prospective update decision, retrospective applied-update benefits, or enterprise capability discovery. Do not answer a retrospective question with today's moving main.
2. Resolve the deployed repo through the canonical launcher and named gateway PID/ExecStart; inherited environment and legacy checkouts are not deployment evidence.
3. For prospective review, resolve the installed upstream base and selected public target. Fetch only when permitted, complete it, then capture refs once before counting. Refresh GitHub's latest published stable release in the same observation instead of carrying forward the earlier thread's release name; a newly published release can move thousands of commits from post-release development into the stable range without changing the installed runtime.
4. For retrospective review, recover the pre-update upstream base and approved cutoff from acceptance/activation receipts or the checkpoint source. Review exactly `BASE..TARGET`, distinguish the upstream cutoff from the local MGS port commit, and keep later commits in a separate cycle.
5. Validate ancestry. Verify the official release's published, non-draft, non-prerelease status separately: `git describe` can select a nearer canary and is not stable-release proof.
6. Read official notes for crossed releases, but do not reuse their totals or advertise their entire feature window: some code may already have been installed before our update.

After resolving repo and refs, use:

```bash
git -C "$repo" rev-parse HEAD
git -C "$repo" status --porcelain=v1
git -C "$repo" merge-base --is-ancestor "$BASE" "$TARGET"
git -C "$repo" rev-list --count "$BASE..$TARGET"
git -C "$repo" diff --shortstat "$BASE" "$TARGET"
git -C "$repo" show --format=fuller --stat "$selected_commit"
```

Invoke version probes through the reconciled absolute launcher. Treat cached update banners as advisory to the Git graph. Do not invoke mutating update/plugin commands just to inspect availability.

## 2. Count completely, then inspect representative changes

Run aggregation and filtering in Python. Pass the resolved repo/base/target as arguments:

```python
import collections
import json
import re
import subprocess
import sys

repo, base, target = sys.argv[1:4]
rows = subprocess.check_output(
    ["git", "-C", repo, "log", "--format=%H%x09%s", f"{base}..{target}"],
    text=True,
).splitlines()
categories = collections.Counter()
scopes = collections.Counter()
known = {"feat", "fix", "perf", "docs", "test", "ci", "chore", "refactor", "style", "build"}
for row in rows:
    sha, title = row.split("\t", 1)
    lowered = title.lower()
    match = re.match(r"([a-z]+)(?:\(([^)]+)\))?!?:", lowered)
    if lowered.startswith("merge "):
        category = "merge"
    elif lowered.startswith("revert "):
        category = "revert"
    else:
        category = match.group(1) if match and match.group(1) in known else "other"
    categories[category] += 1
    if match and match.group(2):
        scopes[match.group(2)] += 1
assert sum(categories.values()) == len(rows)
headline = {name: categories[name] for name in ("fix", "feat", "perf")}
print(json.dumps({
    "total": len(rows), "title_prefix_counts": headline,
    "remaining": len(rows) - sum(headline.values()),
    "top_scopes": scopes.most_common(12),
}))
```

- Call these title-prefix counts, not unique features, fixed bugs or measured gains; catalogue fixes and repeated iterations inflate categories.
- Group by operational effect: continuity/delivery, compaction/context, cron reliability, skills, security, browser/tools, performance and update infrastructure.
- Inspect a few representative commit diffs per group. Exclude formatting-only, catalogue metadata and Desktop-only work from claims about live Discord agents.
- Verify a feature at the final target before advertising it; a reverted feature or catalogue entry is not deployed implementation. Locate moved symbols before concluding absence from a guessed path.
- Distinguish upstream improvements from preserved MGS customizations; a retained local guard is not a new upstream benefit.
- Label likely impact as expected unless measured in MGS. Do not convert upstream benchmarks, prompt-token reductions or estimated API cost into claimed CPU, latency or cash savings on a subscription.

## 3. Discover capabilities efficiently

1. Start at the authoritative index `https://hermes-agent.nousresearch.com/docs/llms.txt`.
2. Select only pages answering the business question, such as Kanban, Dashboard, goals, hooks/webhooks, plugins or memory/context providers.
3. Batch independent retrievals but reduce them inside `execute_code` to headings and short relevant excerpts before printing. A batch of large full pages still floods context.
4. Compare current public docs against the installed source/catalogue at the approved cutoff; label newer-docs-only capabilities rather than implying they shipped in our runtime.
5. Read selected installed `plugin-catalog/*.yaml` entries for purpose, supported platforms, requirements, capabilities and limitations. Publisher descriptions are not independent security audits.

Prefer native features that solve a company problem before extra packages. Compare each option with existing MGS skills/scripts/MCP and sources of truth; do not create a second canonical queue or memory architecture by implication.

## 4. Verify current MGS state

Read only whitelisted fields for Zeus/Atena/Ares and reduce output at the source. Never print full configs, auth documents, `.env`, MCP arguments or secret-bearing endpoints.

Inspect relevant selectors: `memory.provider`, `context.engine`, compression threshold, `plugins.enabled`, Kanban dispatch settings and curator enablement. A missing override is not proof a feature is off; consult the deployed default/resolver.

Distinguish these evidence levels for each option:

- **Available:** matching shipped source or catalogue entry exists.
- **Installed:** optional plugin/dependencies are present.
- **Configured:** settings select it.
- **Used operationally:** processes, workload records or behavior prove use.
- **Validated:** real acceptance/smoke evidence exists for that path.

Concrete checks and pitfalls:

- Inspect existing Kanban DBs with SQLite URI `mode=ro` and count tasks by status; do not invoke readers that initialize a board. An empty DB with enabled dispatch is infrastructure, not an implemented business workflow.
- Inspect Dashboard/Desktop process and deployment evidence; do not start either just to prove availability.
- Inspect the selected memory/context provider, not only directories. A file-memory guard may not cover Honcho or another external provider.
- Check explicit plugin activation and platform support. A Windows-oriented extension is not automatically suitable for a Linux VPS; a Desktop pane does not add its interface to Discord.
- Verify an observer's exact surface. Slash-command metadata is not an audit of every terminal command or production operation.
- Reuse existing trustworthy smoke evidence for an explanatory brief; label untested options instead of launching exploratory LLM runs or installing dependencies.
- Read each real profile's resolved session-pruning policy, not only the target's new default. An explicit `sessions.auto_prune: true` survives an upstream change back to opt-in and can delete history during startup, including a seemingly harmless candidate smoke. Record the current setting and its authorization, preserve the retention decision, and use synthetic/disposable profiles for preparation until backup and the applicable destructive gate are settled; never silently toggle production retention during a read-only review.
- Compare memory-provider migration and gateway multiplexing headlines against the installed base and live selectors before calling them new work. A provider may already be external, while three explicitly standalone gateways must not become one host gateway merely because the updater offers automatic migration. List only remaining adoption/port work and freeze the existing topology and provider route in the controlled plan.

## 5. Translate capabilities into company outcomes

For each useful feature, explain in plain PT-BR: what it does; one concrete MGS use case with the responsible agent/human preserved; verified current state; adoption requirements and principal cost/risk; priority and whether it complements or duplicates the existing stack.

Evaluate classes rather than automatically deploying products:

- Durable work queue: ownership, dependencies, review and evidence across agents.
- Private management panel: sessions, jobs and blockers.
- MGS-owned plugins: typed wrappers around existing authorized operations instead of core patches for every integration.
- Hooks/webhooks: respond to authenticated events without interpreting payload text as authorization.
- Persistent goals: bounded continuation with objective acceptance criteria; a model judge does not replace tests/readback or critical confirmations.
- Observability: actual tool failures, duration and tokens with access/redaction controls; traces can contain company data and cost estimates are not subscription bills.
- Context/model-routing experiments: justify with measured need and a canary, not a reflexive replacement of working Honcho, compressor or Sol defaults.

Inspect unattended execution, scratch cleanup, credential exposure and profile-write behavior before recommending automation: technically compatible defaults can violate MGS permissions and retention. Host-owned LLM access avoids giving a plugin the token, but does not make calls free; additional providers and services may consume separate credits or money.

## 6. Report the correct branch

**Prospective update decision:** installed base/version, selected target, coherent pending count, meaningful improvements, textual versus semantic port risk, and recommendation. Route execution to the controlled update workflow.

**Applied-update benefits:** exact installed range, commits-versus-features distinction, practical MGS improvements, active-versus-optional/Desktop effects, and action needed. Do not propose another update window for a completed update.

**Enterprise capability discovery:** use four sections: applied improvements; useful available-but-not-operational capabilities; optional-plugin trade-offs; short prioritized recommendation.

Use numbered topics and bullets, not raw changelogs, pipe tables or unsolicited attachments. Keep a simple version question short; expand for broader discovery. End with an operational priority, not a generic offer or installation question when the user only asked to understand. Cite official pages plus exact-range/current-state evidence. State that no plugins were installed or configurations changed by the review.

## Conditional branch: patch portability dry-run

Only run when requested or necessary for an update decision. A capability explanation does not require another staging checkout or full profile archive.

A clean tree does not imply stock Hermes. Inventory committed base-to-HEAD customizations, canonical patch/guard manifests, staged/unstaged changes and untracked paths. Use `vps-maintenance-and-backup-governance/references/git-update-delta-and-patch-portability.md` as the owner of complete-surface exported-target checks.

Create probes only in canonical profile scratch. Retain them unless exact disposal is authorized; never use automatic trap deletion or raw worktree deletion. Locate relocated symbols in the frozen target before rewriting paths. Prepare any authorized port only in an inactive candidate.

Require current reverse checks and frozen clean-target forward checks, then distinguish textual application from compile/behavior/lifecycle validation. Neither a clean tree nor a successful apply check authorizes activation.
