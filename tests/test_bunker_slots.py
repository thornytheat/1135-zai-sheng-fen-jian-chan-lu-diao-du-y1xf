from sortyield.grade_acceptance.contracts import Grade, GradeResult
from sortyield.bunker_slots.contracts import Bunker, PlacementFlag
from sortyield.bunker_slots.engine import allocate, tally


def record(key="202A", kg=800, feed="PET", grade=Grade.CLEAN):
    return GradeResult(
        key, grade, ("检验",), kg, kg if grade == Grade.CLEAN else 0, 1000, feed
    )


def test_least_slack_fit_keeps_large_space_for_next_lot():
    slots = [Bunker("A", "PET", 1300, 0), Bunker("B", "PET", 850, 0)]
    result = allocate([record()], slots, 1400)
    assert result.events[0].target == "B" and result.remaining == {"A": 1300, "B": 50}


def test_need_full_space_in_one_compatible_bin():
    slots = [
        Bunker("A", "PP", 1000, 0),
        Bunker("B", "PET", 700, 0),
        Bunker("C", "PET", 700, 0),
    ]
    result = allocate([record()], slots, 1000)
    assert result.events[0].flag == PlacementFlag.HOLD and result.used == 0


def test_cannot_exceed_global_mass_even_if_bin_fits():
    result = allocate([record()], [Bunker("A", "PET", 1000, 0)], 799)
    assert result.used == 0


def test_exact_fit_is_allowed():
    result = allocate([record()], [Bunker("A", "PET", 1000, 150, 50)], 800)
    assert tally(result) == {"A": 800} and result.remaining["A"] == 0


def test_dirtier_grade_does_not_enter_clean_bunker():
    result = allocate([record(grade=Grade.MIXED)], [], 1000)
    assert result.events[0].flag == PlacementFlag.SORT


def test_input_order_does_not_change_assignment():
    slots = [Bunker("A", "PET", 1000, 0), Bunker("B", "PET", 850, 0)]
    items = [record("Z"), record("M")]
    assert allocate(items, slots, 1000) == allocate(items[::-1], slots[::-1], 1000)


def test_changeover_loss_leaves_no_negative_capacity():
    assert Bunker("A", "PET", 1000, 990, 15).spare == 0
