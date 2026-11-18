"""WS2 pipeline-authored modules living beside the workers' entry point.

These belong to the scheduled-ingestion workstream only. Anything that
becomes a governed ``Observation`` still flows exclusively through the
existing ``farm_ontology`` store/adapters; this package adds no store
and no transport of its own.
"""
