from datetime import date
from pathlib import Path
from .weighbridge import service as weigh
from .contamination_sample import service as sample
from .yield_forecast import service as model
from .grade_acceptance import service as grade
from .bunker_slots import service as store
from .bunker_slots.load_study import exercise, rows as capacity_rows
from .material_recovery import service as recover

DATA = Path(__file__).resolve().parents[2] / "sample_data"
CUT = weigh.instant("2026-11-25T11:00:00+08:00")
FOLD = date(2026, 11, 1)


def run(capacity=None):
    limit = (18 if capacity is None else capacity) * 1000
    journal = weigh.read(DATA / "weighbridge_shift_north.csv", CUT)
    samples, orphans = sample.from_file(DATA / "conveyor_cut_tag_log.csv", journal.lots)
    history = model.read(DATA / "separated_material_yield_history.csv")
    curves = model.per_polymer(history, FOLD, CUT.date())
    forecasts = tuple(
        model.predict(lot, samples[lot.lot], curves.get(lot.material))
        for lot in journal.lots
    )
    classifications = grade.grade_batch(journal.lots, samples, forecasts)
    bunkers = store.read(DATA / "bunker_register.csv")
    allocations = store.allocate(classifications, bunkers, limit)
    registered = recover.close(classifications, allocations)
    drift = recover.material_shift(history, forecasts, CUT.date())
    balance = recover.compare_bunkers(bunkers, allocations)
    final = {order.lot: order for order in allocations.events}
    rows = []
    for item in classifications:
        location = final[item.lot]
        rows.append(
            {
                "lot": item.lot,
                "material": item.feed,
                "input": item.input_kg,
                "forecast": item.forecast_kg,
                "grade": item.grade,
                "bunker": location.target,
                "placement": location.flag,
                "why": location.rule,
            }
        )
    metrics = {
        "来料批次": len(rows),
        "来料（kg）": registered.net_kg,
        "预留（kg）": allocations.used,
        "可用仓容（kg）": sum(balance.values()),
    }
    return {
        "metrics": metrics,
        "columns": {
            "lot": "料批",
            "material": "材质",
            "input": "来料（kg）",
            "forecast": "估算出料（kg）",
            "grade": "等级",
            "bunker": "仓位",
            "placement": "去向状态",
            "why": "依据",
        },
        "rows": rows,
        "series": [
            {"label": item.lot, "value": item.forecast_kg} for item in classifications
        ],
        "stages": [
            weigh.evidence(journal),
            sample.evidence(samples, orphans),
            model.evidence(curves, forecasts),
            grade.evidence(classifications),
            {
                **store.evidence(allocations),
                "班次额度试算": capacity_rows(
                    exercise(classifications, bunkers, [1000, limit, 100000])
                ),
            },
            recover.evidence(registered, drift, balance),
        ],
    }
