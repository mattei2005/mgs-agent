#!/usr/bin/env node
/**
 * yoast-scorer.js
 * 
 * Calcula scores SEO + Readability do Yoast para um post do WordPress
 * usando a mesma biblioteca (yoastseo) que roda no editor Gutenberg.
 *
 * Usage:
 *   node yoast-scorer.js <wp_url> <post_id> <wp_user> <wp_pass>
 *
 * Output (stdout, JSON):
 *   { "post_id": N, "seo_score": N, "readability_score": N, "status": "ok" }
 *
 * Exit codes:
 *   0 = success
 *   1 = error (JSON with "status":"error" and "message" on stdout)
 */

'use strict';

const https = require('https');
const http  = require('http');

// ── Args ──────────────────────────────────────────────────────────────────────
const [,, WP_URL, POST_ID, WP_USER, WP_PASS] = process.argv;

if (!WP_URL || !POST_ID || !WP_USER || !WP_PASS) {
  console.log(JSON.stringify({ status: 'error', message: 'Usage: yoast-scorer.js <wp_url> <post_id> <wp_user> <wp_pass>' }));
  process.exit(1);
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fetchJSON(url, auth) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    const opts = {
      headers: {
        'Authorization': 'Basic ' + Buffer.from(auth).toString('base64'),
        'User-Agent': 'mgs-yoast-scorer/1.0',
      }
    };
    mod.get(url, opts, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch(e) { reject(new Error('JSON parse error: ' + data.slice(0, 200))); }
      });
    }).on('error', reject);
  });
}

// ── Score thresholds (mirrors Yoast WP plugin) ────────────────────────────────
// SEO:         >= 71 = good (green), 41-70 = ok (orange), <= 40 = bad (red)
// Readability: >= 71 = good (green), 41-70 = ok (orange), <= 40 = bad (red)
// 0 = not analyzed (gray)

async function main() {
  try {
    // 1. Fetch post (rendered content + meta)
    const base  = WP_URL.replace(/\/$/, '');
    const url   = `${base}/wp-json/wp/v2/posts/${POST_ID}?context=view&_fields=id,slug,title,content,excerpt,meta`;
    const auth  = `${WP_USER}:${WP_PASS}`;
    const post  = await fetchJSON(url, auth);

    if (post.code && post.code.includes('invalid_post')) {
      throw new Error(`Post ${POST_ID} not found`);
    }

    const content  = (post.content  && post.content.rendered)  || '';
    const title    = (post.title    && post.title.rendered)    || '';
    const slug     = post.slug || '';
    const meta     = post.meta || {};
    const focuskw  = meta._yoast_wpseo_focuskw  || '';
    const metadesc = meta._yoast_wpseo_metadesc || '';
    const seotitle = meta._yoast_wpseo_title    || title;

    if (!content) throw new Error('Post content is empty — cannot analyze');
    if (!focuskw)  throw new Error('_yoast_wpseo_focuskw is empty — cannot calculate SEO score');

    // 2. Load yoastseo
    const { Paper, SeoAssessor, ContentAssessor } =
      require('./node_modules/yoastseo');
    const EnResearcher =
      require('./node_modules/yoastseo/build/languageProcessing/languages/en/Researcher');

    // 3. Build Paper
    const paper = new Paper(content, {
      keyword:    focuskw,
      title:      seotitle,
      titleWidth: seotitle.length,
      slug:       slug,
      locale:     'en_GB',
      description: metadesc,
    });

    // 4. Run assessors
    const researcher  = new EnResearcher.default(paper);
    const seoAssessor = new SeoAssessor(researcher);
    seoAssessor.assess(paper);
    const seoScore = seoAssessor.calculateOverallScore();

    const readAssessor = new ContentAssessor(researcher);
    readAssessor.assess(paper);
    const readScore = readAssessor.calculateOverallScore();

    // 5. Output
    console.log(JSON.stringify({
      post_id:           parseInt(POST_ID),
      seo_score:         seoScore,
      readability_score: readScore,
      focuskw:           focuskw,
      slug:              slug,
      status:            'ok'
    }));

  } catch(err) {
    console.log(JSON.stringify({ status: 'error', message: err.message }));
    process.exit(1);
  }
}

main();
