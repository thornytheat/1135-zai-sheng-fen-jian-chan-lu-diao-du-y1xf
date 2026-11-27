from collections import defaultdict
from hashlib import sha256
from statistics import median
from .contracts import DriftObservation, LotBalance, ShiftBalance


def close(grades, reservation):
    locations = {event.lot: event for event in reservation.events}
    graded = {row.lot for row in grades}
    if (
        graded != set(locations)
        or len(graded) != len(grades)
        or len(locations) != len(reservation.events)
    ):
        raise ValueError("分级记录与仓位清单不匹配")
    balances = []
    for grade in sorted(grades, key=lambda row: row.lot):
        event = locations[grade.lot]
        in_bin = event.kg
        free = grade.forecast_kg - in_bin
        residue = grade.input_kg - grade.forecast_kg
        balances.append(LotBalance(grade.lot, grade.input_kg, in_bin, free, residue))
    material = tuple(
        (
            row.lot,
            row.net_kg,
            row.warehoused,
            row.forecast_unassigned,
            row.expected_residue,
            locations[row.lot].target,
            locations[row.lot].flag,
        )
        for row in balances
    )
    receipt = sha256(repr((reservation.limit, material)).encode()).hexdigest()[:14]
    return ShiftBalance(tuple(balances), receipt)


def material_shift(history, forecasts, cutoff):
    previous = defaultdict(list)
    current = defaultdict(list)
    for example in history:
        if example.closed <= cutoff:
            previous[example.polymer].append(example.yield_rate)
    for prediction in forecasts:
        if prediction.rate is not None:
            current[prediction.fit_group].append(prediction.rate)
    return tuple(
        DriftObservation(
            kind,
            len(previous[kind]),
            len(current[kind]),
            median(previous[kind]) if previous[kind] else None,
            median(current[kind]) if current[kind] else None,
        )
        for kind in sorted(previous.keys() | current.keys())
    )


def compare_bunkers(inventory, book):
    initial = {bunker.tag: bunker.spare for bunker in inventory}
    allocations = defaultdict(int)
    for placement in book.events:
        if placement.target:
            if placement.target not in initial:
                raise ValueError("预留记录包含未知仓位")
            allocations[placement.target] += placement.kg
    remainder = {key: value - allocations[key] for key, value in initial.items()}
    if remainder != book.remaining or any(value < 0 for value in remainder.values()):
        raise ValueError("分仓余量与登记不一致")
    return remainder
