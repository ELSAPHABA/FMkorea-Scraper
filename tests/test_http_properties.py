from __future__ import annotations

from hypothesis import given, settings

from fmkorea_scraper.http import (
    ClassificationKind,
    HeaderBuilder,
    ProxyConfig,
    ResponseClassifier,
    SafeHttpEventBuilder,
    UserAgentConfig,
    UserAgentProvider,
)
from tests.strategies.http_runtime import headers, proxy_hosts, secret_values, user_agents


@given(user_agents, user_agents, user_agents)
@settings(max_examples=30)
def test_header_merge_referer_wins(default_user_agents, caller_user_agents, referers) -> None:
    default = {"Accept": "text/html", "User-Agent": default_user_agents[0]}
    caller = {"User-Agent": caller_user_agents[0]}
    merged = HeaderBuilder.build(default_headers=default, user_agent="runtime-ua", caller_headers=caller, referer=referers[0])

    assert merged["Accept"] == "text/html"
    assert merged["User-Agent"] == caller_user_agents[0]
    assert merged["Referer"] == referers[0]


@given(user_agents)
@settings(max_examples=30)
def test_user_agent_rotation_stays_within_candidates(agents) -> None:
    provider = UserAgentProvider(UserAgentConfig(default_user_agent="fallback", rotation_interval_requests=2))
    provider.agents = agents

    seen = [provider.next_for_request()[0] for _ in range(len(agents) * 3)]

    assert set(seen).issubset(set(agents))


@given(proxy_hosts, proxy_hosts)
@settings(max_examples=30)
def test_proxy_safe_label_never_contains_credentials(explicit_host, env_host) -> None:
    explicit = ProxyConfig.from_values(host=explicit_host, username="user", password="secret", source="explicit")
    env = ProxyConfig.from_values(host=env_host, username="env", password="env-secret", source="env_file")

    selected = explicit if explicit.enabled else env

    assert "secret" not in selected.safe_label
    assert "@" not in selected.safe_label


@given(headers)
@settings(max_examples=30)
def test_response_classification_is_idempotent(random_headers) -> None:
    classifier = ResponseClassifier()
    first = classifier.classify_response(
        status_code=500,
        final_url="https://www.fmkorea.com/best/1",
        headers=random_headers,
        body_sample="temporary",
    )
    second = classifier.classify_response(
        status_code=500,
        final_url="https://www.fmkorea.com/best/1",
        headers=random_headers,
        body_sample="temporary",
    )

    assert first == second
    assert first.kind == ClassificationKind.RETRYABLE


@given(secret_values)
@settings(max_examples=30)
def test_safe_event_builder_drops_secret_like_fields(secret) -> None:
    event = SafeHttpEventBuilder.build(
        "event",
        url="https://example.com/path?token=secret",
        password=secret,
        cookie=secret,
        headers={"authorization": secret},
    )

    assert "secret" not in repr(event).lower()
    assert event["url"] == "https://example.com/path"
