---
name: software-development-methods
description: "Use when choosing or enforcing software work methods: root-cause debugging, TDD, disposable spikes, parallel cleanup/review, and language-specific debugger instrumentation."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [software-development, debugging, tdd, spikes, refactoring, code-review, debugger]
    related_skills: [plan, subagent-driven-development]
---

# Software Development Methods

## Overview

Class-level umbrella for software execution methods. Load this when the task is not just "edit code" but requires choosing a disciplined workflow: root-cause debugging, test-first implementation, throwaway feasibility experiments, parallel cleanup review, or interactive debugger instrumentation.

## When to Use

- A bug, flaky test, crash, regression, or unclear technical failure needs investigation.
- A feature or behavior change should be developed test-first.
- The user wants a quick spike/prototype before committing to a design.
- Recent code changes need cleanup or review by several focused perspectives.
- Async startup, sentinel-to-worker promotion, event steering, or cross-thread handoff code needs race/deadlock review.
- Console logs are insufficient and Python/Node debugger tooling is appropriate.

## Method Router

| Situation | Method |
|---|---|
| Unknown bug/root cause | Systematic debugging; see `references/absorbed-skill-md/systematic-debugging.md` |
| Behavior change or bug fix | Test-driven development; see `references/absorbed-skill-md/test-driven-development.md` |
| Feasibility unknown | Spike; see `references/absorbed-skill-md/spike.md` |
| Cleanup/reuse/perf pass | Simplify-code; see `references/absorbed-skill-md/simplify-code.md` |
| Async startup/event handoff review | Model the state machine and test controlled interleavings; see `references/async-startup-handoff-review.md` |
| Read-only security/concurrency/compatibility review of jobs, caches, or credential consumers | Trace real call sites and side effects, model unknown states fail-closed, and verify current line references; see `references/security-concurrency-regression-review.md` |
| Python process needs breakpoints/attach | `references/absorbed-skill-md/python-debugpy.md` |
| Node process needs inspector/CDP | `references/absorbed-skill-md/node-inspect-debugger.md` |

## Non-Negotiables

1. **No fixes before evidence.** For debugging, reproduce and locate root cause before changing code.
2. **For TDD, watch RED first.** A test that never failed proves little.
3. **Keep spikes disposable.** Do not silently promote spike code to production without hardening.
4. **Verify with real execution.** Tests, repro scripts, linters, or debugger output must back the conclusion.

## Verification Checklist

- [ ] Chosen method matches the task class.
- [ ] Evidence gathered before code changes when debugging.
- [ ] Tests or executable checks run after changes.
- [ ] Temporary spike/debug artifacts cleaned up or explicitly reported.
- [ ] If a normal suite/lint/build is unavailable but code was edited, run a focused ad-hoc verifier from `/tmp` using an OS-safe `tempfile` path with a `hermes-verify-` prefix, clean it up, and label the result as ad-hoc verification rather than suite green.
