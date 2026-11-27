from sortyield.bunker_slots.contracts import Bunker
from sortyield.bunker_slots.load_study import exercise, rows
from sortyield.grade_acceptance.contracts import Grade, GradeResult


def grade(key, material, reserved):
    return GradeResult(key, Grade.CLEAN, (), reserved, reserved, 1800, material)


def test_incompatible_inventory_never_creates_more_spare_for_held_material():
    grades = [grade("A", "PP", 200), grade("B", "PET", 600)]
    stock = [Bunker("A", "PET", 1000, 0), Bunker("B", "HDPE", 9000, 0)]
    evidence = exercise(grades, stock, [900, 0])
    assert evidence[0].compatible_space_unused == 1000
    assert evidence[1].held_feed == (("PP", 200),)
    assert evidence[1].reserved_kg == 600
    assert evidence[1].compatible_space_unused == 0
    assert rows(evidence)[-1]["相邻额度预留变化（kg）"] == 600


def test_fragmented_compatible_capacity_is_retained_in_the_evidence():
    stock = [Bunker("A", "PET", 400, 0), Bunker("B", "PET", 500, 0)]
    evidence = exercise([grade("A", "PET", 600)], stock, [1000])[0]
    assert evidence.held_feed == (("PET", 600),)
    assert evidence.compatible_space_unused == 900
    assert evidence.reserved_lots == 0


def test_empty_evidence_has_known_zero_counts():
    evidence = exercise([], [], [1000, 1000, 0])
    assert len(evidence) == 2
    assert all(row.reserved_kg == 0 for row in evidence)
    assert all(row.change_from_previous_kg == 0 for row in evidence)
