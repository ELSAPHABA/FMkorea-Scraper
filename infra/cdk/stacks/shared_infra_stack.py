from __future__ import annotations

from dataclasses import dataclass

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from constructs import Construct

from .config import EnvironmentConfig
from .naming import apply_standard_tags, resource_name


@dataclass(frozen=True)
class SharedInfraRefs:
    vpc: ec2.IVpc
    public_subnet_selection: ec2.SubnetSelection
    db_subnet_selection: ec2.SubnetSelection
    bucket: s3.IBucket
    cluster: ecs.ICluster
    database: rds.IDatabaseInstance
    database_security_group: ec2.ISecurityGroup


class SharedInfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, config: EnvironmentConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.config = config
        apply_standard_tags(self, config)

        vpc_kwargs = {
            "nat_gateways": config.network.nat_gateways,
            "subnet_configuration": [
                ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(name="db", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24),
            ],
        }
        if config.network.availability_zones:
            vpc_kwargs["availability_zones"] = config.network.availability_zones
        else:
            vpc_kwargs["max_azs"] = config.network.max_azs

        self.vpc = ec2.Vpc(self, "Vpc", **vpc_kwargs)

        self.bucket = s3.Bucket(
            self,
            "OutputBucket",
            bucket_name=config.s3.bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=config.s3.versioned,
            enforce_ssl=True,
            removal_policy=_stateful_removal_policy(config),
            auto_delete_objects=config.removal_policy.allow_destroy_stateful,
        )

        db_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=self.vpc,
            description="RDS PostgreSQL access from scraper worker tasks only",
            allow_all_outbound=True,
        )

        self.database = rds.DatabaseInstance(
            self,
            "CheckpointDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(version=_postgres_version(config.rds.engine_version)),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            credentials=rds.Credentials.from_generated_secret("scraper"),
            database_name=config.rds.database_name,
            instance_type=_instance_type(config.rds.instance_class),
            allocated_storage=config.rds.allocated_storage_gb,
            multi_az=config.rds.multi_az,
            backup_retention=Duration.days(config.rds.backup_retention_days),
            security_groups=[db_security_group],
            publicly_accessible=False,
            storage_encrypted=True,
            deletion_protection=config.removal_policy.profile.lower() == "prod",
            removal_policy=_stateful_removal_policy(config),
        )

        self.cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=self.vpc,
            cluster_name=resource_name(config, "cluster"),
        )

        self.refs = SharedInfraRefs(
            vpc=self.vpc,
            public_subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            db_subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            bucket=self.bucket,
            cluster=self.cluster,
            database=self.database,
            database_security_group=db_security_group,
        )

        CfnOutput(self, "OutputBucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "ClusterName", value=self.cluster.cluster_name)
        CfnOutput(self, "DatabaseEndpoint", value=self.database.db_instance_endpoint_address)


def _stateful_removal_policy(config: EnvironmentConfig) -> RemovalPolicy:
    return RemovalPolicy.RETAIN if config.removal_policy.retain_stateful else RemovalPolicy.DESTROY


def _postgres_version(version: str | None) -> rds.PostgresEngineVersion:
    if version:
        return rds.PostgresEngineVersion.of(version, version.split(".", 1)[0])
    return rds.PostgresEngineVersion.of("16.3", "16")


def _instance_type(value: str) -> ec2.InstanceType:
    if value == "burstable-low-cost":
        return ec2.InstanceType("t3.micro")
    return ec2.InstanceType(value)


