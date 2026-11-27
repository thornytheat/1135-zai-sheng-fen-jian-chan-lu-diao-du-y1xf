from collections import defaultdict
from math import ceil, fsum, log1p, sqrt
from .contracts import Curve, Estimate


def model_vector(kg, impurity, moisture, line):
    return log1p(kg), impurity, moisture, float(line == "涡电流线")


def normalize(raw, center, scale):
    return tuple(
        (x - mu) / sigma for x, mu, sigma in zip(raw, center, scale, strict=True)
    )


def center_fit(rows):
    columns = tuple(zip(*(row.features for row in rows), strict=True))
    center = tuple(fsum(col) / len(col) for col in columns)
    scale = tuple(
        max(1e-6, sqrt(fsum((x - mu) ** 2 for x in col) / len(col)))
        for col, mu in zip(columns, center, strict=True)
    )
    return center, scale, tuple((min(col), max(col)) for col in columns)


def clipped_prediction(vector, center, scale, params, base):
    weighted = fsum(
        w * x for w, x in zip(params, normalize(vector, center, scale), strict=True)
    )
    return max(0, min(1, base + weighted))


def fit_curve(material, train, validation, penalty=0.10):
    if len(train) < 5:
        raise ValueError("回归样本不足")
    center, scale, limits = center_fit(train)
    values = [normalize(row.features, center, scale) for row in train]
    target = [row.yield_rate for row in train]
    base = fsum(target) / len(target)
    params = [0.0] * len(center)
    for _ in range(150):
        errors = [
            base + fsum(w * x for w, x in zip(params, features, strict=True)) - y
            for features, y in zip(values, target, strict=True)
        ]
        gradient = [
            fsum(
                error * features[i]
                for error, features in zip(errors, values, strict=True)
            )
            / len(train)
            + penalty * params[i]
            for i in range(len(params))
        ]
        params = [
            weight - 0.1 * slope for weight, slope in zip(params, gradient, strict=True)
        ]
    residual = sorted(
        abs(
            row.yield_rate
            - clipped_prediction(row.features, center, scale, params, base)
        )
        for row in validation
    )
    quantile = (
        residual[min(len(residual), ceil(0.9 * (len(residual) + 1))) - 1]
        if residual
        else 0.12
    )
    return Curve(
        material,
        center,
        scale,
        limits,
        tuple(params),
        base,
        quantile,
        len(train),
        len(validation),
    )


def per_polymer(history, fold, cutoff):
    train = defaultdict(list)
    calibration = defaultdict(list)
    for row in history:
        if row.handled < fold and row.closed <= fold:
            train[row.polymer].append(row)
        elif row.handled >= fold and row.closed <= cutoff:
            calibration[row.polymer].append(row)
    curves = {
        material: fit_curve(material, rows, calibration[material])
        for material, rows in sorted(train.items())
        if len(rows) >= 5
    }
    return curves


def predict(lot, audit, curve):
    if curve is None or not audit.approved_samples:
        return Estimate(lot.lot, None, None, None, lot.material, "缺足量抽检或拟合记录")
    vector = model_vector(lot.kg, audit.impurity, audit.moisture, lot.line)
    distance = max(
        max(low - x, x - high, 0) / sd
        for x, (low, high), sd in zip(vector, curve.limits, curve.scale, strict=True)
    )
    if distance > 2.5:
        return Estimate(lot.lot, None, None, None, curve.material, "料批超出训练支撑")
    score = clipped_prediction(
        vector, curve.center, curve.scale, curve.params, curve.rate
    )
    return Estimate(
        lot.lot,
        score,
        max(0, score - curve.loss_radius),
        min(1, score + curve.loss_radius),
        curve.material,
        "已估算",
    )
