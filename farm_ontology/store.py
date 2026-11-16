"""Append-only record. Refusals are stored. Forbidden records are not."""

from __future__ import annotations

from datetime import datetime

from farm_ontology.build import mint
from farm_ontology.model import (
    BoundaryVersion,
    CommitResult,
    Cropping,
    FitActivity,
    Holding,
    JitteredSurveyPoint,
    LabelLink,
    Observation,
    Overlap,
    Party,
    Refusal,
    Season,
    SpatialJoin,
)
from farm_ontology.namespaces import (
    EUDR_COMMODITIES,
    FAO_LABEL_LANGUAGES,
    REQUESTED_LABEL_LANGUAGES,
    JOIN_RELATIONS,
    OVERLAP_DISPOSITIONS,
)
from farm_ontology.policy import CLASS_C_USES, class_c_policy, named_reviewer
from farm_ontology.rules import (
    Violation,
    boundary_violations,
    class_b_blockers,
    cropping_violations,
    observation_violations,
)
from farm_ontology.timeutil import ensure_utc

POLICY_KEYS = ("classCPolicy", "class_c_policy", "fd:classCPolicy", "FD_CLASS_C_POLICY")


class Store:
    def __init__(self) -> None:
        if class_c_policy() != "closed":
            raise RuntimeError("class C policy must ship closed")
        self.observations: dict[str, Observation] = {}
        self.boundaries: dict[str, BoundaryVersion] = {}
        self.holdings: dict[str, Holding] = {}
        self.parties: dict[str, Party] = {}
        self.seasons: dict[str, Season] = {}
        self.croppings: dict[str, Cropping] = {}
        self.joins: dict[str, SpatialJoin] = {}
        self.overlaps: dict[str, Overlap] = {}
        self.labels: dict[str, LabelLink] = {}
        self.survey_points: dict[str, JitteredSurveyPoint] = {}
        self.fits: dict[str, FitActivity] = {}
        self.refusals: list[Refusal] = []
        self.accepted_gates: list[dict] = []
        self._seq = 0

    def _next(self, kind: str) -> str:
        self._seq += 1
        return mint(kind, f"{kind}-{self._seq}")

    def _refuse(
        self, rule_id: str, input_entity: str, attempted_change: str, at: datetime
    ) -> CommitResult:
        at = ensure_utc(at, "refusal time")
        refusal = Refusal(
            iri=self._next("refusal"),
            rule_id=rule_id,
            time=at,
            input_entity=input_entity,
            attempted_change=attempted_change,
        )
        self.refusals.append(refusal)
        return CommitResult(ok=False, iri=None, refusal=refusal)

    def _refuse_all(
        self, violations: list[Violation], input_entity: str, at: datetime
    ) -> CommitResult:
        first = None
        for item in violations:
            result = self._refuse(item.rule_id, input_entity, item.detail, at)
            if first is None:
                first = result
        return first if first is not None else CommitResult(True, input_entity, None)

    def add_observation(self, obs: Observation, *, at: datetime) -> CommitResult:
        if obs.iri in self.observations or obs.iri in self.joins:
            return self._refuse(
                "R-parallel", obs.iri, "an IRI is not recycled", at
            )
        previous = None
        if obs.revision_of is not None:
            previous = self.observations.get(obs.revision_of)
            if previous is None:
                return self._refuse(
                    "R-parallel",
                    obs.iri,
                    "a reprocess cites a previous version that is still in the store",
                    at,
                )
        violations = observation_violations(
            obs, set(self.boundaries), previous, set(self.survey_points)
        )
        if violations:
            return self._refuse_all(violations, obs.iri, at)
        self.observations[obs.iri] = obs
        return CommitResult(ok=True, iri=obs.iri, refusal=None)

    def add_boundary(self, boundary: BoundaryVersion, *, at: datetime) -> CommitResult:
        if boundary.iri in self.boundaries:
            return self._refuse(
                "R-parallel", boundary.iri, "a boundary IRI is not recycled", at
            )
        violations = boundary_violations(boundary)
        if violations:
            return self._refuse_all(violations, boundary.iri, at)
        self.boundaries[boundary.iri] = boundary
        return CommitResult(ok=True, iri=boundary.iri, refusal=None)

    def add_holding(self, holding: Holding, *, at: datetime) -> CommitResult:
        if not holding.links:
            return self._refuse(
                "R-foi", holding.iri, "a holding links to one or more boundary versions", at
            )
        for boundary_iri, interval in holding.links:
            if boundary_iri not in self.boundaries:
                return self._refuse(
                    "R-foi", holding.iri, "a holding link cites a missing boundary", at
                )
            if interval.end <= interval.start:
                return self._refuse(
                    "R-property", holding.iri, "a holding link needs a real interval", at
                )
        self.holdings[holding.iri] = holding
        return CommitResult(ok=True, iri=holding.iri, refusal=None)

    def add_party(self, party: Party, *, at: datetime) -> CommitResult:
        if party.personal_data:
            return self._refuse(
                "R-personal",
                party.iri,
                "real persons stay out until a lawful basis exists (Q14)",
                at,
            )
        if party.role not in {"operator", "right-holder"}:
            return self._refuse("R-tenure", party.iri, "unknown party role", at)
        self.parties[party.iri] = party
        return CommitResult(ok=True, iri=party.iri, refusal=None)

    def copy_operator_to_right_holder(
        self, operator_iri: str, *, at: datetime
    ) -> CommitResult:
        return self._refuse(
            "R-tenure",
            operator_iri,
            "the operator is not copied into the right-holder; unknown stays unknown",
            at,
        )

    def add_season(self, season: Season, *, at: datetime) -> CommitResult:
        name = season.calendar_name.strip().lower()
        if name in {"calendar-year", "gregorian-year", "calendar year"}:
            return self._refuse(
                "R-property",
                season.iri,
                "a calendar year is not a season",
                at,
            )
        if season.end <= season.start:
            return self._refuse("R-property", season.iri, "season interval is empty", at)
        if not season.calendar_source:
            return self._refuse(
                "R-property", season.iri, "the calendar source is an entity", at
            )
        self.seasons[season.iri] = season
        return CommitResult(ok=True, iri=season.iri, refusal=None)

    def add_cropping(self, cropping: Cropping, *, at: datetime) -> CommitResult:
        violations = cropping_violations(cropping, set(self.boundaries))
        if cropping.season not in self.seasons:
            violations.append(
                Violation("R-property", "cropping cites a season that is not in the store")
            )
        if violations:
            return self._refuse_all(violations, cropping.iri, at)
        self.croppings[cropping.iri] = cropping
        return CommitResult(ok=True, iri=cropping.iri, refusal=None)

    def add_join(
        self,
        *,
        observation: str,
        boundary: str,
        relation: str,
        crs: str,
        generated_at: datetime,
        at: datetime,
    ) -> CommitResult:
        if relation not in JOIN_RELATIONS:
            return self._refuse(
                "R-join-type", observation, "join relation must be sfWithin or sfIntersects", at
            )
        if observation not in self.observations:
            return self._refuse(
                "R-join-type", observation, "a join cites a missing observation", at
            )
        if boundary not in self.boundaries:
            return self._refuse(
                "R-foi", boundary, "a join cites a missing boundary", at
            )
        if not crs:
            return self._refuse("R-support", observation, "the join names its CRS", at)
        iri = self._next("join")
        if iri in self.observations:
            return self._refuse("R-join-type", iri, "a join IRI collided with an observation", at)
        self.joins[iri] = SpatialJoin(
            iri=iri,
            observation=observation,
            boundary=boundary,
            relation=relation,
            crs=crs,
            generated_at=ensure_utc(generated_at, "join generated_at"),
            activity=self._next("activity"),
        )
        # The observation object is not replaced. Its resolution stays put.
        return CommitResult(ok=True, iri=iri, refusal=None)

    def add_overlap(
        self,
        *,
        boundary_a: str,
        boundary_b: str,
        season: str,
        area_ha: float,
        method: str,
        disposition: str | None,
        at: datetime,
    ) -> CommitResult:
        if boundary_a not in self.boundaries or boundary_b not in self.boundaries:
            return self._refuse("R-overlap", boundary_a, "overlap cites a missing boundary", at)
        if season not in self.seasons:
            return self._refuse("R-overlap", season, "overlap cites a missing season", at)
        if area_ha <= 0:
            return self._refuse("R-overlap", boundary_a, "overlap area must be stored and positive", at)
        if not method:
            return self._refuse("R-overlap", boundary_a, "the overlap method is named", at)
        if disposition is not None and disposition not in OVERLAP_DISPOSITIONS:
            return self._refuse("R-overlap", boundary_a, "unknown overlap disposition", at)
        iri = self._next("overlap")
        self.overlaps[iri] = Overlap(
            iri=iri,
            boundary_a=boundary_a,
            boundary_b=boundary_b,
            season=season,
            area_ha=area_ha,
            method=method,
            disposition=disposition,
        )
        return CommitResult(ok=True, iri=iri, refusal=None)

    def distinct_plots_reading(
        self, boundary_a: str, boundary_b: str, season: str, *, at: datetime
    ) -> CommitResult:
        matches = [
            item
            for item in self.overlaps.values()
            if item.season == season
            and {item.boundary_a, item.boundary_b} == {boundary_a, boundary_b}
        ]
        if any(item.disposition is None for item in matches):
            return self._refuse(
                "R-overlap",
                boundary_a,
                "stored overlap without a disposition cannot be read as distinct plots at class B",
                at,
            )
        return CommitResult(ok=True, iri=boundary_a, refusal=None)

    def add_label(
        self,
        *,
        local_iri: str,
        concept_iri: str,
        relation: str,
        language: str,
        extra_grant: bool,
        at: datetime,
    ) -> CommitResult:
        if relation != "skos:exactMatch":
            return self._refuse(
                "R-agrovoc",
                local_iri,
                "AGROVOC links are skos:exactMatch, not owl:sameAs or owl:equivalentClass",
                at,
            )
        if language in REQUESTED_LABEL_LANGUAGES:
            return self._refuse(
                "R-language",
                local_iri,
                "Japanese, zh-TW, zh-CN, Indonesian, Thai, and Vietnamese need a fetched label source; none is attached",
                at,
            )
        if language not in FAO_LABEL_LANGUAGES and not extra_grant:
            return self._refuse(
                "R-language",
                local_iri,
                "shipped AGROVOC labels stay inside the six FAO languages",
                at,
            )
        iri = self._next("label")
        self.labels[iri] = LabelLink(
            iri=iri,
            local_iri=local_iri,
            concept_iri=concept_iri,
            relation=relation,
            language=language,
        )
        return CommitResult(ok=True, iri=iri, refusal=None)

    def add_jittered_survey_point(self, note: str, *, at: datetime) -> CommitResult:
        if "0-5 km" not in note and "privacy" not in note.lower():
            return self._refuse(
                "R-accuracy",
                "survey-point",
                "this constructor is only for a privacy-displaced survey point",
                at,
            )
        iri = self._next("survey-point")
        self.survey_points[iri] = JitteredSurveyPoint(
            iri=iri, note=note, personal_data=False
        )
        return CommitResult(ok=True, iri=iri, refusal=None)

    def add_fit(
        self, *, used: tuple[str, ...], error_cut: str | None, at: datetime
    ) -> CommitResult:
        if error_cut is not None and error_cut in used:
            return self._refuse(
                "R-split-sample",
                error_cut,
                "one crop-cut entity cannot both train the fit and be its error statement",
                at,
            )
        iri = self._next("fit")
        self.fits[iri] = FitActivity(iri=iri, used=used, error_cut=error_cut)
        return CommitResult(ok=True, iri=iri, refusal=None)

    def record_eudr_syntax(
        self,
        boundary_iri: str,
        *,
        commodity: str,
        production_date: datetime | None,
    ) -> bool:
        boundary = self.boundaries.get(boundary_iri)
        if boundary is None:
            return False
        claimed = _eudr_syntax(boundary, commodity, production_date)
        if claimed:
            self.boundaries[boundary_iri] = BoundaryVersion(
                **{**boundary.__dict__, "eudr_syntactic_claim": True}
            )
        return claimed

    def delete(self, iri: str, *, at: datetime) -> CommitResult:
        return self._refuse(
            "R-parallel",
            iri,
            "previous entities stay readable; this store does not delete them",
            at,
        )

    def add_annotation(self, kind: str, *, at: datetime) -> CommitResult:
        if kind == "nature-unit":
            return self._refuse(
                "R-nature",
                kind,
                "no method entity exists for additionality, leakage, or permanence",
                at,
            )
        if kind in {"hedge", "trigger"}:
            return self._refuse(
                "R-instrument",
                kind,
                "no named listed instrument and no measured basis are in the store",
                at,
            )
        if kind in CLASS_C_USES:
            return self._refuse("R-classC", kind, "class C policy is closed", at)
        return self._refuse("R-classC", kind, "unknown annotation", at)

    def ingest_payload(self, payload: dict, *, at: datetime) -> CommitResult:
        for key in POLICY_KEYS:
            if key in payload and payload[key] != "closed":
                return self._refuse(
                    "R-classC",
                    str(payload.get("iri") or "payload"),
                    "class C policy cannot be set by data",
                    at,
                )
        use_class = payload.get("useClass")
        if use_class in CLASS_C_USES:
            rule = "R-nature" if use_class == "nature-unit" else (
                "R-instrument" if use_class in {"hedge", "trigger"} else "R-classC"
            )
            return self._refuse(
                rule,
                str(payload.get("iri") or "payload"),
                "class C cannot be set by data while the policy is closed",
                at,
            )
        annotation = payload.get("annotation")
        if annotation:
            return self.add_annotation(str(annotation), at=at)
        if "observation" in payload:
            return self.add_observation(payload["observation"], at=at)
        return self._refuse(
            "R-property",
            "payload",
            "the payload did not contain a record this ingest path accepts",
            at,
        )

    def promote(
        self,
        observation_iri: str,
        *,
        to_class: str,
        reviewer: str | None,
        checklist: dict,
        region: str,
        crop: str,
        at: datetime,
    ) -> CommitResult:
        if to_class in CLASS_C_USES:
            return self._refuse(
                "R-classC",
                observation_iri,
                "a gate to Settlement, hedge, trigger, or a nature unit fails while class C is closed",
                at,
            )
        if reviewer and (
            reviewer.endswith("gserviceaccount.com")
            or reviewer.startswith("service-account")
        ):
            return self._refuse(
                "R-gate",
                observation_iri,
                "a service account cannot be the reviewer",
                at,
            )
        if named_reviewer() is None:
            return self._refuse(
                "R-gate",
                observation_iri,
                "Q13 placeholder FARM_NAMED_REVIEWER is empty; promotions do not run",
                at,
            )
        obs = self.observations.get(observation_iri)
        if obs is None:
            return self._refuse("R-gate", observation_iri, "missing observation", at)
        blockers = class_b_blockers(obs, region, crop)
        if blockers:
            return self._refuse_all(blockers, observation_iri, at)
        if not checklist:
            return self._refuse("R-gate", observation_iri, "the checklist is missing", at)
        return self._refuse(
            "R-gate",
            observation_iri,
            "promotions stay off; naming a reviewer does not open a gate in this build",
            at,
        )


def _eudr_syntax(
    boundary: BoundaryVersion, commodity: str, production_date: datetime | None
) -> bool:
    if commodity not in EUDR_COMMODITIES:
        return False
    if boundary.accuracy_unknown or boundary.accuracy_m is None:
        return False
    if production_date is None:
        return False
    if boundary.coordinate_decimals < 6:
        return False
    if boundary.area_ha is not None and boundary.area_ha > 4:
        if not boundary.wkt.lstrip().upper().startswith("POLYGON"):
            return False
    return True
