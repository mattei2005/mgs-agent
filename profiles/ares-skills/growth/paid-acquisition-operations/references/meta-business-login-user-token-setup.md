# Facebook Login for Business — User-token setup

Use this reference when configuring Meta Facebook Login for Business to let multiple advertiser profiles authorize the same corporate app and produce separate User Access Tokens.

## Interactive procedure

1. Open the intended app in Meta for Developers and read back the app name, type, mode, attached Business Portfolio, and verification status. Do not change the Live/Development state and never open or expose App Secret.
2. Expand **Facebook Login for Business**. Navigate to **Configurations**; do not edit the unrelated **Settings** page or its redirect URI fields merely to reach the configuration wizard.
3. Select **Create configuration**, not **Create from template**, when building the advertiser authorization flow manually.
4. Use a stable functional name that describes the shared purpose rather than an individual manager, for example `MGS Advertiser OAuth`.
5. Select the **General** login variation for the standard Facebook Login for Business flow. Treat immutable-choice warnings as a stop point: verify the selection visually before advancing.
6. When the intended architecture is one token tied to each personal advertiser profile that logs in and authorizes the app, select **User access token**. Do not select **System-user access token** merely because advertising assets need ongoing operational access; that option changes the authorization identity to a business portfolio/system user.
7. Continue through later Assets and Permissions screens only after inspecting each live screen and confirming the exact available choices. Do not infer provider options from an older UI or advance past an unverified irreversible choice.
8. After a configuration has just been created and its choices were visually read back during the wizard, treat that readback as sufficient. Do not ask the operator to reopen **Edit** merely to reconfirm the same choices; return to Edit only when a specific field must be corrected or evidence is genuinely missing.

## Operator-facing cadence

- Issue exactly one atomic action per response.
- Include the exact label to click or exact value to enter.
- Explicitly name the nearest wrong option when confusion would be costly.
- Ask for a screenshot when the visible page, exact choices, ownership, permissions, status, or error determines the next action; otherwise accept the operator's explicit confirmation and continue without duplicate proof.
- Inspect every screenshot that is provided before confirming completion. A successful click alone is not evidence that the intended page opened, but a clear confirmation of a binary state such as “approved” does not require reopening the screen.
- If the screenshot remains on the prior submenu, say so plainly and repeat only the missing navigation action.

## Security and architecture guardrails

- One corporate app can serve multiple advertiser profiles; do not prescribe one app per manager by default.
- Keep each resulting User Access Token isolated in the approved credential store and never paste it into chat.
- App conversion, permission expansion, production publishing, and changes to callback URLs are distinct writes; do not fold them into navigation guidance or execute them without the applicable approval and readback.
- Do not treat a redirect URI merely displayed in the app as an intentional or usable MGS callback. Confirm who set it, validate DNS/HTTPS and the authorization-code handler, and treat inherited/default or unexplained URIs as legacy until replaced through an authorized callback setup.
