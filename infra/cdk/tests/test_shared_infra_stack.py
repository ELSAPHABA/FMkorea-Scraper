from __future__ import annotations

from aws_cdk import App, Environment
from aws_cdk.assertions import Match, Template

from stacks.config import load_environment_config
from stacks.shared_infra_stack import SharedInfraStack


def test_shared_stack_creates_no_nat_vpc_s3_rds_and_cluster() -> None:
    stack = _shared_stack("dev")
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::EC2::NatGateway", 0)
    template.resource_count_is("AWS::S3::Bucket", 1)
    template.resource_count_is("AWS::RDS::DBInstance", 1)
    template.resource_count_is("AWS::ECS::Cluster", 1)
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
        },
    )
    template.has_resource_properties(
        "AWS::RDS::DBInstance",
        Match.object_like(
            {
                "PubliclyAccessible": False,
                "StorageEncrypted": True,
                "MultiAZ": False,
            }
        ),
    )


def test_prod_stateful_resources_are_retained() -> None:
    stack = _shared_stack("prod")
    template = Template.from_stack(stack)

    template.has_resource("AWS::S3::Bucket", {"DeletionPolicy": "Retain"})
    template.has_resource("AWS::RDS::DBInstance", {"DeletionPolicy": "Retain"})


def _shared_stack(env_name: str) -> SharedInfraStack:
    config = load_environment_config(env_name)
    app = App()
    return SharedInfraStack(
        app,
        f"test-{env_name}-shared",
        config=config,
        env=Environment(account=config.aws.account, region=config.aws.region),
    )

