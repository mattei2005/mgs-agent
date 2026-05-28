# WP File Manager provenance audit

Use when Rodolfo asks whether Zeus/Atena installed WP File Manager or whether it was already present.

## Intent handling

If the question is provenance/accountability ("foi você que instalou?", "isso já estava aí?"), do **not** pivot into the content-production task or explain the last publication. Answer the provenance question directly after auditing evidence.

## Evidence sources, in order

1. Current WordPress state
   - WP-CLI when the site is RunCloud/SSH reachable:
     - `wp --path=<site_path> plugin list --fields=name,status,version,title --format=csv`
     - `wp --path=<site_path> eval 'echo WP_PLUGIN_DIR; echo json_encode(get_option("active_plugins"));'`
   - REST API `/wp-json/wp/v2/plugins` when using Application Password.
2. Filesystem timestamps
   - Check canonical slug directories: `wp-file-manager`, `file-manager-advanced`, `advanced-file-manager`.
   - Use `stat` with mtime/ctime/birth where available.
   - On RunCloud, direct `find` as non-owner may show permission denied; use the site owner or sudo when already authorized.
3. Operation/session history
   - Search session transcripts and local docs for `wp-file-manager`, `file_folder_manager`, `WP File Manager`, `wp_file_manager` plus the site/domain.
   - Distinguish RunCloud deploys from Bitnami/SFTP deploys: the 2026-04-23 File Manager flow was intentionally used on openzed/cliquet Bitnami/SFTP sites; RunCloud sites normally used SSH/WP-CLI/direct filesystem.
4. Agent/tool code paths
   - For content-production suspicion, inspect the relevant runner/scripts for plugin install/activate calls before blaming a REC/P1 run.
   - REC/P1 publishing should create posts/media/taxonomy/Yoast only; plugin install would be an abnormal side effect.
5. Web/server logs
   - Admin access logs may show `wp-admin/plugins.php`, `wp-json/wp/v2/plugins`, or `wp_file_manager` activity; use timestamps to correlate with session events.

## Reporting standard

Return a compact evidence table and a clear operational conclusion:

```text
Question                               | Answer
---------------------------------------|-------------------------------
Installed during current REC/P1?       | No / Yes / Not proven
Current plugin status                  | active/inactive/not installed
Slug/version                           | wp-file-manager/file_folder_manager / X
Filesystem first-seen                  | timestamp + user timezone
Best-supported provenance              | already present / installed by Zeus / manual/Rodolfo likely / unknown
```

Use confidence language honestly:
- "I did not find evidence that I installed it" when evidence is negative but not definitive.
- "Evidence shows Zeus installed it" only when transcript/tool output shows install/activate.
- "Already present before this task" when filesystem/session timing predates the current task.

## Safety posture

WP File Manager is a high-risk temporary deploy tool. If it is active and not needed, recommend deactivation/removal, but do not remove it without explicit confirmation unless the current authorized flow already includes cleanup.
