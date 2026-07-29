"""Matching engine to resolve incoming requests against captured network snapshots."""

import urllib.parse

from app.shadow.match_options import MatchOptions
from app.shadow.scoring import MatchScorer
from app.shadow.schemas import CapturedRequest, CapturedResponse, NetworkSnapshot


class NoMatchError(Exception):
    """Raised when the matcher cannot find a matching snapshot for a request."""

    def __init__(
        self, request: CapturedRequest, message: str = "No matching network snapshot found"
    ):
        self.request = request
        super().__init__(f"{message}: {request.method} {request.url}")


class SnapshotMatcher:
    """Matches outgoing intercepted requests against stored NetworkSnapshots using similarity scoring."""

    def __init__(
        self,
        snapshots: list[NetworkSnapshot],
        scorer: MatchScorer | None = None,
        options: MatchOptions | None = None,
    ):
        self.snapshots = snapshots
        if scorer is not None and options is not None and scorer.options != options:
            raise ValueError("scorer and matcher must use the same MatchOptions")
        self.options = options or (scorer.options if scorer is not None else MatchOptions())
        self.scorer = scorer or MatchScorer(options=self.options)

    def _best(self, request: CapturedRequest) -> tuple[NetworkSnapshot, float]:
        """Scores all snapshots and returns the winning (snapshot, score) pair.

        Deterministic conflict resolution/tie-breaking, sorting candidates by:
        1. Score descending (highest score first)
        2. Exact URL match (True comes before False)
        3. Exact URL path match (True comes before False)
        4. Original snapshot index ascending (stable, deterministic ordering)
        """
        candidates = []

        for idx, snapshot in enumerate(self.snapshots):
            score = self.scorer.calculate_score(request, snapshot.request)
            if score >= 0 and score >= self.options.min_score:
                candidates.append((score, idx, snapshot))

        if not candidates:
            raise NoMatchError(request)

        def sort_key(item):
            score, idx, snapshot = item
            exact_url = request.url == snapshot.request.url

            p1 = urllib.parse.urlparse(request.url).path
            p2 = urllib.parse.urlparse(snapshot.request.url).path
            exact_path = p1 == p2

            # Sort is ascending by default. To put highest scores first, we negate score.
            # To put exact matches (True) first, we negate the boolean value (-1 for True, 0 for False).
            return (-score, -int(exact_url), -int(exact_path), idx)

        candidates.sort(key=sort_key)
        score, _, snapshot = candidates[0]
        return snapshot, score

    def match(self, request: CapturedRequest) -> CapturedResponse:
        """Resolves the given captured request to the best-matching captured response.

        Scans all snapshots, scores them using the MatchScorer, and returns the response
        of the highest scoring candidate. Resolves ties deterministically.
        """
        snapshot, _ = self._best(request)
        return snapshot.response

    def match_with_score(self, request: CapturedRequest) -> tuple[CapturedResponse, float]:
        """Resolves the given captured request and returns the response plus its similarity score."""
        snapshot, score = self._best(request)
        return snapshot.response, score
