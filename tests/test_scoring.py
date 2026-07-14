"""Unit tests for app.shadow.scoring.MatchScorer.

MatchScorer's default RequestNormalizer is pure and deterministic, so these
tests use the real normalizer directly (no mocks/fakes, no external
dependencies) per the issue's acceptance criteria.
"""

import json

import pytest

from app.shadow.scoring import MatchScorer, ScoringWeights
from app.shadow.schemas import CapturedRequest

WEIGHTS = ScoringWeights()
FULL_SCORE = (
    WEIGHTS.exact_url_bonus + WEIGHTS.query_max + WEIGHTS.headers_max + WEIGHTS.body_max
)


@pytest.fixture
def scorer():
    return MatchScorer()


def make_request(method="GET", url="/api/x", headers=None, body=None) -> CapturedRequest:
    return CapturedRequest(method=method, url=url, headers=headers or {}, body=body)


# --- Incompatibility (-1.0) cases ------------------------------------------------

def test_different_methods_are_incompatible(scorer):
    r1 = make_request(method="GET")
    r2 = make_request(method="POST")
    assert scorer.calculate_score(r1, r2) == -1.0


def test_method_comparison_is_case_insensitive(scorer):
    r1 = make_request(method="get", url="/api/x")
    r2 = make_request(method="GET", url="/api/x")
    assert scorer.calculate_score(r1, r2) != -1.0


def test_different_paths_are_incompatible(scorer):
    r1 = make_request(url="/api/a")
    r2 = make_request(url="/api/b")
    assert scorer.calculate_score(r1, r2) == -1.0


def test_different_uuids_in_path_still_match(scorer):
    r1 = make_request(url="/api/users/550e8400-e29b-41d4-a716-446655440000")
    r2 = make_request(url="/api/users/123e4567-e89b-12d3-a456-426614174000")
    assert scorer.calculate_score(r1, r2) != -1.0


# --- Exact match -------------------------------------------------------------

def test_exact_match_scores_full_marks(scorer):
    body = json.dumps({"x": 1})
    r1 = make_request(url="/api/x?a=1", headers={"H": "v"}, body=body)
    r2 = make_request(url="/api/x?a=1", headers={"H": "v"}, body=body)
    assert scorer.calculate_score(r1, r2) == pytest.approx(FULL_SCORE)


def test_identical_requests_with_no_query_headers_or_body(scorer):
    r1 = make_request(url="/api/x", headers={}, body=None)
    r2 = make_request(url="/api/x", headers={}, body=None)
    assert scorer.calculate_score(r1, r2) == pytest.approx(FULL_SCORE)


# --- Partial match -------------------------------------------------------------

def test_partial_match_scores_between_zero_and_full(scorer):
    r1 = make_request(url="/api/x?a=1&b=2", body=json.dumps({"x": 1, "y": 2}))
    r2 = make_request(url="/api/x?a=1&b=3", body=json.dumps({"x": 1, "y": 3}))
    score = scorer.calculate_score(r1, r2)
    assert 0.0 < score < FULL_SCORE


def test_same_url_different_query_values_uses_base_url_match(scorer):
    r1 = make_request(url="/api/x?a=1")
    r2 = make_request(url="/api/x?a=2")
    score = scorer.calculate_score(r1, r2)
    assert score < FULL_SCORE
    assert score >= WEIGHTS.base_url_match


# --- No overlap on query/headers/body, but same method + path -------------------

def test_disjoint_query_and_body_keys_score_low(scorer):
    r1 = make_request(url="/api/x?a=1", body=json.dumps({"x": 1}))
    r2 = make_request(url="/api/x?b=2", body=json.dumps({"y": 2}))
    score = scorer.calculate_score(r1, r2)
    assert score == pytest.approx(WEIGHTS.base_url_match + WEIGHTS.headers_max)


# --- Boundary / tie cases -------------------------------------------------------

