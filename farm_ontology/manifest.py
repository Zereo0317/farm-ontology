"""Vocabulary manifest. Upstream ontologies are referenced, not vendored."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "vocabulary-manifest.json"

FORBIDDEN_MARKERS = (
    "glosis-ld/glosis",
    "SDG-InterfaceOntology/sdgio",
    "AgriculturalSemantics/SEOnt",
    "bioversity/Crop-Ontology",
    "xriss/agrovoc-json",
    "FAO-SID/GloSIS",
    "YaoXinZhi/Rice-Trait-Ontology",
    "global-soil-intelligence/gsip",
    "sweetAll",
    "plant-stress-ontology",
    "atol",
    "eol",
    "geosparql-next",
    "sosa-2023-editors-draft",
    "-edit.owl",
)


def load_manifest(path: Path | None = None) -> dict:
    target = path or MANIFEST_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def manifest_violations(document: dict) -> list[str]:
    problems = []
    imports = document.get("imports") or []
    if imports:
        problems.append("the shipped manifest imports nothing; Q2 and the non-commercial list stay out")
    blob = json.dumps(document.get("imports") or []).lower()
    for marker in FORBIDDEN_MARKERS:
        if marker.lower() in blob:
            problems.append(f"forbidden import marker {marker}")
    if document.get("class_c_policy") != "closed":
        problems.append("class C policy in the manifest must be closed")
    if document.get("reasoner") != "none":
        problems.append("this build runs no OWL DL reasoner")
    pins = document.get("pins") or []
    for pin in pins:
        if pin.get("vendored"):
            problems.append(f"pin {pin.get('id')} is marked vendored")
        if pin.get("sha256") not in (None, "") and pin.get("role") != "local-module":
            # A hash is allowed only when this repository computed it.
            if not pin.get("hash_computed_here"):
                problems.append(f"pin {pin.get('id')} claims a hash this build did not compute")
    local = document.get("local_module") or {}
    if local.get("vendored_upstream"):
        problems.append("the local module must not vendor upstream ontologies")
    return problems


def manifest_ok(document: dict) -> bool:
    return not manifest_violations(document)
