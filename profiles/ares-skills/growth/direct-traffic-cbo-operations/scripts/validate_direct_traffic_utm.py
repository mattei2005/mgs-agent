#!/usr/bin/env python3
"""Build or validate MGS direct-traffic Meta UTM URLs."""

import argparse
import json
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MEDIUM_RE = re.compile(r"^g(?P<manager>\d{3})-(?P<suffix>[fs])$")
CAMPAIGN_RE = re.compile(r"^b(?P<bm>\d{2})fb(?P<account>\d{2})c(?P<campaign>\d{2,})$")
ADGROUP_RE = re.compile(r"^(?P<prefix>b\d{2}fb\d{2}c\d{2,})g(?P<adset>\d{2})$")
REQUIRED = ("utm_source", "utm_medium", "utm_campaign", "utm_adgroup")


def validate(url: str, conversion_event: str | None = None) -> dict:
    errors = []
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    occurrences = {}
    for key, value in pairs:
        occurrences.setdefault(key, []).append(value)

    for key in REQUIRED:
        count = len(occurrences.get(key, []))
        if count != 1:
            errors.append(f"{key} must occur exactly once (found {count})")

    values = {key: occurrences.get(key, [""])[0] for key in REQUIRED}
    for key, value in values.items():
        if value != value.strip() or any(ch.isspace() for ch in value):
            errors.append(f"{key} contains whitespace")

    if values["utm_source"] != "facebook":
        errors.append("utm_source must be exactly 'facebook'")

    medium = MEDIUM_RE.fullmatch(values["utm_medium"])
    if not medium:
        errors.append("utm_medium must match gXXX-f (chat) or gXXX-s (quiz)")

    campaign = CAMPAIGN_RE.fullmatch(values["utm_campaign"])
    if not campaign:
        errors.append("utm_campaign must match bNNfbNNc{campaign}, with campaign using at least two digits")
    elif int(campaign.group("campaign")) < 1:
        errors.append("campaign number must be at least 1")

    adgroup = ADGROUP_RE.fullmatch(values["utm_adgroup"])
    if not adgroup:
        errors.append("utm_adgroup must match bNNfbNNc{campaign}gNN, with campaign using at least two digits")

    if campaign and adgroup and adgroup.group("prefix") != values["utm_campaign"]:
        errors.append("utm_adgroup prefix must equal utm_campaign")

    result = {"valid": not errors, "url": url, "errors": errors}
    if medium:
        strategy = "chat" if medium.group("suffix") == "f" else "quiz"
        required_event = "ADD_TO_WISHLIST" if strategy == "chat" else "SUBSCRIBE"
        result["manager"] = f"g{medium.group('manager')}"
        result["strategy"] = strategy
        result["required_conversion_event"] = required_event
        if conversion_event is not None:
            normalized_event = conversion_event.strip()
            result["conversion_event"] = normalized_event
            result["conversion_event_verified"] = normalized_event == required_event
            if normalized_event != required_event:
                errors.append(f"adset conversion event for {strategy} must be '{required_event}'")
    if campaign:
        result.update({k: int(campaign.group(k)) for k in ("bm", "account", "campaign")})
    if adgroup:
        result["adset"] = int(adgroup.group("adset"))
    result["errors"] = errors
    result["valid"] = not errors
    return result


def two_digit(value: int, label: str) -> str:
    if not 0 <= value <= 99:
        raise ValueError(f"{label} must be between 0 and 99")
    return f"{value:02d}"


def campaign_number(value: int) -> str:
    if value < 1:
        raise ValueError("campaign must be at least 1")
    return str(value).zfill(2)


def three_digit(value: int) -> str:
    if not 0 <= value <= 999:
        raise ValueError("manager must be between 0 and 999")
    return f"{value:03d}"


def build(args) -> str:
    parts = urlsplit(args.base_url)
    existing = parse_qsl(parts.query, keep_blank_values=True)
    if any(key in REQUIRED for key, _ in existing):
        raise ValueError("base URL already contains a canonical UTM; remove it before building")
    campaign = f"b{two_digit(args.bm, 'bm')}fb{two_digit(args.account, 'account')}c{campaign_number(args.campaign)}"
    suffix = "s" if args.strategy == "quiz" else "f"
    canonical = [
        ("utm_source", "facebook"),
        ("utm_medium", f"g{three_digit(args.manager)}-{suffix}"),
        ("utm_campaign", campaign),
        ("utm_adgroup", f"{campaign}g{two_digit(args.adset, 'adset')}"),
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(existing + canonical), parts.fragment))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", help="URL to validate")
    parser.add_argument("--build", action="store_true", help="Build and validate a URL")
    parser.add_argument("--base-url")
    parser.add_argument("--bm", type=int)
    parser.add_argument("--account", type=int)
    parser.add_argument("--campaign", type=int)
    parser.add_argument("--adset", type=int)
    parser.add_argument("--manager", type=int)
    parser.add_argument("--strategy", choices=("quiz", "chat"))
    parser.add_argument("--conversion-event", choices=("ADD_TO_WISHLIST", "SUBSCRIBE"), help="Meta adset promoted_object.custom_event_type")
    args = parser.parse_args()

    try:
        if args.build:
            missing = [name for name in ("base_url", "bm", "account", "campaign", "adset", "manager", "strategy") if getattr(args, name) is None]
            if missing:
                parser.error("--build requires: " + ", ".join("--" + x.replace("_", "-") for x in missing))
            url = build(args)
        elif args.url:
            url = args.url
        else:
            parser.error("provide a URL or use --build")
        result = validate(url, args.conversion_event)
    except ValueError as exc:
        result = {"valid": False, "errors": [str(exc)]}

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    sys.exit(main())
