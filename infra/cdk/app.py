#!/usr/bin/env python3
from __future__ import annotations

from aws_cdk import App, Environment

from stacks.config import load_environment_config
from stacks.naming import stack_name
from stacks.shared_infra_stack import SharedInfraStack
from stacks.worker_stack import WorkerStack


def main() -> None:
    app = App()
    env_name = app.node.try_get_context("env") or "dev"
    use_config_account = str(app.node.try_get_context("use_config_account") or "").lower() == "true"
    config = load_environment_config(env_name)
    aws_env = Environment(
        account=config.aws.account if use_config_account else None,
        region=config.aws.region,
    )

    shared = SharedInfraStack(
        app,
        stack_name(config, "shared"),
        config=config,
        env=aws_env,
    )

    for worker in config.workers:
        WorkerStack(
            app,
            stack_name(config, "worker", worker.site_id),
            config=config,
            worker=worker,
            shared=shared.refs,
            env=aws_env,
        )

    app.synth()


if __name__ == "__main__":
    main()

