#!/usr/bin/env python3
"""Generate and validate the canonical Openzed DigitalTRChat link catalog."""

import argparse
import json
import sys
from urllib.parse import parse_qs, urlparse

SCHEMAS = {
    "US-CC-EN": {
        "host": "sr.openzed.com",
        "path_prefix": "op-us-cc-en-drip-",
        "content_prefix": "drip_us_cc_",
    },
    "GB-CC-EN": {
        "host": "sr.openzed.com",
        "path_prefix": "op-gb-cc-en-drip-",
        "content_prefix": "drip_gb_cc_",
    },
    "US-CC-ES": {
        "host": "srf.openzed.com",
        "path_prefix": "opf-us-cc-es-drip-",
        "content_prefix": "drip_us_cc_",
    },
    "ES-CC-ES": {
        "host": "srf.openzed.com",
        "path_prefix": "opf-es-cc-es-drip-",
        "content_prefix": "drip_es_cc_",
    },
}

LABELS = ["m0-1", "nm"] + [f"m{i}-1" for i in range(1, 29)]


def build_catalog(vertical):
    schema = SCHEMAS[vertical]
    result = {}
    for label in LABELS:
        result[label] = (
            f"https://{schema['host']}/{schema['path_prefix']}{label}/"
            f"?utm_source=facebook&utm_medium=g003-d"
            f"&utm_campaign=pg_#PAGE_ID#"
            f"&utm_content={schema['content_prefix']}{label}"
        )
    return result


def validate_catalogs(catalogs):
    errors = []
    all_urls = []
    for vertical, catalog in catalogs.items():
        schema = SCHEMAS[vertical]
        if list(catalog) != LABELS:
            errors.append(f"{vertical}: label order mismatch")
        if len(catalog) != 30 or len(set(catalog.values())) != 30:
            errors.append(f"{vertical}: expected 30 unique URLs")
        for label, original in catalog.items():
            if original.count("#PAGE_ID#") != 1:
                errors.append(f"{vertical}:{label}: PAGE_ID placeholder mismatch")
                continue
            safe = original.replace("#PAGE_ID#", "PAGE_ID_PLACEHOLDER")
            parsed = urlparse(safe)
            query = parse_qs(parsed.query)
            expected_path = f"/{schema['path_prefix']}{label}/"
            expected_content = f"{schema['content_prefix']}{label}"
            checks = {
                "scheme": parsed.scheme == "https",
                "host": parsed.netloc == schema["host"],
                "path": parsed.path == expected_path,
                "utm_source": query.get("utm_source") == ["facebook"],
                "utm_medium": query.get("utm_medium") == ["g003-d"],
                "utm_campaign": query.get("utm_campaign") == ["pg_PAGE_ID_PLACEHOLDER"],
                "utm_content": query.get("utm_content") == [expected_content],
                "utm_term_absent": "utm_term" not in query,
                "subscriber_absent": "subscriber_id" not in query,
            }
            for name, ok in checks.items():
                if not ok:
                    errors.append(f"{vertical}:{label}:{name}")
            all_urls.append(original)
    if len(all_urls) != 120 or len(set(all_urls)) != 120:
        errors.append("global catalog must contain 120 unique URLs")
    return {
        "status": "ok" if not errors else "error",
        "verticals": {key: len(value) for key, value in catalogs.items()},
        "total_urls": len(all_urls),
        "unique_urls": len(set(all_urls)),
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertical", choices=sorted(SCHEMAS))
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--format", choices=("json", "lines"), default="json")
    args = parser.parse_args()

    keys = [args.vertical] if args.vertical else list(SCHEMAS)
    catalogs = {key: build_catalog(key) for key in keys}

    if args.validate:
        # Global validation always covers all four approved combinations.
        result = validate_catalogs({key: build_catalog(key) for key in SCHEMAS})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "ok" else 1

    if args.format == "json":
        print(json.dumps(catalogs, ensure_ascii=False, indent=2))
    else:
        for vertical, catalog in catalogs.items():
            print(vertical)
            for label, url in catalog.items():
                print(f"{label}\t{url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
