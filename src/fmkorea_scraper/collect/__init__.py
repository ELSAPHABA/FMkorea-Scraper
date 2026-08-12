"""Search and link collection contracts."""

from fmkorea_scraper.collect.models import (
    BoardCandidate,
    CollectorFailure,
    CollectorRun,
    CollectorSummary,
    RangeDecision,
    RangeDecisionKind,
    SearchTraversalState,
)
from fmkorea_scraper.collect.parsers import BoardPageParser, IntegratedSearchParser
from fmkorea_scraper.collect.policies import BoardCandidateDeduper, CandidateDeduper, RangeFilterEvaluator
from fmkorea_scraper.collect.service import LinkCollectorService, collect_all
from fmkorea_scraper.collect.urls import BoardUrlBuilder, DirectPostUrlNormalizer, IntegratedSearchUrlBuilder

__all__ = [
    "BoardCandidate",
    "BoardCandidateDeduper",
    "BoardPageParser",
    "BoardUrlBuilder",
    "CandidateDeduper",
    "CollectorFailure",
    "CollectorRun",
    "CollectorSummary",
    "DirectPostUrlNormalizer",
    "IntegratedSearchParser",
    "IntegratedSearchUrlBuilder",
    "LinkCollectorService",
    "RangeDecision",
    "RangeDecisionKind",
    "RangeFilterEvaluator",
    "SearchTraversalState",
    "collect_all",
]
