#!/usr/bin/env bash
set -euo pipefail
[[ "${1:-}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { printf 'invalid site key\n' >&2; exit 2; }
[[ "${2:-}" =~ ^[1-9][0-9]*$ ]] || { printf 'invalid post ID\n' >&2; exit 2; }
[ -f "${3:-}" ] || { printf 'validation record missing\n' >&2; exit 2; }
SITE_KEY=$1; POST_ID=$2; RECORD=$3
jq -e --argjson id "$POST_ID" '.post_id == $id and (.slug|type=="string" and length>0) and (.score.status=="ok" or .score.status=="success" or .score.status=="OK") and (.score.seo_score|type=="number" and .>=70) and (.score.readability_score|type=="number" and .>=71)' "$RECORD" >/dev/null || { printf 'score/identity gate failed\n' >&2; exit 2; }
EXPECTED_SLUG=$(jq -r '.slug' "$RECORD")
DIR=$(cd "$(dirname "$0")" && pwd)
source "$DIR/wp-curl-auth.sh"
# This helper reruns scoring; the caller's JSON is not accepted as fresh proof.
creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds"); user=$(jq -r '.username' <<<"$creds"); pass=$(jq -r '.password' <<<"$creds")
BEFORE=$(mktemp); AFTER=$(mktemp); RESULT=$(mktemp)
http=$(wp_curl_auth_http "$BEFORE" "$user" "$pass" "$wp/wp-json/wp/v2/posts/$POST_ID?context=edit")
[[ "$http" == 200 ]] || { printf 'post preflight unavailable\n' >&2; exit 2; }
python3 /root/mgs-agent/scripts/mgs_security_boundaries.py post-identity "$BEFORE" "$POST_ID" "$EXPECTED_SLUG"
jq -e '.status=="draft" or .status=="pending"' "$BEFORE" >/dev/null || { printf 'only staged drafts can be published\n' >&2; exit 2; }
score=$(bash /root/mgs-agent/skills/content-generate-rec-p1/scripts/yoast-score-post.sh "$SITE_KEY" "$POST_ID")
jq -e '(.status=="ok" or .status=="success" or .status=="OK") and (.seo_score|type=="number" and .>=70) and (.readability_score|type=="number" and .>=71)' <<<"$score" >/dev/null || { printf 'fresh score gate failed\n' >&2; exit 2; }
http=$(wp_curl_auth_http "$AFTER" "$user" "$pass" "$wp/wp-json/wp/v2/posts/$POST_ID?context=edit")
[[ "$http" == 200 ]] || { printf 'post score readback unavailable\n' >&2; exit 2; }
python3 /root/mgs-agent/scripts/mgs_security_boundaries.py post-identity "$AFTER" "$POST_ID" "$EXPECTED_SLUG"
before_digest=$(jq -Sc '{id,slug,status,title:.title.raw,content:.content.raw,meta:(.meta|del(._yoast_wpseo_linkdex,._yoast_wpseo_content_score)),featured_media}' "$BEFORE" | sha256sum | cut -d' ' -f1)
after_digest=$(jq -Sc '{id,slug,status,title:.title.raw,content:.content.raw,meta:(.meta|del(._yoast_wpseo_linkdex,._yoast_wpseo_content_score)),featured_media}' "$AFTER" | sha256sum | cut -d' ' -f1)
[[ "$before_digest" == "$after_digest" ]] || { printf 'post changed while scoring\n' >&2; exit 2; }
http=$(wp_curl_auth_http "$RESULT" "$user" "$pass" -X POST -H 'Content-Type: application/json' -d '{"status":"publish"}' "$wp/wp-json/wp/v2/posts/$POST_ID")
[[ "${http:0:1}" == 2 ]] || { printf 'publish failed\n' >&2; exit 2; }
http=$(wp_curl_auth_http "$AFTER" "$user" "$pass" "$wp/wp-json/wp/v2/posts/$POST_ID?context=edit")
[[ "$http" == 200 ]] || { printf 'publication readback unavailable\n' >&2; exit 2; }
python3 /root/mgs-agent/scripts/mgs_security_boundaries.py post-identity "$AFTER" "$POST_ID" "$EXPECTED_SLUG"
jq -e '.status=="publish"' "$AFTER" >/dev/null || { printf 'publication not confirmed\n' >&2; exit 2; }
jq '{id,slug,status,link}' "$AFTER"
