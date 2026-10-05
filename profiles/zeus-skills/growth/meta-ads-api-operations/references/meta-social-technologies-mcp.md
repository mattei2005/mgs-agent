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

- Verify the current OpenAI client documentation and the user's screenshot before naming navigation controls; Meta's setup page may retain the older Connectors path. For the interface showing Security and login plus Integrations > Plugins, current OpenAI guidance places Developer mode at Settings > Security and login, then creates the MCP app via the plus button at https://chatgpt.com/plugins. Source: https://developers.openai.com/api/docs/guides/developer-mode. Re-check for UI changes rather than inferring a missing entitlement from the absent Connectors label.
- Keep the Meta endpoint https://mcp.facebook.com/devtools with OAuth and one test app at Read scope; disable webhook management and webhook test tools before a read-only pilot.

## Read-only local evidence boundary

The 2026-10-05 assessment found no Meta MCP entry in Zeus/Ares `config.yaml` and existing protected credential caching in `scripts/ares-meta-common.py`. These are dated findings, not permanent configuration guarantees. Re-read current state when diagnosing implementation or performance.
