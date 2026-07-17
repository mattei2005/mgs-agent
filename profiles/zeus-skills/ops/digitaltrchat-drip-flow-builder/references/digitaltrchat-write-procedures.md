# DigitalTRChat write procedures — taught video workflow

> Rodolfo taught these procedures by screen recording on 2026-07-16. Zeus validated the first production write on the same date: M16 was retimed and M17 was created on page 1084 with backup, dry-run, Save, reload and independent readback. This procedure is now write-validated for narrow, explicitly authorized node edits/clones.

## A. Get-started Template and No Match Template

Route: selected segurador/profile and Page → `Action button settings`.

### Get-started

1. Click `Get-started Template`.
2. In the editor, change only the explicitly scoped fields:
   - reply message;
   - button text;
   - button type when required, normally `Web URL`;
   - Web URL, which is the M0 source URL reused by the campaign JSON button.
3. Click `Update`.
4. Reload/reopen Get-started and read back message, button text/type and exact URL.

### No Match

1. Return to `Action button settings`.
2. Click `No Match Template`.
3. Change the scoped reply message, button text/type and Web URL.
4. Click `Update`.
5. Reload/reopen No Match and read back all changed fields.
6. If the No Match URL changed, separately audit initial Auto Principal Drip block 6 because its exact destination must match No Match; never silently expand the write scope.

`Reset all action button settings to default` is destructive and must never be used in this workflow.

## B. Edit an existing Drip node

1. Back up the live graph from `JSON.parse(window.data)` before touching the canvas.
2. Select the exact node.
3. Use its right-side configuration panel:
   - `Configure New Postback`: title such as M16;
   - `Configure Button`: Button text, Button type and Web URL;
   - `Configure Text Message`: reply text, typing display and delay.
4. After changing each node, click `Done` inside that panel.
5. Clicking elsewhere without `Done` discards that node's unsaved edit.
6. After every intended node has been confirmed with `Done`, use the top-right `Save` button or `Ctrl+S`.
7. Wait for the green toast: `Success! Template has been updated successfully.`
8. Reload the builder and parse the graph again. Compare node count, targeted fields, reachability, postback names, sequence delays and all URLs against the backup. The toast proves the server accepted a save; it does not prove the graph is semantically correct.

## C. Create a new timed message by cloning

Rodolfo's demonstrated method is to clone the previous timed branch instead of dragging blank nodes from the left palette.

### Preconditions

- Confirm the requested postback, e.g. `M16`, does not already exist.
- Record the exact source branch to clone, usually the prior message such as M15.
- Record target delay, message composition, postback name, text, button label/type, URL and expected UTM.
- Back up the full graph.

### Clone the branch

For a text/button/text branch, clone the exact source nodes individually via the node context menu's `Clone` item:

1. `Sequence item`.
2. `New Postback`.
3. first Text node, commonly the arrow text `👇 👇 👇`.
4. Button node.
5. final Text message node.

The context menu places `Delete` next to `Clone`. Locate and click the exact `Clone` text; never click by position.

A branch using an image/link composition requires cloning the corresponding image/Generic Template node set instead of assuming the five-node text composition.

### Reconnect

Recreate the source branch topology exactly:

1. `New Sequence` output → cloned `Sequence item` input `Reply`.
2. cloned `Sequence item` output `Next` → cloned `New Postback` input `Reply`.
3. cloned `New Postback` output `Next` → cloned first Text/image block input `Reply`.
4. cloned first Text node output `Buttons` → cloned Button input `Reply`.
5. cloned first Text node output `Next` → cloned final Text input `Reply`.

Move the cloned nodes to a clear row below the source branch. Layout does not change behavior, but separation helps prevent editing the original nodes.

### Edit inherited values

Cloning preserves the source branch's values. Explicitly inspect and change every scoped field:

- Sequence delay;
- New Postback title, e.g. M15 → M16;
- arrow/first text if required;
- button label;
- button type;
- exact Web URL and M-number UTM/content suffix;
- final message text;
- typing display/delay.

Click `Done` after every node edit. Then Save/Ctrl+S, wait for the green success toast, reload and compare the graph to the backup.

## Historical demonstrated M16 readback — page 1084

The video itself performed and saved the demonstrated clone on `Hortensia Martínez`, internal page ID 1084. The immediate live readback after Rodolfo's video confirmed:

- graph grew from 82 to 87 nodes;
- all 87 nodes were reachable;
- M16 existed;
- M16 was connected through a five-node branch;
- M16 used 11 hours at that moment, the same delay as M15;
- its button/text/URL were inherited from M15;
- the M16 button URL carried the M15 destination/UTM suffix `drip_us_cc_m15-1`.

That state was superseded by the validated Zeus pilot below. The history remains useful as the original before-state.

## Validated Zeus pilot — page 1084

Authorized by Rodolfo in Discord message `1527466861019533434`:

- M16 changed from 11 hours to 12 hours;
- M17 created at 13 hours;
- M17 preserved M16's message, button label/type and exact URL.

Execution evidence:

- before: 87 nodes, all reachable, no M17;
- dry-run in an unsaved browser session: 92/92 reachable nodes;
- after Save/Ctrl+S and reload: 92 nodes, all reachable, no disconnected nodes;
- independent second-session readback confirmed M16=12h and M17=13h;
- added nodes: 346–350;
- no removed nodes;
- only existing nodes changed: node 25 gained the M17 Sequence connection and node 341 changed `promotional`/`promotionalText` from 11h to 12h.

The Rete editor instance is available through an existing node's Vue component, e.g. `.node-id-342.__vue__.editor`. The validated narrow clone implementation used:

1. `editor.getComponent(name).createNode(deepClonedData)`;
2. regenerate node-level `postbackId`/`uniqueId` values instead of reusing M16 IDs;
3. `editor.addNode(node)`;
4. `editor.connect(output, input)` following the canonical five-node topology;
5. `editor.toJSON()` for unsaved validation;
6. `Ctrl+S`, reload and independent inspector readback.

This internal editor path is version-sensitive. Re-inspect the Vue/editor surface before future automation; if it drifts, use the taught visual Clone/Done/Save flow instead of guessing.

A first introspection attempt reused a stale browser storage state and timed out before loading `window.data`. The reliable path is a fresh login using the 1Password item in memory, followed by direct builder navigation. Never treat a stale-state timeout as a production change.

## Routine write gate

For every real write:

1. Rodolfo must identify exact account/segurador/Page/flow/template and exact before/after fields.
2. Capture backup and sanitized baseline.
3. Abort on live drift before mutation.
4. Run an unsaved dry-run and validate node count, reachability, target timing and inherited fields.
5. No scope expansion during the write.
6. Use node-level Done or the validated Rete data update, then one global Save.
7. Validate by reload and an independent second-session readback, not toast alone.
8. Produce an exact diff of added/removed/changed nodes.
9. On mismatch, stop and restore the backup or exact original fields; do not stack fixes blindly.
