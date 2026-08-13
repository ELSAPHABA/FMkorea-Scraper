from __future__ import annotations

import json

from aws_cdk import App, Environment
from aws_cdk.assertions import Match, Template

from stacks.config import load_environment_config
from stacks.shared_infra_stack import SharedInfraStack
from stacks.worker_stack import WorkerStack


def test_worker_stack_maps_container_env_secrets_logs_and_failure_signal() -> None:
    _, worker_template = _templates("dev")

    worker_template.resource_count_is("AWS::ECS::TaskDefinition", 1)
    worker_template.resource_count_is("AWS::Logs::LogGroup", 1)
    worker_template.resource_count_is("AWS::Events::Rule", 1)
    worker_template.resource_count_is("AWS::CloudWatch::Alarm", 1)
    worker_template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": Match.array_with(
                [
                    Match.object_like(
                        {
                            "Environment": Match.array_with(
                                [
                                    Match.object_like({"Name": "S3_ENDPOINT_URL", "Value": "https://s3.ap-northeast-2.amazonaws.com"}),
                                    Match.object_like({"Name": "S3_BUCKET"}),
                                    Match.object_like({"Name": "S3_REGION", "Value": "ap-northeast-2"}),
                                    Match.object_like({"Name": "S3_FORCE_PATH_STYLE", "Value": "false"}),
                                    Match.object_like({"Name": "S3_PREFIX", "Value": "outputs/dev/fmkorea"}),
                                ]
                            ),
                            "Secrets": Match.array_with(
                                [
                                    Match.object_like({"Name": "DATABASE_URL"}),
                                    Match.object_like({"Name": "S3_ACCESS_KEY_ID"}),
                                    Match.object_like({"Name": "S3_SECRET_ACCESS_KEY"}),
                                ]
                            ),
                        }
                    )
                ]
            )
        },
    )


def test_worker_task_role_scopes_s3_and_secret_access() -> None:
    _, worker_template = _templates("dev")
    data = worker_template.to_json()
    rendered = json.dumps(data)

    assert "outputs/dev/fmkorea/*" in rendered
    assert "community-scraper/dev/database-url" in rendered
    assert "community-scraper/dev/s3-access-key-id" in rendered
    assert "community-scraper/dev/s3-secret-access-key" in rendered
    assert "postgresql://user:password" not in rendered
    worker_template.has_resource_properties(
        "AWS::IAM::Policy",
        Match.object_like(
            {
                "PolicyDocument": Match.object_like(
                    {
                        "Statement": Match.array_with(
                            [
                                Match.object_like(
                                    {
                                        "Action": "s3:ListBucket",
                                        "Condition": {"StringLike": {"s3:prefix": ["outputs/dev/fmkorea", "outputs/dev/fmkorea/*"]}},
                                    }
                                )
                            ]
                        )
                    }
                )
            }
        ),
    )


def test_worker_stack_adds_database_ingress_without_mutating_shared_stack() -> None:
    shared_template, worker_template = _templates("dev")

    shared_template.resource_count_is("AWS::EC2::SecurityGroupIngress", 0)
    worker_template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        Match.object_like({"FromPort": 5432, "IpProtocol": "tcp", "ToPort": 5432}),
    )


def _templates(env_name: str) -> tuple[Template, Template]:
    config = load_environment_config(env_name)
    app = App()
    aws_env = Environment(account=config.aws.account, region=config.aws.region)
    shared = SharedInfraStack(app, f"test-{env_name}-shared", config=config, env=aws_env)
    worker = WorkerStack(
        app,
        f"test-{env_name}-worker",
        config=config,
        worker=config.workers[0],
        shared=shared.refs,
        env=aws_env,
    )
    return Template.from_stack(shared), Template.from_stack(worker)

