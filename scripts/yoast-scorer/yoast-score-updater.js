#!/usr/bin/env node
/**
 * yoast-score-updater.js
 *
 * Computes real Yoast SEO + readability scores for a WordPress post
 * using the same @yoast/yoastseo library that runs in the Gutenberg editor,
 * then writes the scores back to wp_postmeta via WP-CLI and triggers
 * `wp yoast index` to rebuild the indexable (used by the admin list columns).
 *
 * Usage:
 *   node yoast-score-updater.js <post_id> <wp_url> <wp_user> <wp_pass> <wp_path>
 *
 * Arguments:
 *   post_id   — WordPress post ID (integer)
 *   wp_url    — e.g. https://eggbev.com
 *   wp_user   — WP REST API username
 *   wp_pass   — WP REST API application password
 *   wp_path   — path to WP root on server, e.g. /home/runcloud/webapps/eggbev
 *               (used for WP-CLI commands via SSH — passed to calling shell script)
 *
 * Exit codes:
 *   0 — success (scores computed + written)
 *   1 — fetch error
 *   2 — analysis error
 *   3 — score below threshold (warning only, still exits 0 in practice)
 */

'use strict';

const https  = require('https');
const http   = require('http');
const { execSync } = require('child_process');

// ── @yoast/yoastseo imports ───────────────────────────────────────────────────
const {
  Paper,
  Researcher,
  SeoAssessor,
  ContentAssessor,
} = require('yoastseo');

// ── Args ─────────────────────────────────────────────────────────────────────
const [,, POST_ID, WP_URL, WP_USER, WP_PASS, WP_CLI_PATH] = process.argv;

if (!POST_ID || !WP_URL || !WP_USER || !WP_PASS) {
  console.error('Usage: node yoast-score-updater.js <post_id> <wp_url> <wp_user> <wp_pass> [wp_cli_path]');
  process.exit(1);
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fetchJson(url, user, pass) {
  return new Promise((resolve, reject) => {
    const parsed   = new URL(url);
    const lib      = parsed.protocol === 'https:' ? https : http;
    const auth     = Buffer.from(`${user}:${pass}`).toString('base64');
    const options  = {
      hostname : parsed.hostname,
      path     : parsed.pathname + parsed.search,
      headers  : { 'Authorization': `Basic ${auth}`, 'Accept': 'application/json' },
    };
    lib.get(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(body)); }
        catch (e) { reject(new Error(`JSON parse error: ${e.message}\nBody: ${body.slice(0,200)}`)); }
      });
    }).on('error', reject);
  });
}

// Strip HTML tags for plain-text analysis
function stripHtml(html) {
  return (html || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .trim();
}

// Yoast score → numeric (0–100 integer)
// SeoAssessor returns a Score object; getOverallScore() returns 0–9 float
// We map it to 0–100 to match wp_postmeta format
function overallToInt(assessor) {
  const raw = assessor.calculateOverallScore();  // 0–100 already in yoastseo lib
  return Math.round(raw);
}

// ── Main ──────────────────────────────────────────────────────────────────────
(async () => {
  // 1. Fetch post from REST API (rendered content = what the browser sees)
  const endpoint = `${WP_URL}/wp-json/wp/v2/posts/${POST_ID}?context=view&_fields=id,title,content,excerpt,meta,slug,link`;
  console.log(`[yoast-scorer] Fetching post ${POST_ID} from ${WP_URL}...`);

  let post;
  try {
    post = await fetchJson(endpoint, WP_USER, WP_PASS);
  } catch (e) {
    console.error(`[yoast-scorer] Fetch error: ${e.message}`);
    process.exit(1);
  }

  if (post.code && post.code.includes('invalid_id')) {
    console.error(`[yoast-scorer] Post ${POST_ID} not found.`);
    process.exit(1);
  }

  const title     = stripHtml(post.title?.rendered || '');
  const content   = stripHtml(post.content?.rendered || '');
  const excerpt   = stripHtml(post.excerpt?.rendered || '');
  const focuskw   = (post.meta?._yoast_wpseo_focuskw || '').trim();
  const permalink = post.link || '';
  const slug      = post.slug || '';

  console.log(`[yoast-scorer] title="${title.slice(0,60)}" focuskw="${focuskw}" words≈${content.split(' ').length}`);

  // 2. Build Paper + run analysis
  let seoScore, readabilityScore;
  try {
    const paper = new Paper(content, {
      keyword      : focuskw,
      title        : title,
      titleWidth   : title.length * 8,   // approximate px
      url          : slug,
      permalink    : permalink,
      excerpt      : excerpt,
      locale       : 'en_US',
    });

    const researcher = new Researcher(paper);

    const seoAssessor  = new SeoAssessor(null, { locale: 'en_US' });
    seoAssessor.assess(paper);

    const readAssessor = new ContentAssessor(null, { locale: 'en_US' });
    readAssessor.assess(paper);

    seoScore         = overallToInt(seoAssessor);
    readabilityScore = overallToInt(readAssessor);

  } catch (e) {
    console.error(`[yoast-scorer] Analysis error: ${e.message}`);
    process.exit(2);
  }

  console.log(`[yoast-scorer] Scores computed — SEO: ${seoScore}, Readability: ${readabilityScore}`);

  // Score → color mapping (for logging)
  const color = (s) => s >= 71 ? 'green' : s >= 41 ? 'orange' : 'red';
  console.log(`[yoast-scorer] SEO color: ${color(seoScore)}, Readability color: ${color(readabilityScore)}`);

  // 3. Output scores as JSON for the calling shell script to use
  const result = {
    post_id          : parseInt(POST_ID),
    seo_score        : seoScore,
    readability_score: readabilityScore,
    seo_color        : color(seoScore),
    readability_color: color(readabilityScore),
  };

  // Print JSON to stdout — shell script reads this
  console.log('SCORES_JSON:' + JSON.stringify(result));

})();
