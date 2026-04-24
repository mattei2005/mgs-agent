#!/usr/bin/env node
/**
 * yoast-score-updater.js
 *
 * Fetches a WordPress post via REST API, runs Yoast SEO + Readability analysis
 * using the @yoast/yoastseo library (same engine as Gutenberg editor),
 * and outputs scores as JSON to stdout.
 *
 * Usage: node yoast-score-updater.js <post_id> <wp_url> <wp_user> <wp_pass>
 *
 * Output (stdout, JSON):
 *   { "seo": 72, "readability": 85, "seo_color": "green", "read_color": "green" }
 *
 * Exit codes: 0 = success, 1 = error
 */

'use strict';

const https = require('https');
const http  = require('http');

// ─── helpers ────────────────────────────────────────────────────────────────

function scoreColor(score) {
  if (score === null || score === undefined) return 'notAnalyzed';
  if (score >= 71) return 'green';
  if (score >= 41) return 'orange';
  return 'red';
}

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

function fetchJson(url, user, pass) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const options = {
      hostname: parsed.hostname,
      port:     parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path:     parsed.pathname + parsed.search,
      method:   'GET',
      headers: {
        'Authorization': 'Basic ' + Buffer.from(`${user}:${pass}`).toString('base64'),
        'Accept':        'application/json',
      },
    };
    const lib = parsed.protocol === 'https:' ? https : http;
    const req = lib.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error(`JSON parse error: ${e.message}\nBody: ${data.slice(0, 200)}`)); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

// ─── main ────────────────────────────────────────────────────────────────────

async function main() {
  const [postId, wpUrl, wpUser, wpPass] = process.argv.slice(2);

  if (!postId || !wpUrl || !wpUser || !wpPass) {
    process.stderr.write('Usage: node yoast-score-updater.js <post_id> <wp_url> <wp_user> <wp_pass>\n');
    process.exit(1);
  }

  // 1. Fetch post data
  const apiUrl = `${wpUrl.replace(/\/$/, '')}/wp-json/wp/v2/posts/${postId}?_fields=id,slug,link,title,content,excerpt,meta`;
  let post;
  try {
    post = await fetchJson(apiUrl, wpUser, wpPass);
  } catch (e) {
    process.stderr.write(`Failed to fetch post ${postId}: ${e.message}\n`);
    process.exit(1);
  }

  if (post.code) {
    process.stderr.write(`WP API error for post ${postId}: ${post.message}\n`);
    process.exit(1);
  }

  // 2. Extract fields
  const meta        = post.meta || {};
  const keyword     = meta._yoast_wpseo_focuskw   || '';
  const seoTitle    = meta._yoast_wpseo_title      || (post.title && post.title.rendered) || '';
  const metaDesc    = meta._yoast_wpseo_metadesc   || (post.excerpt && stripHtml(post.excerpt.rendered)) || '';
  const bodyHtml    = (post.content && post.content.rendered) || '';
  const slug        = post.slug || '';
  const permalink   = post.link || `${wpUrl}/${slug}/`;

  // 3. Load Yoast modules
  const { Paper, assessors } = require('yoastseo');
  const { SEOAssessor, ContentAssessor } = assessors;
  const EnResearcher = require('./node_modules/yoastseo/build/languageProcessing/languages/en/Researcher.js').default;

  // 4. Build Paper
  const paper = new Paper(
    stripHtml(bodyHtml),
    {
      keyword,
      description : metaDesc,
      title       : seoTitle,
      titleWidth  : Math.min(seoTitle.length * 8, 600), // rough px estimate
      slug,
      permalink,
      locale      : 'en_US',
    }
  );

  // 5. Run assessors (suppress internal Yoast Trace logs to stderr)
  const origWarn = console.warn;
  console.warn = () => {};

  const researcher = new EnResearcher(paper);

  const seoAssessor = new SEOAssessor(researcher);
  seoAssessor.assess(paper);
  const seoScore = seoAssessor.calculateOverallScore();

  const readAssessor = new ContentAssessor(researcher);
  readAssessor.assess(paper);
  const readScore = readAssessor.calculateOverallScore();

  console.warn = origWarn;

  // 6. Output
  const result = {
    post_id      : parseInt(postId, 10),
    seo          : seoScore,
    readability  : readScore,
    seo_color    : scoreColor(seoScore),
    read_color   : scoreColor(readScore),
    keyword,
    slug,
  };

  process.stdout.write(JSON.stringify(result) + '\n');
  process.exit(0);
}

main().catch(e => {
  process.stderr.write(`Unhandled error: ${e.message}\n`);
  process.exit(1);
});
