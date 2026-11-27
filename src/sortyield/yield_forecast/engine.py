from collections import defaultdict
from math import ceil, fsum, log1p, sqrt
from .contracts import Curve, Estimate, LayerEstimate


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


def score_point(vector, curve):
    """Score a single (kg, impurity, moisture, line) vector against a curve."""
    distance = max(
        max(low - x, x - high, 0) / sd
        for x, (low, high), sd in zip(vector, curve.limits, curve.scale, strict=True)
    )
    if distance > 2.5:
        return None, None, None
    rate = clipped_prediction(
        vector, curve.center, curve.scale, curve.params, curve.rate
    )
    return rate, max(0, rate - curve.loss_radius), min(1, rate + curve.loss_radius)


def predict_layers(lot, audit, curve):
    """Score each measured stratum on its own impurity/moisture pairing.

    Returns one LayerEstimate per stratum, keeping the measured pair intact so
    no synthetic (impurity, moisture) combination is ever scored.  A layer whose
    measured pair falls outside the training support is left unscored.
    """
    if curve is None or not audit.approved_samples:
        return tuple(
            LayerEstimate(layer.stratum, None, None, None, "缺足量抽检或拟合记录")
            for layer in audit.strata
        )
    layers = []
    for layer in audit.strata:
        vector = model_vector(lot.kg, layer.impurity, layer.moisture, lot.line)
        rate, lower, upper = score_point(vector, curve)
        notice = "已估算" if rate is not None else "料批超出训练支撑"
        layers.append(LayerEstimate(layer.stratum, rate, lower, upper, notice))
    return tuple(layers)


def predict(lot, audit, curve):
    if curve is None or not audit.approved_samples:
        return Estimate(lot.lot, None, None, None, lot.material, "缺足量抽检或拟合记录")
    strata = getattr(audit, "strata", ())
    if strata:
        layers = predict_layers(lot, audit, curve)
        if any(layer.rate is None for layer in layers):
            return Estimate(
                lot.lot,
                None,
                None,
                None,
                curve.material,
                "料批超出训练支撑",
                layers,
            )
        rate = fsum(layer.rate for layer in layers) / len(layers)
        lower = min(layer.lower for layer in layers)
        upper = max(layer.upper for layer in layers)
        return Estimate(
            lot.lot, rate, lower, upper, curve.material, "已估算", layers
        )
    vector = model_vector(lot.kg, audit.impurity, audit.moisture, lot.line)
    rate, lower, upper = score_point(vector, curve)
    if rate is None:
        return Estimate(lot.lot, None, None, None, curve.material, "料批超出训练支撑")
    return Estimate(lot.lot, rate, lower, upper, curve.material, "已估算")
