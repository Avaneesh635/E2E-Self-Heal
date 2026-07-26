"""Tests for the opt-in richer matching modes (MatchOptions).

Covers, per mode, that the default (no options) behavior is unchanged and that
enabling the mode changes matching as intended — including near-miss cases (a
candidate that almost matches) and reorder cases (order-insensitive matching).
"""

import pytest

from app.shadow.match_options import MatchOptions
from app.shadow.matcher import NoMatchError, SnapshotMatcher
from app.shadow.normalizer import RequestNormalizer
from app.shadow.scoring import MatchScorer
from app.shadow.schemas import CapturedRequest, CapturedResponse, NetworkSnapshot


def _snapshot(request: CapturedRequest, body: str) -> NetworkSnapshot:
    return NetworkSnapshot(request=request, response=CapturedResponse(status=200, body=body))


# ---------------------------------------------------------------------------
# Default behavior unchanged
# ---------------------------------------------------------------------------


def test_default_options_do_not_change_score():
    req1 = CapturedRequest(
        method="POST",
        url="http://test.com/items?page=1",
        headers={"Content-Type": "application/json"},
        body='{"a": 1, "tags": ["x", "y"]}',
    )
    req2 = CapturedRequest(
        method="POST",
        url="http://test.com/items?page=1",
        headers={"Content-Type": "application/json"},
        body='{"a": 1, "tags": ["x", "y"]}',
    )

    baseline = MatchScorer().calculate_score(req1, req2)
    with_defaults = MatchScorer(options=MatchOptions()).calculate_score(req1, req2)

    assert baseline == with_defaults


# ---------------------------------------------------------------------------
# Query-param normalization
# ---------------------------------------------------------------------------


def test_ignored_query_params_removes_key_from_scoring():
    normalizer = RequestNormalizer(MatchOptions(ignored_query_params=frozenset({"debug"})))
    _, query = normalizer.normalize_url("http://test.com/s?page=1&debug=xyz")
    assert "debug" not in query
    assert query["page"] == ["1"]


def test_ignored_query_params_near_miss_now_matches_fully():
    req1 = CapturedRequest(method="GET", url="http://test.com/s?page=1&debug=xyz")
    req2 = CapturedRequest(method="GET", url="http://test.com/s?page=1&debug=abc")

    # Default: differing 'debug' drags the query score below a full match.
    default_score = MatchScorer().calculate_score(req1, req2)

    # Opt-in: 'debug' ignored, so only 'page' is scored and it matches fully.
    opts = MatchOptions(ignored_query_params=frozenset({"debug"}))
    opted_score = MatchScorer(options=opts).calculate_score(req1, req2)

    assert opted_score > default_score


def test_case_insensitive_query_keys():
    req1 = CapturedRequest(method="GET", url="http://test.com/s?Tab=all")
    req2 = CapturedRequest(method="GET", url="http://test.com/s?tab=all")

    # Default: 'Tab' and 'tab' are distinct keys -> no query overlap.
    default_score = MatchScorer().calculate_score(req1, req2)

    opts = MatchOptions(case_insensitive_query_keys=True)
    opted_score = MatchScorer(options=opts).calculate_score(req1, req2)

    assert opted_score > default_score


# ---------------------------------------------------------------------------
# Header-aware matching (hard constraint)
# ---------------------------------------------------------------------------


def test_required_header_rejects_mismatch():
    snapshots = [
        _snapshot(
            CapturedRequest(
                method="GET",
                url="http://test.com/data",
                headers={"X-Tenant": "acme"},
            ),
            body="acme-data",
        ),
        _snapshot(
            CapturedRequest(
                method="GET",
                url="http://test.com/data",
                headers={"X-Tenant": "globex"},
            ),
            body="globex-data",
        ),
    ]

    opts = MatchOptions(required_headers=frozenset({"X-Tenant"}))
    matcher = SnapshotMatcher(snapshots, options=opts)

    # Near-miss: same path/method, only the required header differentiates them.
    incoming = CapturedRequest(
        method="GET", url="http://test.com/data", headers={"X-Tenant": "globex"}
    )
    assert matcher.match(incoming).body == "globex-data"


def test_required_header_absent_raises_no_match():
    snapshots = [
        _snapshot(
            CapturedRequest(method="GET", url="http://test.com/data", headers={"X-Tenant": "acme"}),
            body="acme-data",
        )
    ]
    opts = MatchOptions(required_headers=frozenset({"X-Tenant"}))
    matcher = SnapshotMatcher(snapshots, options=opts)

    # Incoming lacks the required header entirely -> no candidate qualifies.
    incoming = CapturedRequest(method="GET", url="http://test.com/data")
    with pytest.raises(NoMatchError):
        matcher.match(incoming)


