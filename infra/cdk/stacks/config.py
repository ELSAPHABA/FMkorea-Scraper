from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
SECRET_VALUE_KEYS = {
    "password",
    "secret",
    "secret_value",
    "token",
    "cookie",
    "access_key_id",
    "secret_access_key",
}


@dataclass(frozen=True)
class AwsConfig:
    account: str
    region: str


@dataclass(frozen=True)
class NamingConfig:
    project: str
    name_prefix: str


@dataclass(frozen=True)
class RemovalPolicyConfig:
    profile: str = "dev"
    allow_destroy_stateful: bool = False

    @property
    def retain_stateful(self) -> bool:
        return self.profile.lower() == "prod" or not self.allow_destroy_stateful


@dataclass(frozen=True)
class NetworkConfig:
    max_azs: int = 2
    nat_gateways: int = 0
    availability_zones: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class S3Config:
    bucket_name: str | None = None
    versioned: bool = False


@dataclass(frozen=True)
class RdsConfig:
    database_name: str = "scraper"
    engine_version: str | None = None
    allocated_storage_gb: int = 20
    instance_class: str = "burstable-low-cost"
    multi_az: bool = False
    backup_retention_days: int = 1


@dataclass(frozen=True)
class EcsConfig:
    cpu: int = 512
    memory_mib: int = 1024
    ephemeral_storage_gib: int | None = None


@dataclass(frozen=True)
class SecretRef:
    name: str | None = None
    arn: str | None = None
    field: str | None = None

    def present(self) -> bool:
        return bool(self.name or self.arn)


@dataclass(frozen=True)
class WorkerConfig:
    site_id: str
    image_uri: str
    image_tag: str = "latest"
    command: list[str] = field(default_factory=lambda: ["run"])
    schedule: str | None = None
    environment: dict[str, str] = field(default_factory=dict)
    secrets: dict[str, SecretRef] = field(default_factory=dict)
    failure_sns_topic_arn: str | None = None


@dataclass(frozen=True)
class EnvironmentConfig:
    environment: str
    aws: AwsConfig
    naming: NamingConfig
    removal_policy: RemovalPolicyConfig
    network: NetworkConfig
    s3: S3Config
    rds: RdsConfig
    ecs: EcsConfig
    workers: list[WorkerConfig]


def load_environment_config(env: str, *, config_dir: Path | None = None) -> EnvironmentConfig:
    path = (config_dir or CONFIG_DIR) / f"{env}.yaml"
    if not path.exists():
        raise ValueError(f"missing CDK environment config: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("environment config must be a mapping")
    _reject_plaintext_secrets(raw)

    aws = _required_mapping(raw, "aws")
    naming = _required_mapping(raw, "naming")
    workers_raw = raw.get("workers")
    if not isinstance(workers_raw, list) or not workers_raw:
        raise ValueError("workers must be a non-empty list")

    return EnvironmentConfig(
        environment=env,
        aws=AwsConfig(account=_required_str(aws, "account"), region=_required_str(aws, "region")),
        naming=NamingConfig(
            project=_required_str(naming, "project"),
            name_prefix=_required_str(naming, "name_prefix"),
        ),
        removal_policy=_parse_removal(raw.get("removal_policy") or {}),
        network=_parse_network(raw.get("network") or {}),
        s3=_parse_s3(raw.get("s3") or {}),
        rds=_parse_rds(raw.get("rds") or {}),
        ecs=_parse_ecs(raw.get("ecs") or {}),
        workers=[_parse_worker(item) for item in workers_raw],
    )


def _parse_removal(raw: dict[str, Any]) -> RemovalPolicyConfig:
    return RemovalPolicyConfig(
        profile=str(raw.get("profile") or "dev"),
        allow_destroy_stateful=bool(raw.get("allow_destroy_stateful", False)),
    )


def _parse_network(raw: dict[str, Any]) -> NetworkConfig:
    availability_zones = raw.get("availability_zones") or []
    if not isinstance(availability_zones, list):
        raise ValueError("network.availability_zones must be a list")
    return NetworkConfig(
        max_azs=int(raw.get("max_azs", 2)),
        nat_gateways=int(raw.get("nat_gateways", 0)),
        availability_zones=[str(zone) for zone in availability_zones],
    )


def _parse_s3(raw: dict[str, Any]) -> S3Config:
    return S3Config(
        bucket_name=_blank_none(raw.get("bucket_name")),
        versioned=bool(raw.get("versioned", False)),
    )


def _parse_rds(raw: dict[str, Any]) -> RdsConfig:
    return RdsConfig(
        database_name=str(raw.get("database_name") or "scraper"),
        engine_version=_blank_none(raw.get("engine_version")),
        allocated_storage_gb=int(raw.get("allocated_storage_gb", 20)),
        instance_class=str(raw.get("instance_class") or "burstable-low-cost"),
        multi_az=bool(raw.get("multi_az", False)),
        backup_retention_days=int(raw.get("backup_retention_days", 1)),
    )


def _parse_ecs(raw: dict[str, Any]) -> EcsConfig:
    return EcsConfig(
        cpu=int(raw.get("cpu", 512)),
        memory_mib=int(raw.get("memory_mib", 1024)),
        ephemeral_storage_gib=_optional_int(raw.get("ephemeral_storage_gib")),
    )


def _parse_worker(raw: Any) -> WorkerConfig:
    if not isinstance(raw, dict):
        raise ValueError("worker config must be a mapping")
    secrets_raw = raw.get("secrets") or {}
    if not isinstance(secrets_raw, dict):
        raise ValueError("worker secrets must be a mapping")
    environment = raw.get("environment") or {}
    if not isinstance(environment, dict):
        raise ValueError("worker environment must be a mapping")

    return WorkerConfig(
        site_id=_required_str(raw, "site_id"),
        image_uri=_required_str(raw, "image_uri"),
        image_tag=str(raw.get("image_tag") or "latest"),
        command=[str(part) for part in (raw.get("command") or ["run"])],
        schedule=_blank_none(raw.get("schedule")),
        environment={str(key): str(value) for key, value in environment.items()},
        secrets={str(key): _parse_secret_ref(value) for key, value in secrets_raw.items()},
        failure_sns_topic_arn=_blank_none(raw.get("failure_sns_topic_arn")),
    )


def _parse_secret_ref(raw: Any) -> SecretRef:
    if raw in (None, ""):
        return SecretRef()
    if not isinstance(raw, dict):
        raise ValueError("secret references must be mappings with name or arn")
    return SecretRef(
        name=_blank_none(raw.get("name")),
        arn=_blank_none(raw.get("arn")),
        field=_blank_none(raw.get("field")),
    )


def _required_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _required_str(raw: dict[str, Any], key: str) -> str:
    value = _blank_none(raw.get(key))
    if value is None:
        raise ValueError(f"{key} is required")
    return value


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _blank_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _reject_plaintext_secrets(value: Any, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        if path[-1:] == ("secrets",):
            for name, ref in value.items():
                if ref not in (None, "") and not isinstance(ref, dict):
                    raise ValueError(f"secret reference {name} must not be a plaintext value")
            return
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in SECRET_VALUE_KEYS and _blank_none(child) is not None:
                raise ValueError(f"plaintext secret-like config value is forbidden: {'.'.join(path + (str(key),))}")
            _reject_plaintext_secrets(child, path=path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_plaintext_secrets(child, path=path + (str(index),))

