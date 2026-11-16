"""Center brain and one brain per farm.

Q8. Asia and Africa only. This module does not start a multi-agent runtime
and does not call a network.
"""

from __future__ import annotations

from dataclasses import dataclass

REGIONS = frozenset({"Asia", "Africa"})


@dataclass(frozen=True)
class FarmBrain:
    farm_id: str
    region: str

    def __post_init__(self) -> None:
        if self.region not in REGIONS:
            raise ValueError("a farm brain is in Asia or Africa")
        if not self.farm_id or "/" in self.farm_id:
            raise ValueError("farm id is one path segment")


@dataclass(frozen=True)
class CenterBrain:
    farms: tuple[FarmBrain, ...] = ()

    def orchestrate(self, farm_id: str) -> FarmBrain:
        for farm in self.farms:
            if farm.farm_id == farm_id:
                return farm
        raise KeyError(farm_id)
