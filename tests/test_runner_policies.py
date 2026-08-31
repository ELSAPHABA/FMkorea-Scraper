from __future__ import annotations

from fmkorea_scraper.core.errors import BrowserFallbackError, BlockedResponseError, CaptchaDetectedError, ParseFailureError
from fmkorea_scraper.models.enums import StopReason
from fmkorea_scraper.models.job import PostCandidate
from fmkorea_scraper.runner.policies import (
    failure_retryable,
    post_key_from_candidate,
    post_key_token,
    should_save_running_checkpoint,
    stop_reason_for_exception,
)


def test_post_key_from_candidate_is_stable() -> None:
    candidate = PostCandidate(board_id="best", document_srl=101, document_id_raw="101", url="https://www.fmkorea.com/best/101")

    key = post_key_from_candidate(candidate)

    assert post_key_token(key) == ("fmkorea", "best", 101, "101")


def test_checkpoint_cadence_is_every_ten_successes() -> None:
    assert should_save_running_checkpoint(9, 0) is False
    assert should_save_running_checkpoint(10, 0) is True
    assert should_save_running_checkpoint(19, 10) is False
    assert should_save_running_checkpoint(20, 10) is True


def test_stop_reason_mapping_and_parser_retryability() -> None:
    assert stop_reason_for_exception(CaptchaDetectedError("captcha")) == StopReason.CAPTCHA
    assert stop_reason_for_exception(BlockedResponseError("blocked")) == StopReason.BLOCKED
    assert stop_reason_for_exception(BrowserFallbackError("browser failed")) == StopReason.ERROR
    assert failure_retryable("post", ParseFailureError("parse")) is True
