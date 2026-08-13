from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from fmkorea_scraper.adapters import cli
from fmkorea_scraper.adapters.cli import build_job_config
from tests.strategies.cli import direct_post_commands, realtime_keyword_envs


@given(direct_post_commands())
@settings(max_examples=30)
def test_direct_post_command_maps_without_changing_url(command) -> None:
    config = build_job_config(command, env={})

    assert config.job_id == command["job_id"]
    assert config.source.type == "direct_post"
    assert config.source.urls == command["urls"]


@given(realtime_keyword_envs())
@settings(max_examples=30)
def test_realtime_keyword_env_maps_to_duration_source(env) -> None:
    config = build_job_config({"subcommand": "run"}, env=env)

    assert config.source.type == "realtime_keyword"
    assert config.source.keyword == env["FMKOREA_REALTIME_KEYWORD"]
    assert config.source.termination.duration_seconds == int(env["FMKOREA_REALTIME_DURATION_SECONDS"])


@given(source=st.sampled_from(cli.SOURCE_CHOICES))
def test_source_alias_normalization_accepts_hyphen_and_underscore(source: str) -> None:
    normalized = source.replace("-", "_")

    assert cli.normalize_source_name(source) == normalized
    assert cli.normalize_source_name(normalized) == normalized
