# Joint MCP/performance activation — prepared, not yet executed

Authority Rodolfo message 1555642186169716877, thread 1555572634228490283.

Order Ares → Atena → Zeus. Canonical detached finalizer prepared from mgs-gateway-restart-safe.sh, exact ordering checked. Full frozen snapshot has 61 targets, including all modified runtime files, three configs, shared helpers, skills and external supervisor/smokes. No runtime/config frozen target will be edited after preparation.

Preflight:671 canonical regressions,83 performance-focused tests;3 actual profile browser DOM/config smokes;3 real subscription model responses; all passed. Native-browser harness initially queried an unloaded fixture; wait_for_load plus exact supervisor/canonical test-session cleanup fixed the harness, and all three profiles passed. Procedure saved in Zeus browser-performance-admission-budget.md and exact mirror verified. No protected session or production Page was modified.

Canonical finalizer: /root/mgs-agent/data/mgs-gateway-restart-finalizer-20261002T182455Z-2419710.sh
Snapshot: /root/mgs-agent/data/mgs-gateway-restart-snapshot-20261002T182455Z-2419710.sha256
External supervisor: /root/mgs-agent/work/joint-activation-1555642186169716877/activation-supervisor.py
Validation plan: readiness/new PIDs, native Hostinger5GET/batch/deny/fixedVM,3 profile rendered browser smokes,3 real model responses,full snapshot/crontab readback,inventory/checkpoints and canonical REPORT-INFRA, then executive callback to origin with exact message readback.

This preparation is not an activation-success claim. No VPS reboot, credential/firewall/billing change, schedule migration or production throughput speedup is included.
