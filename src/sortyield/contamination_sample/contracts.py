from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, order=True)
class Cut:
    specimen: str
    stratum: str
    grams: int
    unwanted: int
    water: int

    def __post_init__(self):
        if not self.specimen or not self.stratum or self.grams <= 0:
            raise ValueError("样本或切面缺失")
        if (
            min(self.unwanted, self.water) < 0
            or self.unwanted + self.water > self.grams
        ):
            raise ValueError("杂质及水分质量超出总重")


@dataclass(frozen=True)
class StratumReading:
    """One stratum's measured impurity and moisture, kept as a real pairing."""

    stratum: str
    grams: int
    impurity: float
    moisture: float

    def __post_init__(self):
        if not self.stratum or self.grams <= 0:
            raise ValueError("分层读数缺失")
        if not all(isfinite(x) and 0 <= x <= 1 for x in (self.impurity, self.moisture)):
            raise ValueError("分层读数越界")


@dataclass(frozen=True)
class Audit:
    lot: str
    slices: int
    mass: int
    impurity: float | None
    moisture: float | None
    upper_impurity: float | None
    excluded: int
    coverage: float
    strata: tuple[StratumReading, ...] = ()

    @property
    def approved_samples(self):
        return self.slices >= 3 and self.coverage >= 0.95 and self.impurity is not None

    @property
    def full_coverage(self):
        """All planned strata measured, so every layer can be scored on its own."""
        return bool(self.strata) and self.coverage >= 0.95


@dataclass(frozen=True)
class SamplingPlan:
    strata: tuple[str, ...] = ("上", "中", "下")
    minimum_grams: int = 300

    def __post_init__(self):
        if (
            self.minimum_grams <= 0
            or not self.strata
            or len(set(self.strata)) != len(self.strata)
        ):
            raise ValueError("抽检层或最小称样量无效")
