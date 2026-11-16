"""Layer types that are in scope and not loaded.

Q15 livelihood zones and Q20 soil profiles. No geometries and no profile
rows are stored.
"""

from __future__ import annotations

from dataclasses import dataclass

LIVELIHOOD_MISSING = (
    "https://fews.net/data redirected to an explorer page and was not a zone file",
    "https://data.humdata.org/dataset/fews-net-livelihood-zones returned HTTP 202 with an empty body",
)

SOIL_MISSING = (
    "GloSIS OWL modules were not downloaded and are not imported",
    "ISRIC ISO 28258 README was fetched and states MIT; the Postgres schema was not loaded",
    "No soil profile rows are stored",
)


@dataclass(frozen=True)
class LivelihoodZoneLayer:
    loaded: bool = False

    def __post_init__(self) -> None:
        if self.loaded:
            raise ValueError("a livelihood-zone dataset was not fetched")


@dataclass(frozen=True)
class SoilProfile:
    """A SOSA-shaped slot. The material IRI, when set, is an ENVO reference."""

    feature_iri: str
    envo_material_iri: str | None = None
    observation_iris: tuple[str, ...] = ()
