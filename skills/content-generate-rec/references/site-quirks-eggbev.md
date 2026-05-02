# Site quirks - eggbev.com (jbf-wp-theme-main)

Reference loaded ON DEMAND quando Atena esta publicando em eggbev.com.
Carregada via `view references/site-quirks-eggbev.md`.

---

## Theme HTML sanitization (CRITICAL)

The `jbf-wp-theme-main` theme used on eggbev applies aggressive `wp_kses`
filtering at render time. Inside `<!-- wp:html -->` blocks, it strips:

- `<div style="...">` - inline style removed, div may also be removed
- `<div class="...">` - the div element itself is removed from output
- `<style>` tags - removed entirely

The HTML saves correctly to the database but is sanitized on page render.
This means you CANNOT add responsive wrappers or scoped CSS inside `wp:html`.

**What survives inside wp:html:** native table elements (`<table>`, `<thead>`,
`<tbody>`, `<tr>`, `<th>`, `<td>`), and their standard attributes.

**Where to put global CSS:** Customizer -> Additional CSS (`Aparencia ->
Customizar -> CSS Adicional`) - this is injected into `<head>` by WordPress
itself, before the theme's `wp_kses` filter runs, so it is safe. Any CSS
that needs to affect post content (e.g. responsive table overflow) must go
there. Example for responsive tables on all posts:

```css
.jd-post-content table {
  display: block;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  max-width: 100%;
}
```

This requires manual action in the WP admin panel (cannot be applied via
REST API on this site - the `/wp/v2/custom_css` and global-styles endpoints
are not available for this classic theme).

---

## Comparative Table - use wp:table block (not wp:html)

When inserting a Comparative Table in REC articles for eggbev, ALWAYS use the
native Gutenberg `<!-- wp:table -->` block wrapped in `<figure class="wp-block-table">`.

This is the ONLY format that receives the theme's `overflow-x: auto` on mobile.
Do NOT use `<!-- wp:html -->`, which the theme sanitizes and strips the wrapper.

HTML must be compact (no indentation, no line breaks between tags).

Example:
```
<!-- wp:table -->
<figure class="wp-block-table"><table class="has-fixed-layout" style="font-size:85%"><thead><tr><th>...</th></tr></thead><tbody><tr><td>...</td></tr></tbody></table></figure>
<!-- /wp:table -->
```

---

## REST /posts?slug= broken on eggbev

Symptom: `GET /wp-json/wp/v2/posts?slug=<existing-slug>&status=any` returns []
even when the slug exists. Affects both auth and unauth requests.

Suspected cause: Plugin interference in `rest_post_query` filter hook
(likely Rank Math SEO, Wordfence, or theme functions).

Workaround: `check-slug-conflict.sh` already handles this fail-closed.
The script may emit `WARN posts_query_zero_results` - this is expected on
eggbev and does not block publishing.

Detection: look for these WARN entries in `/root/mgs-agent/logs/publish-wordpress.log`.
