from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest

pytestmark = pytest.mark.s3_smoke


def test_s3_compatible_smoke_when_enabled(tmp_path):
    if os.getenv("FMKOREA_S3_SMOKE_ENABLED") != "true":
        pytest.skip("set FMKOREA_S3_SMOKE_ENABLED=true to run S3 smoke")
    boto3 = pytest.importorskip("boto3")

    from fmkorea_scraper.models.comment import AuthorInfo
    from fmkorea_scraper.models.enums import StorageMode
    from fmkorea_scraper.models.job import S3StorageConfig, StorageConfig
    from fmkorea_scraper.models.post import PostResult
    from fmkorea_scraper.outputs import StorageFactory

    endpoint = os.environ["FMKOREA_S3_ENDPOINT_URL"]
    bucket = os.environ["FMKOREA_S3_BUCKET"]
    access_key = os.environ["FMKOREA_S3_ACCESS_KEY_ID"]
    secret_key = os.environ["FMKOREA_S3_SECRET_ACCESS_KEY"]
    region = os.getenv("FMKOREA_S3_REGION")
    prefix = f"{os.getenv('FMKOREA_S3_PREFIX', 'smoke').strip('/')}/{uuid4().hex}"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    bundle = StorageFactory.create(
        StorageConfig(
            output_mode=StorageMode.S3_COMPATIBLE,
            base_output_path=str(tmp_path),
            s3=S3StorageConfig(endpoint_url=endpoint, bucket=bucket, prefix=prefix, region=region),
        ),
        job_id="job-1",
        run_id="run-1",
        s3_client=client,
    )
    ref = asyncio.run(
        bundle.output_store.append_post(
            PostResult(
                document_id_raw="101",
                canonical_url="https://www.fmkorea.com/best/101",
                title="sample",
                author=AuthorInfo(nickname="user"),
            )
        )
    )
    asyncio.run(bundle.output_store.finalize())

    try:
        response = client.get_object(Bucket=bucket, Key=ref.object_key)
        assert b'"document_id_raw":"101"' in response["Body"].read()
    finally:
        client.delete_object(Bucket=bucket, Key=ref.object_key)
