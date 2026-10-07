import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _spec():
    return json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))


def test_go_host_is_noindexed_on_every_path_without_changing_existing_headers():
    headers = _spec()["headers"]
    go_rules = [
        rule
        for rule in headers
        if rule.get("source") == "/(.*)"
        and rule.get("has") == [{"type": "host", "value": "go.nuviestudio.com"}]
    ]

    assert len(go_rules) == 1, "missing one host-scoped noindex rule for go.nuviestudio.com"
    assert go_rules[0]["headers"] == [
        {"key": "X-Robots-Tag", "value": "noindex, nofollow"}
    ]
    assert set(go_rules[0]) == {"source", "has", "headers"}

    existing_headers = [rule for rule in headers if rule is not go_rules[0]]
    assert existing_headers == [
        {
            "source": "/availability.json",
            "headers": [{"key": "Cache-Control", "value": "public, max-age=300"}],
        },
        {
            "source": "/fonts/(.*)",
            "headers": [
                {
                    "key": "Cache-Control",
                    "value": "public, max-age=604800, stale-while-revalidate=2592000",
                }
            ],
        },
        {
            "source": "/img/(.*)",
            "headers": [
                {
                    "key": "Cache-Control",
                    "value": "public, max-age=86400, stale-while-revalidate=604800",
                }
            ],
        },
        {
            "source": "/(.*)\\.(css|js)",
            "headers": [
                {
                    "key": "Cache-Control",
                    "value": "public, max-age=300, stale-while-revalidate=600",
                }
            ],
        },
    ]
