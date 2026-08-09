"""Tests for dog policy classification, rank order, and gate integrity."""

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


def test_apply_large_dog_rank_order_puts_small_only_after_dogs_ok():
    dogs_ok = _listing(
        source_id="ok",
        dog_policy="dogs_ok",
        llm_rank=25,
        llm_severity="concerns",
    )
    small = _listing(
        source_id="small",
        dog_policy="small_only",
        llm_rank=14,
        llm_severity="concerns",
    )
    unknown = _listing(
        source_id="unk",
        dog_policy=None,
        llm_rank=16,
        llm_severity="concerns",
    )
    moved = dogs.apply_large_dog_rank_order([small, unknown, dogs_ok])
    assert moved >= 1
    assert dogs_ok.llm_rank == 1
    assert unknown.llm_rank == 2
    assert small.llm_rank == 3


def test_apply_large_dog_rank_order_is_idempotent():
    a = _listing(
        source_id="a",
        dog_policy="dogs_ok",
        llm_rank=3,
        llm_severity="ok",
    )
    b = _listing(
        source_id="b",
        dog_policy="small_only",
        llm_rank=1,
        llm_severity="concerns",
    )
    dogs.apply_large_dog_rank_order([a, b])
    first = (a.llm_rank, b.llm_rank)
    assert dogs.apply_large_dog_rank_order([a, b]) == 0
    assert (a.llm_rank, b.llm_rank) == first


def test_gate_conflict_flags_small_only_in_review_band():
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


def test_gate_conflict_skips_small_only_past_review_band():
    L = _listing(
        source_id="small",
        dog_policy="small_only",
        llm_rank=80,
        llm_severity="concerns",
    )
    assert dogs.gate_conflict_why(L) is None


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
    # After tier order: c=1 dogs_ok, b=2 unknown+ok (flagged), a=3 small_only (flagged)
    assert [f.listing.key for f in flags] == ["manual:b", "manual:a"]


def test_find_gate_conflicts_raw_skips_apply_order():
    small = _listing(
        source_id="small",
        dog_policy="small_only",
        llm_rank=14,
        llm_severity="concerns",
    )
    dogs_ok = _listing(
        source_id="ok",
        dog_policy="dogs_ok",
        llm_rank=25,
        llm_severity="concerns",
    )
    flags = dogs.find_gate_conflicts([small, dogs_ok], apply_order=False)
    assert small.llm_rank == 14
    assert any(f.listing.key == "manual:small" for f in flags)
