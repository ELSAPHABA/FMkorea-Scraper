from __future__ import annotations

import pytest

from stacks.config import load_environment_config
from stacks.naming import resource_name, slug, stack_name


def test_slug_is_deterministic_and_aws_safe() -> None:
    assert slug("Community Scraper_DEV__Worker") == "community-scraper-dev-worker"


def test_slug_rejects_blank_after_sanitize() -> None:
    with pytest.raises(ValueError):
        slug("___")


def test_resource_and_stack_names_include_environment() -> None:
    config = load_environment_config("dev")

    assert resource_name(config, "bucket").startswith("community-scraper-dev-")
    assert stack_name(config, "worker", "fmkorea") == "community-scraper-dev-fmkorea-worker"

