# Apex smoke matrix (foundation for the UA sweep; run from repo root)
#
# Expected final statuses after redirects on https://seges.ai
# (verified live 2026-11-27, worker 643a4ce3+).

# (path, expected_INTERMEDIATE_status, note) — the locale tool-escape is a
# 302 by design (locale prefix -> bare path); the smoke asserts the HOP,
# and curls one level deeper only when the expectation is 200-on-bare.
matrix = [
    # (path, expected_final_status, note, follow)
    ("/", 302, "landing bare root redirects (locale negotiate)", False),
    ("/zh-TW", 200, "traditional landing", False),
    ("/zh-CN", 200, "simplified landing", False),
    ("/en", 200, "english landing", False),
    ("/ja", 200, "japanese landing", False),
    ("/th", 200, "thai landing", False),
    ("/zh-TW/pitch/reliable", 302, "locale tool-escape hop", False),
    ("/ja/walk", 302, "locale tool-escape hop", False),
    ("/th/fieldday", 302, "locale tool-escape hop", False),
    ("/zh-CN/report/biratori-1119", 302, "locale tool-escape hop", False),
    ("/walk", 200, "bare walk (public)", False),
    ("/fieldday", 200, "bare fieldday (public)", False),
    ("/pitch/reliable", 200, "bare pitch (public)", False),
    ("/farm", 307, "unauth farm -> login chain", False),
]

import json
import subprocess
import sys
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(NoRedirect)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) seges-smoke"}

failures = []
for path, expected, note, follow in matrix:
    url = f"https://seges.ai{path}"
    try:
        try:
            resp = opener.open(urllib.request.Request(url, headers=UA), timeout=30)
            code = resp.getcode()
        except urllib.error.HTTPError as e:
            code = e.code
        status = "OK" if code == expected else f"MISMATCH(got {code})"
        if code != expected:
            failures.append((path, expected, code))
    except Exception as e:
        failures.append((path, expected, f"exc {e}"))
        status = "EXCEPTION"
    print(f"{path:36} expect={expected} got={code} {status}")

if failures:
    print(f"\n{len(failures)} FAILURES")
    sys.exit(1)
print("\nAPEX SMOKE: ALL GREEN")
