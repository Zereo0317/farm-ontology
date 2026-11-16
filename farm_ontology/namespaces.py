"""Pinned vocabulary namespaces.

These are references. This repository does not vendor the upstream files
and does not invent file hashes for artefacts it did not download.
"""

IRI_BASE = "https://github.com/Zereo0317/farm-ontology/ns/"
IRI_BASE_STATUS = "provisional-not-a-final-domain"

SOSA = "http://www.w3.org/ns/sosa/"
SSN = "http://www.w3.org/ns/ssn/"
GEO = "http://www.opengis.net/ont/geosparql#"
TIME = "http://www.w3.org/2006/time#"
QUDT = "http://qudt.org/schema/qudt/"
UNIT = "http://qudt.org/vocab/unit/"
KIND = "http://qudt.org/vocab/quantitykind/"
PROV = "http://www.w3.org/ns/prov#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
AGROVOC = "http://aims.fao.org/aos/agrovoc/"

# QUDT local names used as references. The release TTL was not hashed.
UNIT_KM = UNIT + "KiloM"
UNIT_M = UNIT + "M"
UNIT_MM = UNIT + "MilliM"
UNIT_DEG = UNIT + "DEG"
UNIT_HA = UNIT + "HA"
UNIT_TONNE = UNIT + "TONNE"

KIND_LENGTH = KIND + "Length"
KIND_MASS = KIND + "Mass"
KIND_AREA = KIND + "Area"
KIND_ANGLE = KIND + "Angle"

# NVS P07 version 95 is the pin. Individual concept URIs are unresolved.
CF_P07_COLLECTION = "http://vocab.nerc.ac.uk/collection/P07/95/"
CF_P07_VERSION = "95"

MAIZE_AGROVOC = AGROVOC + "c_12332"
FAO_LABEL_LANGUAGES = frozenset({"en", "fr", "es", "ar", "ru", "zh"})
# Requested in Q17. No AGROVOC labels were fetched for these tags.
REQUESTED_LABEL_LANGUAGES = frozenset({"ja", "zh-TW", "zh-CN", "id", "th", "vi"})
CROP_ONTOLOGY = {
    "maize": "CO_322",
    "sorghum": "CO_324",
    "chickpea": "CO_338",
    "groundnut": "CO_337",
    "common bean": "CO_335",
    "potato": "CO_330",
    "banana": "CO_325",
}

EUDR_COMMODITIES = frozenset(
    {"cattle", "cocoa", "coffee", "oil palm", "rubber", "soya", "wood"}
)

TENURE_VALUES = frozenset(
    {"titled", "customary", "leased", "operator-only", "unknown"}
)
JOIN_RELATIONS = frozenset({"geo:sfWithin", "geo:sfIntersects"})
ERROR_METRICS = frozenset(
    {
        "rmse",
        "bias",
        "usersAccuracy",
        "producersAccuracy",
        "falseTriggerRate",
        "predictionInterval",
        "uncalibrated",
        "notApplicable",
    }
)
GAP_REASONS = frozenset({"cloud", "no-scene", "licence", "sensor-down"})
MIX_VALUES = frozenset({"mono", "mixed", "unknown"})
OVERLAP_DISPOSITIONS = frozenset(
    {"same-object", "shared-boundary", "split", "digitising-error"}
)
