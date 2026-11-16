"""Local names stay unmatched. Q19. Nothing is mapped to maize."""

from __future__ import annotations

LOCAL_NAME_GAPS = (
    "No local-name table is loaded.",
    "Unmatched names are not mapped to maize.",
)


def match_local_name(name: str) -> None:
    del name
    return None
