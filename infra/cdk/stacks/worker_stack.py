from __future__ import annotations

import re

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_sns as sns
from constructs import Construct

from .config import EnvironmentConfig, SecretRef, WorkerConfig
from .naming import apply_standard_tags, resource_name
from .shared_infra_stack import SharedInfraRefs


class WorkerStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: EnvironmentConfig,
        worker: WorkerConfig,
        shared: SharedInfraRefs,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        apply_standard_tags(self, config, site_id=worker.site_id)

        worker_sg = ec2.SecurityGroup(
            self,
            "WorkerSecurityGroup",
            vpc=shared.vpc,
            description="Outbound-only scraper worker task security group",
            allow_all_outbound=True,
        )
        ec2.CfnSecurityGroupIngress(
            self,
            "DatabaseIngressFromWorker",
            group_id=shared.database_security_group.security_group_id,
            ip_protocol="tcp",
            from_port=5432,
            to_port=5432,
            source_security_group_id=worker_sg.security_group_id,
            description=f"{worker.site_id} worker to PostgreSQL",
        )

        log_group = logs.LogGroup(
            self,
            "WorkerLogGroup",
            log_group_name=f"/scraper/{config.environment}/{worker.site_id}",
            retention=_log_retention(config.environment),
            removal_policy=_log_removal_policy(config),
        )

        task_role = iam.Role(
            self,
            "WorkerTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        execution_role = iam.Role(
            self,
            "WorkerExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ],
        )

        task_kwargs = {
            "cpu": config.ecs.cpu,
            "memory_limit_mib": config.ecs.memory_mib,
            "task_role": task_role,
            "execution_role": execution_role,
        }
        if config.ecs.ephemeral_storage_gib is not None:
            task_kwargs["ephemeral_storage_gib"] = config.ecs.ephemeral_storage_gib

        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            **task_kwargs,
        )

        secrets = _container_secrets(self, worker.secrets, task_role)
        task_definition.add_container(
            "WorkerContainer",
            image=_container_image(self, worker),
            command=worker.command,
            environment=_container_environment(config, worker, shared),
            secrets=secrets,
            logging=ecs.LogDrivers.aws_logs(stream_prefix=worker.site_id, log_group=log_group),
        )

        _grant_s3_prefix_access(shared.bucket, task_role, config.environment, worker.site_id)

        if worker.schedule:
            events.Rule(
                self,
                "ScheduleRule",
                schedule=events.Schedule.expression(worker.schedule),
                targets=[
                    events_targets.EcsTask(
                        cluster=shared.cluster,
                        task_definition=task_definition,
                        subnet_selection=shared.public_subnet_selection,
                        security_groups=[worker_sg],
                        assign_public_ip=True,
                    )
                ],
            )

        failure_rule = events.Rule(
            self,
            "TaskFailureRule",
            event_pattern=events.EventPattern(
                source=["aws.ecs"],
                detail_type=["ECS Task State Change"],
                detail={
                    "lastStatus": ["STOPPED"],
                    "clusterArn": [shared.cluster.cluster_arn],
                    "taskDefinitionArn": [task_definition.task_definition_arn],
                    "containers": {"exitCode": [{"anything-but": 0}]},
                },
            ),
        )
        alarm = cloudwatch.Alarm(
            self,
            "TaskFailureAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/Events",
                metric_name="TriggeredRules",
                dimensions_map={"RuleName": failure_rule.rule_name},
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        if worker.failure_sns_topic_arn:
            topic = sns.Topic.from_topic_arn(self, "FailureTopic", worker.failure_sns_topic_arn)
            alarm.add_alarm_action(cloudwatch_actions.SnsAction(topic))

        CfnOutput(self, "TaskDefinitionArn", value=task_definition.task_definition_arn)
        CfnOutput(self, "WorkerSecurityGroupId", value=worker_sg.security_group_id)


def _container_image(scope: Construct, worker: WorkerConfig) -> ecs.ContainerImage:
    match = re.fullmatch(r"(?P<account>\d+)\.dkr\.ecr\.(?P<region>[^.]+)\.amazonaws\.com/(?P<repo>.+)", worker.image_uri)
    if match:
        repository = ecr.Repository.from_repository_arn(
            scope,
            "WorkerImageRepository",
            f"arn:aws:ecr:{match.group('region')}:{match.group('account')}:repository/{match.group('repo')}",
        )
        return ecs.ContainerImage.from_ecr_repository(repository, tag=worker.image_tag)
    return ecs.ContainerImage.from_registry(_image_ref(worker))


def _image_ref(worker: WorkerConfig) -> str:
    return f"{worker.image_uri}:{worker.image_tag}" if worker.image_tag else worker.image_uri


def _container_environment(
    config: EnvironmentConfig,
    worker: WorkerConfig,
    shared: SharedInfraRefs,
) -> dict[str, str]:
    generated = {
        "S3_ENDPOINT_URL": f"https://s3.{config.aws.region}.amazonaws.com",
        "S3_BUCKET": shared.bucket.bucket_name,
        "S3_REGION": config.aws.region,
        "S3_FORCE_PATH_STYLE": "false",
        "S3_PREFIX": f"outputs/{config.environment}/{worker.site_id}",
    }
    generated.update(worker.environment)
    return generated


def _container_secrets(scope: Construct, refs: dict[str, SecretRef], task_role: iam.IRole) -> dict[str, ecs.Secret]:
    result: dict[str, ecs.Secret] = {}
    for env_name, ref in refs.items():
        if not ref.present():
            continue
        secret = _import_secret(scope, env_name, ref)
        secret.grant_read(task_role)
        result[env_name.upper()] = ecs.Secret.from_secrets_manager(secret, field=ref.field)
    return result


def _import_secret(scope: Construct, env_name: str, ref: SecretRef) -> secretsmanager.ISecret:
    construct_id = f"Secret{_pascal(env_name)}"
    if ref.arn:
        return secretsmanager.Secret.from_secret_complete_arn(scope, construct_id, ref.arn)
    if ref.name:
        return secretsmanager.Secret.from_secret_name_v2(scope, construct_id, ref.name)
    raise ValueError(f"missing secret reference for {env_name}")


def _grant_s3_prefix_access(bucket, task_role: iam.IRole, environment: str, site_id: str) -> None:
    prefix = f"outputs/{environment}/{site_id}"
    task_role.add_to_policy(
        iam.PolicyStatement(
            actions=["s3:ListBucket"],
            resources=[bucket.bucket_arn],
            conditions={"StringLike": {"s3:prefix": [prefix, f"{prefix}/*"]}},
        )
    )
    task_role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:AbortMultipartUpload",
                "s3:ListMultipartUploadParts",
            ],
            resources=[bucket.arn_for_objects(f"{prefix}/*")],
        )
    )


def _log_retention(environment: str) -> logs.RetentionDays:
    return logs.RetentionDays.ONE_MONTH if environment == "prod" else logs.RetentionDays.ONE_WEEK


def _log_removal_policy(config: EnvironmentConfig):
    from aws_cdk import RemovalPolicy

    return RemovalPolicy.RETAIN if config.removal_policy.profile.lower() == "prod" else RemovalPolicy.DESTROY


def _pascal(value: str) -> str:
    return "".join(part.capitalize() for part in value.replace("-", "_").split("_") if part)

