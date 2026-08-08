"""Tests for dog policy classification and gate integrity."""

from casita import dogs
from casita.models import Listing


def _listing(**kwargs) -> Listing:
    base = dict(
        source="manual",
        source_id="1",
        url="",
        title="Test listing",
    )
    base.update(kwargs)
    return Listing(**base)


def test_classify_restrictive_wins_over_dogs_ok():
    assert dogs.classify("Dogs ok but small dogs only") == "small_only"


def test_classify_no_dogs_and_large_ok():
    assert dogs.classify("Sorry, no pets") == "no_dogs"
    assert dogs.classify("Large dogs welcome") == "large_ok"
    assert dogs.classify("Pet friendly building") == "dogs_ok"
    assert dogs.classify(None, default="dogs_ok") == "dogs_ok"
    assert dogs.classify("") is None


def test_gate_conflict_flags_small_only_concerns():
    L = _listing(
        source_id="small",
        dog_policy="small_only",
        llm_rank=14,
        llm_severity="concerns",
        llm_reason="Small dogs only — would need to negotiate",
    )
    why = dogs.gate_conflict_why(L)
    assert why is not None
    assert "small_only" in why


def test_gate_conflict_flags_ok_with_unknown_policy():
    L = _listing(
        source_id="unk",
        dog_policy=None,
        llm_rank=7,
        llm_severity="ok",
        llm_reason="Great location",
    )
    assert dogs.gate_conflict_why(L) == "Gemini ok but dog policy unknown"


def test_gate_conflict_skips_dogs_ok_and_filtered_no_dogs():
    ok = _listing(
        source_id="ok",
        dog_policy="dogs_ok",
        llm_rank=2,
        llm_severity="ok",
    )
    filtered = _listing(
        source_id="nodogs",
        dog_policy="no_dogs",
        llm_rank=113,
        llm_severity="filtered",
        llm_reason="No dogs allowed.",
    )
    assert dogs.gate_conflict_why(ok) is None
    assert dogs.gate_conflict_why(filtered) is None


def test_find_gate_conflicts_orders_by_llm_rank():
    a = _listing(
        source_id="a",
        dog_policy="small_only",
        llm_rank=20,
        llm_severity="concerns",
    )
    b = _listing(
        source_id="b",
        dog_policy=None,
        llm_rank=5,
        llm_severity="ok",
    )
    c = _listing(
        source_id="c",
        dog_policy="dogs_ok",
        llm_rank=1,
        llm_severity="ok",
    )
    flags = dogs.find_gate_conflicts([a, b, c])
    assert [f.listing.key for f in flags] == ["manual:b", "manual:a"]
