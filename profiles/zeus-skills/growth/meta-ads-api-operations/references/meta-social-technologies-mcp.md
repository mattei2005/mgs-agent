# Meta Social Technologies MCP — app diagnostics

## Official sources

- https://developers.facebook.com/documentation/mcp/devtools-mcp
- https://developers.facebook.com/documentation/mcp
- https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-overview
- https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

## Pilot sequence and evidence checks

1. Identify the exact Meta server and supported client, then follow the live creation form described below. Explain that ChatGPT/Codex is the client calling Meta's tools, not the owner of the Meta MCP; using an OpenAI model inside another agent does not establish client support.
2. Confirm the Facebook actor during OAuth and inspect app selection and scopes. App visibility follows the authenticated Meta profile's app roles and grants, not the ChatGPT subscriber's display name. Prefer adding the intended Meta account over replacing production app admins or campaign tokens merely to perform discovery.
3. Verify connection state, then run `devtools_app_list` through the selected connection and finish pagination. Request app name, App ID, role and granted scope. Treat a connected badge as authentication evidence only; a ChatGPT plugin's Apps count is not the Meta app inventory, and a formatted assistant table is not independent proof of the tool payload.
4. For a production-relevant pilot, resolve the target app from the current account/operation registry's `meta_app.app_id` before selecting a discovered app; never let the first discovery result stand in for the app used by Ares. An arbitrary app is acceptable only as an explicitly labeled connectivity sample, and its review/usage findings do not diagnose the campaign app. Run `devtools_app_review` status/history/privileges/requirements, `devtools_compliance` status and `devtools_api_usage` reads for that exact ID. State the returned usage interval explicitly. Continue to prohibit webhook management and test sends even when the owner deliberately retains Manage scope; a granted capability is not permission to use it in this pilot.
5. Reconcile questionable review results using the original fields separated by tool and, when necessary, the corresponding Dashboard surface. Request only the needed sanitized fields, never a full configuration or credential-bearing payload. Compare field scope before calling `UNSUBMITTED`, approval flags, privilege states and requirement messages contradictory: they can describe different submissions or resources. Compliance health does not prove permission approval, and requirements are not rejection reasons.
6. Label missing data precisely. Do not infer an hourly/daily/monthly interval from `call_quota` alone; distinguish the call-volume reporting window from the rate-limit renewal window. A zero reported volume is a value for that tool and interval, not proof that every production consumer is idle.
7. Report separately: connection established, app discovery returned, diagnostics reported, and externally reconciled facts. Keep unverified assistant summaries attributed to their source instead of silently promoting them to Meta truth.

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

## Local implementation boundary

Inspect current Zeus/Ares configuration and the relevant credential helper before describing an integration as installed or a cache as absent. Distinguish MCP client capability, configured server, authenticated connection and a successful tool call; an external ChatGPT connection does not configure Hermes or replace the production Graph API route.
