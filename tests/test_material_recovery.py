from datetime import date
from dataclasses import replace
from types import SimpleNamespace as Obj
import pytest
from sortyield.material_recovery.engine import close, compare_bunkers, material_shift
from sortyield.grade_acceptance.contracts import Grade, GradeResult
from sortyield.bunker_slots.contracts import Bunker
from sortyield.bunker_slots.engine import allocate


def context(limit=1000):
    item = GradeResult("A", Grade.CLEAN, ("依据",), 850, 730, 1000, "PET")
    bins = [Bunker("BD-9", "PET", 1500, 350)]
    return [item], bins, allocate([item], bins, limit)


def test_exact_kg_conservation_tracks_unassigned_output_and_residue():
    # TRAP-10
    items, _, slots = context()
    line = close(items, slots).lines[0]
    assert (
        line.net_kg,
        line.warehoused,
        line.forecast_unassigned,
        line.expected_residue,
    ) == (1000, 730, 120, 150)


def test_policy_limit_changes_material_receipt_even_when_same_reservation():
    a, _, first = context(900)
    b, _, second = context(1000)
    assert (
        first.events == second.events
        and close(a, first).receipt != close(b, second).receipt
    )


def test_plant_drift_without_current_observations_has_no_shift():
    a = Obj(closed=date(2026, 11, 19), polymer="PET", yield_rate=0.8)
    report = material_shift([a], [], date(2026, 11, 20))
    assert report[0].present_count == 0 and report[0].shift is None


def test_plant_drift_excludes_unclosed_lots():
    a = Obj(closed=date(2026, 11, 19), polymer="PET", yield_rate=0.8)
    b = Obj(fit_group="PET", rate=0.6)
    late = Obj(closed=date(2026, 11, 23), polymer="PET", yield_rate=0)
    shift = material_shift([a, late], [b], date(2026, 11, 20))[0]
    assert shift.past_count == 1 and shift.shift == pytest.approx(-0.2)


def test_bunker_readback_uses_physical_inventory():
    _, stock, book = context()
    assert compare_bunkers(stock, book) == {"BD-9": 420}


def test_bad_bunker_readback_is_rejected():
    _, stock, book = context()
    with pytest.raises(ValueError, match="余量"):
        compare_bunkers(stock, replace(book, remaining={"BD-9": 421}))


def test_unknown_lot_does_not_pass_ledger_match():
    items, _, book = context()
    with pytest.raises(ValueError, match="不匹配"):
        close([], book)
