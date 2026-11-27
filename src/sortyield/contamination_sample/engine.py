from collections import defaultdict
from math import fsum, sqrt
from .contracts import Audit, Cut, SamplingPlan


def wilson_upper(portion, total, z=1.645):
    if total <= 0:
        return None
    if not 0 <= portion <= 1:
        raise ValueError("比例超限")
    correction = z * z / total
    center = portion + 0.5 * correction
    spread = z * sqrt(portion * (1 - portion) / total + correction / (4 * total))
    return min(1, (center + spread) / (1 + correction))


def estimate(lot, raw, plan=SamplingPlan()):
    by_key = defaultdict(set)
    excluded = 0
    for row in raw:
        try:
            cut = Cut(
                row["sample"],
                row["stratum"],
                int(row["grams"]),
                int(row["unwanted"]),
                int(row["water"]),
            )
            if cut.stratum not in plan.strata or cut.grams < plan.minimum_grams:
                raise ValueError("取样层或样本质量不合格")
        except (ValueError, TypeError, KeyError):
            excluded += 1
            continue
        by_key[cut.specimen].add(cut)
    grouped = defaultdict(list)
    for cuts in by_key.values():
        if len(cuts) != 1:
            excluded += 1
            continue
        accepted = next(iter(cuts))
        grouped[accepted.stratum].append(accepted)
    if not grouped:
        return Audit(lot, 0, 0, None, None, None, excluded, 0)
    means = []
    waters = []
    mass = 0
    count = 0
    equivalent = 0
    for stratum, cuts in sorted(grouped.items()):
        grams = sum(cut.grams for cut in cuts)
        undesirable = sum(cut.unwanted for cut in cuts)
        means.append(undesirable / grams)
        waters.append(sum(cut.water for cut in cuts) / grams)
        equivalent += len(cuts) * 10
        mass += grams
        count += len(cuts)
    impurity = fsum(means) / len(means)
    moisture = fsum(waters) / len(waters)
    return Audit(
        lot,
        count,
        mass,
        impurity,
        moisture,
        wilson_upper(impurity, equivalent),
        excluded,
        len(grouped) / len(plan.strata),
    )


def isolate(rows, lots):
    by_lot = defaultdict(list)
    orphans = []
    keys = {lot.lot for lot in lots}
    for entry in rows:
        if entry["lot"] not in keys:
            orphans.append(entry["sample"])
        else:
            by_lot[entry["lot"]].append(entry)
    return {key: estimate(key, by_lot[key]) for key in sorted(keys)}, tuple(
        sorted(orphans)
    )
