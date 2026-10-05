# Meta Social Technologies MCP — app diagnostics

## Official sources

- https://developers.facebook.com/documentation/mcp/devtools-mcp
- https://developers.facebook.com/documentation/mcp
- https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-overview
- https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

## Assessment rules

- Identify the exact server before recommending an integration. `https://mcp.facebook.com/devtools` is Meta Social Technologies (formerly Developer Tools); `https://mcp.facebook.com/ads` is the separate Ads MCP. Never attribute campaign/reporting tools to devtools.
- Use devtools for app settings/security, App Review, compliance, API rate limits/call volume/deprecations, webhook inventory, developer docs and changelog. It is not a replacement for Marketing API campaign reads/writes or Messenger delivery.
- Treat faster diagnosis and fewer manual Dashboard steps as potential operational benefits, not measured HTTP latency improvements. The official docs do not promise faster Graph requests, higher quotas or checkpoint bypass. Benchmark identical reads before claiming speed gains.
- Check product-level client authorization separately from transport compatibility. Hermes supports remote HTTP MCP and OAuth, but the Meta Social Technologies overview currently lists Claude Desktop/Code, ChatGPT Web, Codex App/CLI and Cursor App/CLI, says unlisted clients are unsupported, and does not list Hermes. Never spoof a supported client or promise that Hermes can authenticate. Re-check official sources for changes before a pilot.
- The service is Beta with gradual rollout. A Dashboard notification does not prove every app/user is eligible. OAuth selects apps where the user has a role; it does not grant new roles or asset access.
- Read scope exposes app diagnostics. Manage additionally allows webhook subscription creation/update/deletion. Keep a pilot read-only, filter `devtools_webhook_manage` and `devtools_webhook_test`; the latter sends a payload and can trigger real receiver behavior even without changing subscriptions.
- The docs currently say sign-in must be repeated on client restart. Verify real session persistence before recommending unattended monitoring; Hermes's general OAuth cache support does not override provider requirements.
- For a pilot, obtain authorization for the exact client/app/scope. Prefer an officially supported client first when direct Hermes support remains absent, compare the results with current Dashboard/Graph readbacks, and retain the production Graph route. OAuth/permission changes remain subject to MGS critical confirmation.

## ChatGPT setup — match the live interface

- Verify current OpenAI documentation against the user's live screenshots before naming navigation controls; Meta's setup page may retain the older Connectors path. OpenAI documents Developer mode at Settings > Security and login and MCP app creation via the plus button at https://chatgpt.com/plugins (https://developers.openai.com/api/docs/guides/developer-mode), but live Security and login / Advanced security screenshots can omit the toggle even when the sidebar shows Plugins. Treat this as an unresolved documentation/UI mismatch, not proven plan ineligibility or rollout. Inspect the visible Plugins surface next; never substitute CSP, device-code sign-in, Lockdown or account-security controls for Developer mode, weaken security, or claim a control is present without evidence.
- When the live Plugins UI already exposes “Create custom MCP server” and “Create as a plugin”, use that verified form without insisting on a missing Developer mode toggle. Set Name to Meta Social Technologies, Connection to Server URL, endpoint to https://mcp.facebook.com/devtools and Authentication to OAuth; leave optional icon/description and advanced OAuth overrides untouched unless provider discovery proves they are required. Review the trust warning and inspect Meta consent before any access grant; keep one test app at Read scope and disable webhook management and webhook test tools before a read-only pilot.

## Read-only local evidence boundary

The 2026-10-05 assessment found no Meta MCP entry in Zeus/Ares `config.yaml` and existing protected credential caching in `scripts/ares-meta-common.py`. These are dated findings, not permanent configuration guarantees. Re-read current state when diagnosing implementation or performance.
