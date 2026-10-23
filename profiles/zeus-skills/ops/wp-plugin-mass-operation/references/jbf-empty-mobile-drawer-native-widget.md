# JBF drawer opens empty: repair through WordPress widgets

Use when the JBF theme's hamburger opens a colored/blank panel even though a valid primary navigation menu exists.

1. Inspect the live DOM first. If `#jd-drawer` is empty while the click handler correctly toggles `.open`, distinguish missing drawer content from a broken JavaScript click.
2. Read the actual theme header. Some JBF versions render the desktop menu through `main-menu` but render the drawer only through `dynamic_sidebar('jbf_server_drawer')`; desktop menu assignment does not populate this sidebar.
3. Read registered sidebar, `sidebars_widgets`, `widget_nav_menu`, menu locations and exact menu items. Back up these options, theme mods and the database before mutation.
4. When the drawer is confirmed empty, create one native Navigation Menu widget pointing to the already-approved primary menu. Allocate an unused widget number, preserve all other widgets/sidebar assignments, and add only that widget to `jbf_server_drawer`. Do not rebuild the menu, hardcode links in a theme or edit JavaScript for a missing-widget problem.
5. Reconcile post-write options before retrying. Preserve the original snapshot. Under a no-file-deletion gate, skip WP Fastest Cache's automatic mutation hooks during the narrow WP-CLI write and archive only cached HTML whose old header lacks the widget, including compressed siblings. Keep backup and hashes outside the webroot.
6. Verify on the bare public URL: actual click opens and closes; all intended links have nonzero geometry and readable foreground; real link navigation reaches the expected route. Test mobile widths 320/390/430 and desktop, check horizontal overflow, and GET each destination.
7. Record the exact widget ID, primary menu ID, backup path, changed option keys and browser results. Do not claim that fixing the drawer completes unrelated SEO, content or monetization work.
