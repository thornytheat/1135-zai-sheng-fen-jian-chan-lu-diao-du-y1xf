from dataclasses import dataclass

from .contracts import PlacementFlag
from .engine import allocate


@dataclass(frozen=True)
class CapacityEvidence:
    quota_kg: int
    reserved_kg: int
    reserved_lots: int
    compatible_space_unused: int
    held_feed: tuple[tuple[str, int], ...]
    change_from_previous_kg: int


def exercise(grades, inventory, limits):
    """Compare total tonnage constraints against each material's physical bins."""
    previous = None
    grade_by_lot = {grade.lot: grade for grade in grades}
    buckets = {bunker.tag: bunker for bunker in inventory}
    evidence = []
    for limit in sorted(set(limits)):
        plan = allocate(grades, inventory, limit)
        held = {}
        ratings = set()
        for row in plan.events:
            grade = grade_by_lot[row.lot]
            if row.flag == PlacementFlag.HOLD:
                ratings.add(grade.feed)
                held[grade.feed] = held.get(grade.feed, 0) + grade.reserve_kg
        unused = sum(
            available
            for tag, available in plan.remaining.items()
            if buckets[tag].feed in ratings
        )
        reserved = sum(row.flag == PlacementFlag.RESERVED for row in plan.events)
        change = plan.used - previous if previous is not None else 0
        evidence.append(
            CapacityEvidence(
                limit, plan.used, reserved, unused, tuple(sorted(held.items())), change
            )
        )
        previous = plan.used
    return tuple(evidence)


def rows(study):
    return [
        {
            "班次上限（kg）": row.quota_kg,
            "预留（kg）": row.reserved_kg,
            "已分派批次": row.reserved_lots,
            "待分材质期望（kg）": dict(row.held_feed),
            "同材质空余（kg）": row.compatible_space_unused,
            "相邻额度预留变化（kg）": row.change_from_previous_kg,
        }
        for row in study
    ]