def test_tie_boundary_half_of_query_keys_match(scorer):
    r1 = make_request(url="/api/x?a=1&b=2")
    r2 = make_request(url="/api/x?a=1&b=999")
    score = scorer.calculate_score(r1, r2)
    expected = (
        WEIGHTS.base_url_match
        + 0.5 * WEIGHTS.query_max
        + WEIGHTS.headers_max
        + WEIGHTS.body_max
    )
    assert score == pytest.approx(expected)


def test_tie_boundary_half_of_headers_match(scorer):
    r1 = make_request(url="/api/x", headers={"a": "1", "b": "2"})
    r2 = make_request(url="/api/x", headers={"a": "1", "b": "999"})
    score = scorer.calculate_score(r1, r2)
    expected = (
        WEIGHTS.exact_url_bonus
        + WEIGHTS.query_max
        + 0.5 * WEIGHTS.headers_max
        + WEIGHTS.body_max
    )
    assert score == pytest.approx(expected)


def test_tie_boundary_half_of_body_keys_match(scorer):
    r1 = make_request(url="/api/x", body=json.dumps({"x": 1, "y": 2}))
    r2 = make_request(url="/api/x", body=json.dumps({"x": 1, "y": 999}))
    score = scorer.calculate_score(r1, r2)
    expected = (
        WEIGHTS.exact_url_bonus
        + WEIGHTS.query_max
        + WEIGHTS.headers_max
        + 0.5 * WEIGHTS.body_max
    )
    assert score == pytest.approx(expected)


# --- Dynamic field normalization -------------------------------------------------

def test_dynamic_query_params_are_ignored_in_comparison(scorer):
    r1 = make_request(url="/api/x?timestamp=111")
    r2 = make_request(url="/api/x?timestamp=222")
    score = scorer.calculate_score(r1, r2)
    assert score == pytest.approx(
        WEIGHTS.base_url_match + WEIGHTS.query_max + WEIGHTS.headers_max + WEIGHTS.body_max
    )


def test_dynamic_headers_are_ignored_in_comparison(scorer):
    r1 = make_request(url="/api/x", headers={"Authorization": "Bearer aaa"})
    r2 = make_request(url="/api/x", headers={"Authorization": "Bearer bbb"})
    score = scorer.calculate_score(r1, r2)
    assert score == pytest.approx(FULL_SCORE)


def test_dynamic_body_keys_normalized_to_shared_placeholder(scorer):
    r1 = make_request(url="/api/x", body=json.dumps({"session_id": "aaa", "x": 1}))
    r2 = make_request(url="/api/x", body=json.dumps({"session_id": "bbb", "x": 1}))
    assert scorer.calculate_score(r1, r2) == pytest.approx(FULL_SCORE)


def test_non_json_body_with_timestamp_is_scrubbed(scorer):
    r1 = make_request(url="/api/x", body="log-entry at 2024-01-01T12:00:00Z done")
    r2 = make_request(url="/api/x", body="log-entry at 2024-06-15T09:30:00Z done")
    assert scorer.calculate_score(r1, r2) == pytest.approx(FULL_SCORE)


# --- Determinism -------------------------------------------------------------

def test_score_is_deterministic_across_repeated_calls(scorer):
    r1 = make_request(url="/api/x?a=1", body=json.dumps({"x": 1}))
    r2 = make_request(url="/api/x?a=2", body=json.dumps({"x": 2}))
    first = scorer.calculate_score(r1, r2)
    second = scorer.calculate_score(r1, r2)
    assert first == second


def test_score_is_symmetric_for_matching_dict_bodies(scorer):
    r1 = make_request(url="/api/x", body=json.dumps({"x": 1, "y": 2}))
    r2 = make_request(url="/api/x", body=json.dumps({"x": 1, "y": 3}))
    assert scorer.calculate_score(r1, r2) == pytest.approx(scorer.calculate_score(r2, r1))
