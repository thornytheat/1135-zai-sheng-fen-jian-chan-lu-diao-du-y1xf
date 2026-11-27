from dataclasses import dataclass
from datetime import date
from math import isfinite


@dataclass(frozen=True)
class RunHistory:
    handled: date
    closed: date
    polymer: str
    features: tuple[float, ...]
    yield_rate: float

    def __post_init__(self):
        if self.closed <= self.handled or not self.polymer or len(self.features) != 4:
            raise ValueError("产率样本时序、品种或维度错误")
        if not all(isfinite(x) for x in self.features) or not 0 <= self.yield_rate <= 1:
            raise ValueError("产率观测值越界")


@dataclass(frozen=True)
class Curve:
    material: str
    center: tuple[float, ...]
    scale: tuple[float, ...]
    limits: tuple[tuple[float, float], ...]
    params: tuple[float, ...]
    rate: float
    loss_radius: float
    count: int
    validation: int


@dataclass(frozen=True)
class Estimate:
    lot: str
    rate: float | None
    lower: float | None
    upper: float | None
    fit_group: str
    notice: str
