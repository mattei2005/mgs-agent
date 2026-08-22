from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "profiles/ares-skills/growth/direct-traffic-cbo-operations/scripts/validate_direct_traffic_utm.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("validate_direct_traffic_utm", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def args(campaign: int):
    return SimpleNamespace(
        base_url="https://example.com/quiz/",
        bm=1,
        account=13,
        campaign=campaign,
        adset=1,
        manager=6,
        strategy="quiz",
    )


def test_campaign_numbers_have_no_c59_or_c99_upper_limit():
    module = load_module()
    for campaign in (59, 60, 99, 100, 101, 123456):
        url = module.build(args(campaign))
        result = module.validate(url, "SUBSCRIBE")
        assert result["valid"], result
        assert result["campaign"] == campaign
        token = str(campaign).zfill(2)
        assert f"utm_campaign=b01fb13c{token}" in url
        assert f"utm_adgroup=b01fb13c{token}g01" in url


def test_single_digit_campaigns_keep_two_digit_zero_padding():
    module = load_module()
    url = module.build(args(1))
    assert "utm_campaign=b01fb13c01" in url
    assert module.validate(url, "SUBSCRIBE")["valid"]


def test_campaign_zero_is_rejected():
    module = load_module()
    try:
        module.build(args(0))
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError("campaign zero must be rejected")


def test_one_digit_manual_wrapper_is_rejected():
    module = load_module()
    url = (
        "https://example.com/quiz/?utm_source=facebook&utm_medium=g006-s"
        "&utm_campaign=b01fb13c1&utm_adgroup=b01fb13c1g01"
    )
    result = module.validate(url, "SUBSCRIBE")
    assert not result["valid"]
