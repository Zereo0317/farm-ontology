"""One Planet scene pixel.

The stored record is the opened public disaster scene pixel.
The item id is 20261105_162410_82_24d8.
The datetime is 2026-11-05T16:24:10.823737Z.
The tiff datetime is not the stored datetime.
The citation is the visual cog URL.
https://data.source.coop/ is not the citation.
https://www.planet.com/account/ is not the citation.
A trailing slash is not the citation.
The column is 6260.
The row is 4454.
The band values are 109, 130, 113, 255.
The printed sample order is red, green, blue, unassociated_alpha.
The licence is CC-BY-NC-4.0.
CC-BY-NC-4.0 does not set financial use to true.
permits_financial_use stays false.
Class C stays closed.
This is one pixel of a public disaster scene.
It is not the Biratori field.
It is not a yield.
It is not a price.
It is not a trade.
content_length is not stored.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PLANET_SCENE_PIXEL_URL = (
    "https://data.source.coop/planet/disasterdata/"
    "galapagos-santa-cruz-floods-2026-10-30/post-event/"
    "planetscope-2026-11-05/items/20261105_162410_82_24d8/"
    "20261105_162410_82_24d8_visual.tif"
)

ITEM_ID = "20261105_162410_82_24d8"
DATETIME = "2026-11-05T16:24:10.823737Z"
COLUMN = 6260
ROW = 4454
BAND_VALUES = (109, 130, 113, 255)
SAMPLE_ORDER = ("red", "green", "blue", "unassociated_alpha")
LICENCE = "CC-BY-NC-4.0"
FORBIDDEN_LABELS = frozenset({
    "yield",
    "price",
    "trade",
    "biratori",
    "completed harvest",
    "settlement",
})


def record_scene_pixel(
    directory,
    *,
    citation_url=None,
    label=None,
    permits_financial_use=None,
    class_c_policy=None,
    column=None,
    row=None,
    band_values=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a scene pixel is not a yield, a price, or a trade")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    if column is not None or row is not None or band_values is not None:
        raise ValueError("the pixel is not replaced")
    citation = str(citation_url).strip()
    if citation != PLANET_SCENE_PIXEL_URL:
        raise ValueError("citation_url is not the visual cog")
    header = {
        "item_id": ITEM_ID,
        "datetime": DATETIME,
        "citation_url": citation,
        "column": COLUMN,
        "row": ROW,
        "band_values": list(BAND_VALUES),
        "sample_order": list(SAMPLE_ORDER),
        "licence": LICENCE,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "planet-scene-pixel.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
