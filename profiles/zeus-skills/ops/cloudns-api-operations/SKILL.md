---
name: cloudns-api-operations
description: "Use when operating ClouDNS API. Verify scope and exports."
version: 1.0.0
author: Zeus MGS
license: Proprietary
metadata:
  hermes:
    tags: [cloudns, dns, geodns, onepassword, export]
---

# ClouDNS API operations

## When to Use

Use for authorized ClouDNS API setup, authentication checks, exact-zone DNS/GeoDNS inspection and verified record exports.

## Scope and prerequisites

Read `/root/mgs-agent/context/cloudns.md` for the currently approved credential route and authority. Full API-user capability is not blanket write authorization. Keep export/inspection read-only; DNS/security/credential/permission changes retain canonical confirmation gates. Never test access by modifying a DNS record.

Load `onepassword-service-account-vault-operations` for secret handling. Resolve the exact item through `/root/mgs-agent/scripts/mgs-op-with-service-account.sh`. Select by approved vault, title, username and exact API field labels `auth-id` and `auth-password`. A web-login password is not the API password. If a stored item ID stops resolving, rediscover bounded metadata rather than assuming the credential is unavailable or selecting a same-title item in another vault. Keep secret fields only in process memory, never argv, plaintext artifacts, logs or chat. Preserve literal credential values and reject malformed identifiers; do not trim or repair credential tokens.

Use the fixed official API base `https://api.cloudns.net/`, not untrusted free-text metadata as a destination. A trailing newline in an auxiliary URL field is not an authentication failure and is not permission to modify the 1Password item.

## Authenticate and match the allowed transport

Send parameters in HTTPS POST bodies. First call `login/login.json` and require HTTP 200 plus provider `status=Success`; HTTP 200 alone is insufficient. Then call `ip/get-my-ip.json` and compare the provider-observed source IP with the approved allowlist.

An IPv4 egress lookup does not prove that the ClouDNS client will use IPv4. If the provider explicitly rejects an unallowed IPv6 source while the existing allowlist permits the verified IPv4, constrain only this client/process to AF_INET and repeat login/IP verification. Do not change system networking, disable IPv6 globally, expand the allowlist or rotate credentials. For urllib, a short-lived single-purpose process may wrap socket.getaddrinfo to resolve AF_INET; do not apply that monkeypatch to an agent daemon. Stop and escalate if the approved IPv4 also fails. Preserve exact redacted provider diagnostics; never print request bodies.

## Read and export

- `dns/records.json`: `domain-name=<exact zone>`, `rows-per-page=100`, `page=<n>`, `include-notes=1`; do not filter by type or host when exporting the whole zone.
- Persist each page to a task-private JSON file, deduplicate/count by record ID in code, reject conflicting IDs and stop only on a verified final page. Compare a second independent complete read; if the zone changed concurrently, reconcile the snapshot instead of silently merging it.
- `dns/soa-details.json`: retrieve generated SOA metadata separately. Do not inflate the user-managed record count by silently counting SOA as a listed record.
- Preserve every returned record field, including exact host/value, TTL, status, GeoDNS location/code/name and failover metadata. Keep GeoDNS conditions associated with each record.
- The official BIND export `dns/records-export.json` explicitly excludes GeoDNS. Do not call a human-readable JSON-backed TXT a BIND-importable file. The records-list documentation has a generic master-zone caveat yet describes GeoDNS fields; exercise the exact approved zone and report the actual result, not an assumed capability.
- Format the requested TXT as an inventory with zone, timestamp, record count, readable record headings and full original JSON fields. State that it is not an import-ready BIND file. Check all credential-bearing fields from the 1Password item are absent from the generated artifact, verify the number of record blocks, and generate/check SHA-256 in shell/Python.
- Attach only when requested. Report the exact record count, separately retrieved SOA, any missing data, and whether DNS changes occurred.

## Institutional continuity

Persist nonsecret access receipts and the canonical credential pointer, not credential values. Store manually curated capability/provider entries in the inventory's preserved `runtime_artifacts` list, not a new top-level key: `infra-discovery.sh` regenerates the root schema and drops unrecognized keys. Keep provider facts in `context/cloudns.md` with discovery pointers in `context/sites.md` and `context/mgs-os-map.md`. Register reusable capabilities in the MGS knowledge registry, inventory structural additions and send the canonical REPORT-INFRA embed. Append a secret-free audit event with original authorization IDs, exact zone, read-only endpoints, counts, validation result and artifact checksum. Reconcile writes by readback before retry.

## Official references

- https://www.cloudns.net/wiki/article/42/ — authentication and API users/sub-users
- https://www.cloudns.net/wiki/article/45/ — login test
- https://www.cloudns.net/wiki/article/307/ — provider-observed IP
- https://www.cloudns.net/wiki/article/57/ — record listing and GeoDNS response fields
- https://www.cloudns.net/wiki/article/62/ — SOA details
- https://www.cloudns.net/wiki/article/166/ — BIND export limitation
