---
name: kanban-workflows
description: "Use when operating Hermes Kanban task boards as orchestrator, worker, or external-agent lane owner. Covers decomposition, worker discipline, Codex lanes, reconciliation, and handoff rules."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, orchestrator, worker, codex, task-board, handoff]
    related_skills: [autonomous-coding-agents, subagent-driven-development]
---

# Hermes Kanban Workflows

## Overview
This umbrella consolidates Kanban orchestrator, worker, and Codex-lane conventions. Kanban is a task lifecycle system, not a way to bypass ownership. The current Hermes agent must always know its role, inspect the board, keep scope tight, verify work, and write explicit completion/blocking handoffs.

## Roles
| Role | Responsibility |
|---|---|
| Orchestrator | Decompose work, create cards, assign owners, sequence dependencies, and prevent premature implementation. |
| Worker | Claim one card, inspect context, implement/verify, and complete or block with evidence. |
| External lane owner | Run Codex/other CLIs as implementation inputs while Hermes keeps lifecycle, reconciliation, and verification authority. |

## Orchestrator Discipline
- Decompose by independently verifiable outcomes, not by vague activity.
- Put acceptance criteria, file paths, test expectations, and dependencies on each card.
- Avoid creating cards that require hidden context from the current conversation.
- Do not start implementing while decomposing unless explicitly acting as a worker too.

## Worker Discipline
1. Read the assigned card and surrounding board context.
2. Confirm repo/workdir and prerequisites.
3. Make the smallest complete change for that card.
4. Run targeted verification.
5. Complete with changed paths, commands run, outputs, and residual risks; or block with exact blocker and next action.

## Codex / External-Agent Lanes
Hermes owns the task. Codex is an isolated implementation lane only. Use a clean worktree/branch, pass a bounded prompt, monitor the process, inspect the diff, and run verification yourself. Do not treat Codex output as `kanban_complete`.

## Handoff Format
A good completion handoff includes:
- Task/card ID and summary.
- Files changed or artifacts produced.
- Verification commands and real results.
- Any skipped checks with reason.
- Follow-up risks or downstream cards.

## Common Pitfalls
- Creating too many micro-cards that encode one session's bug instead of a reusable task shape.
- Completing a card from an external agent's claim without diff inspection.
- Omitting acceptance criteria, causing workers to guess.
- Leaving blocked cards without a concrete unblock path.

## Verification Checklist
- [ ] Board/card state was read before acting.
- [ ] Role was clear: orchestrator, worker, or lane owner.
- [ ] Dependencies and acceptance criteria were explicit.
- [ ] Completion/blocking handoff includes evidence.
