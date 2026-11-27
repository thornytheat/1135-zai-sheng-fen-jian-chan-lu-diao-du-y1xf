from .contracts import Placement, PlacementFlag, Reservation
from ..grade_acceptance.contracts import Grade


def allocate(grades, bins, limit):
    if limit < 0 or len({bucket.tag for bucket in bins}) != len(bins):
        raise ValueError("总额度无效或仓位编号重复")
    remaining = {bucket.tag: bucket.spare for bucket in bins}
    total = limit
    entries = []
    for result in sorted(grades, key=lambda row: (-row.reserve_kg, row.lot)):
        if result.grade != Grade.CLEAN:
            flag = (
                PlacementFlag.SORT
                if result.grade == Grade.MIXED
                else PlacementFlag.SAMPLE
            )
            entries.append(
                Placement(result.lot, None, 0, flag, "、".join(result.reasons))
            )
            continue
        if not result.reserve_kg or result.reserve_kg > total:
            entries.append(
                Placement(result.lot, None, 0, PlacementFlag.HOLD, "余量或班次额度不足")
            )
            continue
        choices = [
            bucket
            for bucket in bins
            if bucket.feed == result.feed and remaining[bucket.tag] >= result.reserve_kg
        ]
        if not choices:
            entries.append(
                Placement(
                    result.lot, None, 0, PlacementFlag.HOLD, "缺少同材质的整批仓位"
                )
            )
            continue
        bin = min(choices, key=lambda bucket: (remaining[bucket.tag], bucket.tag))
        remaining[bin.tag] -= result.reserve_kg
        total -= result.reserve_kg
        entries.append(
            Placement(
                result.lot,
                bin.tag,
                result.reserve_kg,
                PlacementFlag.RESERVED,
                "同材质优先最小剩余空间",
            )
        )
    return Reservation(
        tuple(entries), dict(sorted(remaining.items())), limit, limit - total
    )


def tally(reservation):
    totals = {name: 0 for name in reservation.remaining}
    for event in reservation.events:
        if event.target is not None:
            totals[event.target] += event.kg
    return totals
