"""Planet visual COG refetch.

One ranged response from the visual cog already cited.
The citation is the visual cog URL.
https://data.source.coop/ is not the citation.
https://www.planet.com/account/ is not the citation.
A trailing slash is not the citation.
The request range is bytes 0-4095.
The response status was 206.
206 is the ranged response status, not a measurement.
The stored Content-Type is the Content-Type header.
The stored ETag is the ETag header.
The stored Last-Modified is the Last-Modified header.
Last-Modified is the object header, not a period and not a scene datetime.
The stored printed text is bytes 8 through 190 of the response body.
The stored tiff datetime is 2026:11:05 16:24:10.
That string is the printed tiff datetime.
2026-11-05T16:24:10 is not the printed tiff datetime.
The stored crs name is WGS 84 / UTM zone 15S.
That string is the printed name.
A latitude, a longitude, an easting, and a northing are not stored.
A coordinate is not invented.
A pixel is not stored.
Content-Length is not stored.
Content-Range is not stored.
Date, Connection, CF-Ray, CF-Cache-Status, Accept-Ranges,
Access-Control-Allow-Origin, Cache-Control, Server, server-timing,
x-amz-id-2, x-amz-request-id, x-amz-server-side-encryption,
x-amz-version-id, x-request-id, Speculation-Rules, Report-To, Nel,
alt-svc, and the access-control response headers are not stored.
The licence was not opened.
A copied licence is not stored.
permits_financial_use stays false.
Class C stays closed.
This is not the Biratori field.
It is not a yield.
It is not a price.
It is not a trade.
This module is not called from a field save.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

PLANET_VISUAL_COG_URL = (
    "https://data.source.coop/planet/disasterdata/"
    "galapagos-santa-cruz-floods-2026-10-30/post-event/"
    "planetscope-2026-11-05/items/20261105_162410_82_24d8/"
    "20261105_162410_82_24d8_visual.tif"
)

STATUS = 206
CONTENT_TYPE = "image/tiff; application=geotiff; profile=cloud-optimized"
ETAG = '"6e91cd4baa2e47346ecc6e0743910dbc-20"'
LAST_MODIFIED = "Mon, 09 Nov 2026 17:00:50 GMT"
PRINTED = (
    "GDAL_STRUCTURAL_METADATA_SIZE=000140 bytes\n"
    "LAYOUT=IFDS_BEFORE_DATA\n"
    "BLOCK_ORDER=ROW_MAJOR\n"
    "BLOCK_LEADER=SIZE_AS_UINT4\n"
    "BLOCK_TRAILER=LAST_4_BYTES_REPEATED\n"
    "KNOWN_INCOMPATIBLE_EDITION=NO\n "
)
TIFF_DATETIME = "2026:11:05 16:24:10"
CRS_NAME = "WGS 84 / UTM zone 15S"
RANGE = "bytes=0-4095"
FORBIDDEN_LABELS = frozenset({
    "yield",
    "price",
    "trade",
    "biratori",
    "completed harvest",
    "settlement",
})


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open(request):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs()
    opener = urllib.request.build_opener(
        _RefuseRedirect,
        urllib.request.HTTPSHandler(context=context),
    )
    return opener.open(request, timeout=60)


def fetch_visual_cog(citation_url: str):
    request = urllib.request.Request(
        citation_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Range": RANGE,
            "Accept": "*/*",
        },
        method="GET",
    )
    try:
        with _open(request) as response:
            status = response.status
            url = response.geturl()
            content_type = response.headers.get("Content-Type")
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")
            content_range = response.headers.get("Content-Range")
            body = response.read()
    except urllib.error.HTTPError as error:
        raise ValueError("the visual cog response was not stored") from error
    printed = PRINTED.encode("ascii")
    if status != STATUS or url != citation_url:
        raise ValueError("the visual cog response was not stored")
    if content_type != CONTENT_TYPE or etag != ETAG or last_modified != LAST_MODIFIED:
        raise ValueError("the visual cog response was not stored")
    if content_range is None or not str(content_range).startswith("bytes 0-4095/"):
        raise ValueError("the visual cog response was not stored")
    if len(body) != 4096 or body[:4] != b"II*\x00" or body[8:191] != printed:
        raise ValueError("the visual cog response was not stored")
    if TIFF_DATETIME.encode("ascii") not in body or CRS_NAME.encode("ascii") not in body:
        raise ValueError("the visual cog response was not stored")
    return body


def record_visual_cog(
    directory,
    *,
    citation_url=None,
    label=None,
    permits_financial_use=None,
    class_c_policy=None,
    column=None,
    row=None,
    band_values=None,
    latitude=None,
    longitude=None,
    easting=None,
    northing=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a visual cog is not a yield, a price, or a trade")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    if column is not None or row is not None or band_values is not None:
        raise ValueError("a pixel is not stored")
    if (
        latitude is not None
        or longitude is not None
        or easting is not None
        or northing is not None
    ):
        raise ValueError("a coordinate is not invented")
    citation = str(citation_url).strip()
    if citation != PLANET_VISUAL_COG_URL:
        raise ValueError("citation_url is not the visual cog")
    fetch_visual_cog(citation)
    header = {
        "citation_url": citation,
        "status": STATUS,
        "headers": {
            "Content-Type": CONTENT_TYPE,
            "ETag": ETAG,
            "Last-Modified": LAST_MODIFIED,
        },
        "printed": PRINTED,
        "tiff_datetime": TIFF_DATETIME,
        "crs_name": CRS_NAME,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "planet-visual-cog.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
