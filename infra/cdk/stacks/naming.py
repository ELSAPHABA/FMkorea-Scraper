from __future__ import annotations

import re

from aws_cdk import Tags

from .config import EnvironmentConfig


_INVALID_CHARS = re.compile(r"[^a-z0-9-]+")


def slug(value: str, *, max_length: int = 63) -> str:
    text = _INVALID_CHARS.sub("-", value.lower()).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    if not text:
        raise ValueError("name part must contain at least one alphanumeric character")
    return text[:max_length].rstrip("-")


def resource_name(config: EnvironmentConfig, purpose: str, site_id: str | None = None, *, max_length: int = 63) -> str:
    parts = [config.naming.name_prefix, config.environment]
    if site_id:
        parts.append(site_id)
    parts.append(purpose)
    return slug("-".join(parts), max_length=max_length)


def stack_name(config: EnvironmentConfig, purpose: str, site_id: str | None = None) -> str:
    return resource_name(config, purpose, site_id, max_length=128)


def apply_standard_tags(scope, config: EnvironmentConfig, *, site_id: str | None = None) -> None:
    tags = {
        "Project": config.naming.project,
        "Environment": config.environment,
        "ManagedBy": "aws-cdk",
    }
    if site_id:
        tags["SiteId"] = site_id
    for key, value in tags.items():
        Tags.of(scope).add(key, value)

