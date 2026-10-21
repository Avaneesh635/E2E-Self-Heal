import pytest
from concurrent.futures import ThreadPoolExecutor

from app.shadow.scoring import MatchScorer, ScoringWeights
from app.shadow.matcher import SnapshotMatcher, NoMatchError
from app.shadow.schemas import CapturedRequest, CapturedResponse, NetworkSnapshot


def test_matching_engine_identical():
    snapshots = [
        NetworkSnapshot(
            request=CapturedRequest(method="GET", url="http://test.com/users"),
            response=CapturedResponse(status=200, body="users-list"),
        )
    ]
    matcher = SnapshotMatcher(snapshots)
    req = CapturedRequest(method="GET", url="http://test.com/users")
    resp = matcher.match(req)
    assert resp.body == "users-list"


def test_matching_engine_dynamic_fields():
    snapshots = [
        NetworkSnapshot(
            request=CapturedRequest(
                method="POST",
                url="http://test.com/api/users/11111111-2222-3333-4444-555555555555/update?ts=1000000000",
                body='{"name": "Bob", "session_id": "sess-1"}',
            ),
            response=CapturedResponse(status=200, body="bob-updated"),
        )
    ]
    matcher = SnapshotMatcher(snapshots)

    # Request with different dynamic UUID, query param, and body session_id
    incoming = CapturedRequest(
        method="POST",
        url="http://test.com/api/users/99999999-aaaa-bbbb-cccc-dddddddddddd/update?ts=2000000000",
        body='{"name": "Bob", "session_id": "sess-2"}',
    )

    resp = matcher.match(incoming)
    assert resp.body == "bob-updated"


def test_matching_engine_no_match():
    snapshots = [
        NetworkSnapshot(
            request=CapturedRequest(method="GET", url="http://test.com/users"),
            response=CapturedResponse(status=200, body="users-list"),
        )
    ]
    matcher = SnapshotMatcher(snapshots)
    req = CapturedRequest(method="GET", url="http://test.com/posts")

    with pytest.raises(NoMatchError):
        matcher.match(req)


def test_matching_engine_deterministic_conflict_resolution():
    # Multiple snapshots for the same endpoint, differing by stable body content
    snapshots = [
        NetworkSnapshot(
            request=CapturedRequest(
                method="POST",
                url="http://test.com/items",
                body='{"type": "book", "id": "1"}',
            ),
            response=CapturedResponse(status=200, body="book-item"),
        ),
        NetworkSnapshot(
            request=CapturedRequest(
                method="POST",
                url="http://test.com/items",
                body='{"type": "toy", "id": "2"}',
            ),
            response=CapturedResponse(status=200, body="toy-item"),
        ),
        NetworkSnapshot(
            request=CapturedRequest(
                method="POST",
                url="http://test.com/items",
                body='{"type": "book", "id": "3"}',  # same type, different id
            ),
            response=CapturedResponse(status=200, body="another-book-item"),
        ),
    ]

    matcher = SnapshotMatcher(snapshots)

    # Incoming query matches 'toy' more closely
    incoming = CapturedRequest(
        method="POST",
        url="http://test.com/items",
        body='{"type": "toy", "id": "99"}',
    )
    resp = matcher.match(incoming)
    assert resp.body == "toy-item"

    # Incoming query matches 'book' more closely. Should match first book snapshot (idx 0)
    # due to stable index sorting tie-breaker (same score for type=book and mismatching id).
    incoming2 = CapturedRequest(
        method="POST",
        url="http://test.com/items",
        body='{"type": "book", "id": "99"}',
    )
    resp2 = matcher.match(incoming2)
    assert resp2.body == "book-item"


def test_matching_engine_url_vs_path_tie_breaker():
    snapshots = [
        # Snapshot 0: matches normalized path only (different query param)
        NetworkSnapshot(
            request=CapturedRequest(method="GET", url="http://test.com/users?tab=active"),
            response=CapturedResponse(status=200, body="active-users"),
        ),
        # Snapshot 1: matches exact URL (including query param)
        NetworkSnapshot(
            request=CapturedRequest(method="GET", url="http://test.com/users?tab=all"),
            response=CapturedResponse(status=200, body="all-users"),
        ),
    ]

    matcher = SnapshotMatcher(snapshots)

    incoming = CapturedRequest(method="GET", url="http://test.com/users?tab=all")
    resp = matcher.match(incoming)
    assert resp.body == "all-users"


def test_matching_engine_replays_repeated_requests_in_captured_sequence_order():
    request = CapturedRequest(method="GET", url="http://test.com/api/poll")
    matcher = SnapshotMatcher(
        [
            NetworkSnapshot(
                request=request, response=CapturedResponse(status=200, body="complete"), sequence=2
            ),
            NetworkSnapshot(
                request=request, response=CapturedResponse(status=200, body="pending"), sequence=1
            ),
        ]
    )

    assert matcher.match(request).body == "pending"
    assert matcher.match(request).body == "complete"

    with pytest.raises(NoMatchError, match="queue exhausted"):
        matcher.match(request)


def test_matching_engine_keeps_replay_cursors_independent_per_request_signature():
    poll = CapturedRequest(method="GET", url="http://test.com/api/poll")
    page = CapturedRequest(method="GET", url="http://test.com/api/page")
    matcher = SnapshotMatcher(
        [
            NetworkSnapshot(
                request=poll, response=CapturedResponse(status=200, body="pending"), sequence=0
            ),
            NetworkSnapshot(
                request=page, response=CapturedResponse(status=200, body="first-page"), sequence=1
            ),
            NetworkSnapshot(
                request=poll, response=CapturedResponse(status=200, body="complete"), sequence=2
            ),
            NetworkSnapshot(
                request=page, response=CapturedResponse(status=200, body="second-page"), sequence=3
            ),
        ]
    )

    assert matcher.match(poll).body == "pending"
    assert matcher.match(page).body == "first-page"
    assert matcher.match(poll).body == "complete"
    assert matcher.match(page).body == "second-page"


def test_matching_engine_reserves_repeated_responses_safely_across_threads():
    request = CapturedRequest(method="GET", url="http://test.com/api/poll")
    matcher = SnapshotMatcher(
        [
            NetworkSnapshot(
                request=request,
                response=CapturedResponse(status=200, body=str(sequence)),
                sequence=sequence,
            )
            for sequence in range(20)
        ]
    )

    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(lambda _: matcher.match(request).body, range(20)))

    assert sorted(int(response) for response in responses if response is not None) == list(
        range(20)
    )


def test_custom_scoring_weights():
    # 1. Default weights score
    req1 = CapturedRequest(method="GET", url="http://test.com/users")
    req2 = CapturedRequest(method="GET", url="http://test.com/users")

    scorer_default = MatchScorer()
    default_score = scorer_default.calculate_score(req1, req2)
    # Default exact_url_bonus (150) + query_max (30) + headers_max (20) + body_max (50) = 250
    assert default_score == 250.0

    # 2. Custom weights score
    custom_weights = ScoringWeights(
        exact_url_bonus=10.0,
        base_url_match=5.0,
        query_max=1.0,
        headers_max=1.0,
        body_max=1.0,
    )
    scorer_custom = MatchScorer(weights=custom_weights)
    custom_score = scorer_custom.calculate_score(req1, req2)
    # 10 + 1 + 1 + 1 = 13
    assert custom_score == 13.0
