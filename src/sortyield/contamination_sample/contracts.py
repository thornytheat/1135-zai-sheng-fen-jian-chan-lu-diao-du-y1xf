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
class Audit:
    lot: str
    slices: int
    mass: int
    impurity: float | None
    moisture: float | None
    upper_impurity: float | None
    excluded: int
    coverage: float

    @property
    def approved_samples(self):
        return self.slices >= 3 and self.coverage >= 0.95 and self.impurity is not None


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
