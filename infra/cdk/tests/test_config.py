from __future__ import annotations

from pathlib import Path

import pytest

from stacks.config import load_environment_config


def test_loads_dev_config() -> None:
    config = load_environment_config("dev")

    assert config.aws.region == "ap-northeast-2"
    assert config.network.nat_gateways == 0
    assert config.workers[0].site_id == "fmkorea"
    assert config.workers[0].secrets["database_url"].name == "community-scraper/dev/database-url"


def test_rejects_plaintext_secret_reference(tmp_path: Path) -> None:
    _write_config(
        tmp_path / "dev.yaml",
        """
aws:
  account: "111111111111"
  region: "ap-northeast-2"
naming:
  project: "community-scraper"
  name_prefix: "community-scraper"
workers:
  - site_id: "fmkorea"
    image_uri: "repo/image"
    secrets:
      database_url: "postgresql://user:password@db/scraper"
""",
    )

    with pytest.raises(ValueError, match="plaintext"):
        load_environment_config("dev", config_dir=tmp_path)


def test_rejects_secret_like_top_level_value(tmp_path: Path) -> None:
    _write_config(
        tmp_path / "dev.yaml",
        """
aws:
  account: "111111111111"
  region: "ap-northeast-2"
naming:
  project: "community-scraper"
  name_prefix: "community-scraper"
password: "do-not-store"
workers:
  - site_id: "fmkorea"
    image_uri: "repo/image"
""",
    )

    with pytest.raises(ValueError, match="plaintext secret-like"):
        load_environment_config("dev", config_dir=tmp_path)


def _write_config(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")