def test_required_header_ignored_by_default():
    # Without the option, the differing header is only soft-scored, so a match
    # is still found (proves the constraint is strictly opt-in).
    snapshots = [
        _snapshot(
            CapturedRequest(method="GET", url="http://test.com/data", headers={"X-Tenant": "acme"}),
            body="acme-data",
        )
    ]
    matcher = SnapshotMatcher(snapshots)
    incoming = CapturedRequest(
        method="GET", url="http://test.com/data", headers={"X-Tenant": "globex"}
    )
    assert matcher.match(incoming).body == "acme-data"


def test_ignored_headers_dropped_from_scoring():
    normalizer = RequestNormalizer(MatchOptions(ignored_headers=frozenset({"X-Request-Id"})))
    normalized = normalizer.normalize_headers(
        {"X-Request-Id": "req-123", "Content-Type": "application/json"}
    )
    assert "x-request-id" not in normalized
    assert normalized["content-type"] == "application/json"


# ---------------------------------------------------------------------------
# Body-aware matching (hard constraint)
# ---------------------------------------------------------------------------


def test_require_body_match_rejects_near_miss():
    snapshots = [
        _snapshot(
            CapturedRequest(method="POST", url="http://test.com/x", body='{"a": 1, "b": 2}'),
            body="stored",
        )
    ]
    opts = MatchOptions(require_body_match=True)
    matcher = SnapshotMatcher(snapshots, options=opts)

    # Near-miss body: 'b' differs -> hard-rejected.
    near_miss = CapturedRequest(method="POST", url="http://test.com/x", body='{"a": 1, "b": 3}')
    with pytest.raises(NoMatchError):
        matcher.match(near_miss)

    # Exact normalized body -> matches.
    exact = CapturedRequest(method="POST", url="http://test.com/x", body='{"a": 1, "b": 2}')
    assert matcher.match(exact).body == "stored"


def test_require_body_match_default_allows_partial():
    snapshots = [
        _snapshot(
            CapturedRequest(method="POST", url="http://test.com/x", body='{"a": 1, "b": 2}'),
            body="stored",
        )
    ]
    matcher = SnapshotMatcher(snapshots)  # default: no hard body constraint
    near_miss = CapturedRequest(method="POST", url="http://test.com/x", body='{"a": 1, "b": 3}')
    assert matcher.match(near_miss).body == "stored"


# ---------------------------------------------------------------------------
# Fuzzy / order-insensitive array matching
# ---------------------------------------------------------------------------


def test_order_insensitive_arrays_normalizer():
    default = RequestNormalizer()
    fuzzy = RequestNormalizer(MatchOptions(order_insensitive_arrays=True))

    body = '{"tags": ["c", "a", "b"]}'
    assert default.normalize_body(body)["tags"] == ["c", "a", "b"]  # order preserved
    assert fuzzy.normalize_body(body)["tags"] == ["a", "b", "c"]  # canonicalized


def test_order_insensitive_arrays_reorder_matches():
    req1 = CapturedRequest(method="POST", url="http://test.com/x", body='{"tags": ["a", "b", "c"]}')
    req2 = CapturedRequest(method="POST", url="http://test.com/x", body='{"tags": ["c", "b", "a"]}')

    # Default: reordered arrays are not equal -> body scores partially.
    default_score = MatchScorer().calculate_score(req1, req2)

    # Opt-in: reordered arrays compare equal -> full body score.
    opts = MatchOptions(order_insensitive_arrays=True)
    opted_score = MatchScorer(options=opts).calculate_score(req1, req2)

    assert opted_score > default_score
    # Full match under the fuzzy option: exact_url(150)+query(30)+headers(20)+body(50).
    assert opted_score == 250.0


def test_order_insensitive_arrays_different_elements_still_differ():
    # Reorder-insensitivity must not collapse genuinely different arrays.
    req1 = CapturedRequest(method="POST", url="http://test.com/x", body='{"tags": ["a", "b", "c"]}')
    req2 = CapturedRequest(method="POST", url="http://test.com/x", body='{"tags": ["a", "b", "d"]}')
    opts = MatchOptions(order_insensitive_arrays=True)
    score = MatchScorer(options=opts).calculate_score(req1, req2)

    # Bodies differ, so it falls short of the full 250 exact-match score.
    assert score < 250.0


def test_order_insensitive_arrays_reorder_wins_tie_breaker():
    # Two snapshots for the same endpoint; incoming matches one only after reorder.
    snapshots = [
        _snapshot(
            CapturedRequest(method="POST", url="http://test.com/x", body='{"ids": [3, 2, 1]}'),
            body="reordered-set",
        ),
        _snapshot(
            CapturedRequest(method="POST", url="http://test.com/x", body='{"ids": [9, 8, 7]}'),
            body="other-set",
        ),
    ]
    opts = MatchOptions(order_insensitive_arrays=True)
    matcher = SnapshotMatcher(snapshots, options=opts)

    incoming = CapturedRequest(method="POST", url="http://test.com/x", body='{"ids": [1, 2, 3]}')
    assert matcher.match(incoming).body == "reordered-set"
