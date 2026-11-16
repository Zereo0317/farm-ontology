# Farm decision record

A small, tested record for cultivated-land facts. It stores what was known, at which native spatial support, under which licence, with which error mark, and which uses were refused.

It does not estimate yield. It does not issue a hedge ratio, a parametric trigger, or a nature unit. Class C stays closed.

The IRI base `https://github.com/Zereo0317/farm-ontology/ns/` stays **provisional** until seges.ai serves the namespace. The intended domain is seges.ai. No DNS record was written.

## Run the tests

Python 3.11 or newer. No third-party packages.

```powershell
cd farm-ontology
$env:GCLOUD_CONFIGURATION = "segescloud"
$env:GCP_PROJECT = "seges-ai"
python -m unittest discover -s tests -t . -v
```

The tests set those variables themselves when an adapter plan needs them. Unset variables make a cloud plan fail closed.

## Field record

The walk is `docs/field-playbook.md`. The steps are `docs/field-sop.md`. Later dates are `docs/later-routes.md`.

```powershell
cd web
npm install
npm run dev
python -m farm_ontology.mcp_stdio
```

The field page is `http://127.0.0.1:3000/`. The page and the MCP server write `field-notes/obs-*.json`. Notes are `field-notes/notes/note-*.json`. The page does not call weather or a map. Class C stays closed. GPS accuracy stays unknown unless you pass metres. The command-line shape check writes only the file you name. It is not the page record:

```powershell
python -m farm_ontology.fieldkit --dry-run --out fixtures\field\dry-run-not-a-farm.json
```

## GCP

The adapters read the gcloud configuration name and the project id from the environment. They do not embed credentials, tokens, or service-account keys.

| Variable | Value for this deployment |
| --- | --- |
| `GCLOUD_CONFIGURATION` | `segescloud` |
| `GCP_PROJECT` or `EE_PROJECT` | `seges-ai` |

A recorded check from 2026-11-16 is in `fixtures/dry_run/gcp-preflight.json`. Earth Engine's API was enabled on `seges-ai`, and a read of the algorithms catalog returned HTTP 200. The commercial versus noncommercial registration type was not returned, so it is stored as `unknown`. Unknown registration forces `permitsFinancialUse` false and caps the use class at Screening. No Export task was started.

## What is shipped

- Local classes for a boundary version, holding, operator, right-holder, season, cropping, spatial join, error, licence, method, human gate, and refusal (`ontology/fd-decision.ttl`).
- SOSA/SSN, GeoSPARQL, OWL Time, QUDT, PROV-O, and SKOS as namespace references. AGROVOC is a `skos:exactMatch` label only. Nothing from the non-commercial or unlicensed list in the spec is imported.
- Refusal rules that run before a record is stored. A 10 km (or any gridded) value cannot be stored as a measurement of a farm boundary. A join does not rewrite native resolution.
- Synthetic identity. Unknown tenure stays `unknown`. The operator is not copied into the right-holder.
- `factsAt` and `associatedAt`. A fact is returned only when its availability time is at or before the query time, no visible revision supersedes it, and, for a forecast, its issue time is at or before the query time.
- Fail-closed adapters for Earth Engine history, Open-Meteo (`jma_msm`, `ecmwf_ifs`), and CWA F-D0047 / WRF. Issue time and native support stay on the forecast. Contract fixtures under `fixtures/dry_run/` are marked `captured_live: false`.

One live Open-Meteo sample is recorded in `fixtures/live/open_meteo_jma_msm_2026-11-16.json`. The point is 23.5°N, 121.0°E. The model is `jma_msm`. The stored spatial support is the published JMA MSM grid, **0.05° (about 5 km)**, not the 0.4 ha parcel. The stored hour is precipitation `0.0 mm` for 2026-11-16T04:00Z–05:00Z, issued at 2026-11-16T03:00Z and received at 2026-11-16T10:23:44Z. The plain forecast endpoint was called and does not return a model-run time, so its body is not the stored observation. No API key is in the repository. The test suite does not call the network. Class C stays closed.

Upstream ontology files are not in git. Pins and the local-module SHA-256 are in `vocabulary-manifest.json`. QUDT unit IRIs are references; the release file was not downloaded and no hash is claimed for it. Crop Ontology ids in the manifest are the recorded pins: maize CO_322, sorghum CO_324, chickpea CO_338, groundnut CO_337, common bean CO_335, potato CO_330, and banana CO_325. Trait repositories CO_320, CO_321, and CO_334 are named and not cloned. Soybean field notes use CO_336. No ontology titled Musa was found. The precipitation observed-property IRI is a local id marked unresolved against CF standard-name collection P07 version 95.

There is no SPARQL server and no OWL DL reasoner. The recorded store choice is Apache Jena. It is not deployed. The in-memory store is the development record.

## What stays closed

These decisions are recorded. The software keeps the missing files out and the closed switches closed.

| ID | While it is open |
| --- | --- |
| Q1 | The GitHub IRI base above is provisional, not a final domain. |
| Q2 | ENVO v2026-10-23 is pinned and not imported. |
| Q3 | OGC AIM is not vendored. |
| Q4 | Crop ids are recorded, including soybean CO_336 on a field note. Trait repositories CO_320, CO_321, and CO_334 are not cloned. No ontology titled Musa was found. |
| Q5 | Plant Stress Ontology is not shipped. |
| Q6 | The store choice is Apache Jena. It is not deployed. Development uses memory. |
| Q7 | Livestock is in scope. ATOL and EOL OWL files were not downloaded. |
| Q8 | No African, Indian, or Indonesian meteorological service is named or ingested. |
| Q9 | Open-Meteo `permitsFinancialUse` stays false. |
| Q10 | No listed instrument and no basis. Hedge and trigger annotations do not load. |
| Q11 | Financial use stays false. Earth Engine registration type on this project is `unknown`. |
| Q12 | `fd:classCPolicy` is `closed`. Data and environment variables cannot open it. |
| Q13 | The reviewer name defaults to empty. A matching non-empty name can store a class B gate. The observation stays at Screening. Class C stays closed. |
| Q14 | Synthetic parties only. Real personal data does not load. |
| Q15 | No livelihood-zone layer. |
| Q16 | No AgriStack extract is ingested. |
| Q17 | No AGROVOC labels outside English, French, Spanish, Arabic, Russian, and Chinese. The shipped example label is English. |
| Q18 | Phone-point accuracy stays unknown. Six decimal places do not count as metres. |
| Q19 | Unmatched local names are not forced into maize. |
| Q20 | No soil-profile store. |
| Q21 | 宇辰 洪 is named as the independent validator. Pay and trading affiliates were not supplied. An internal score is not an error bar. |

## What a memo will not say

A memo from `factsAt` can say what was knowable at a time, at what support, under what licence, with what error mark, and which promotions were refused. It does not state a parcel yield, a parcel rainfall, a hedge ratio, or a nature unit. Hectare weather is unsupported unless a calibrated sensor observation is present. This build has no live sensor feed.
