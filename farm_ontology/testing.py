"""Hermetic test helpers.

House rule (2026-11-18): tests that fetch the live internet are opt-in.
They fetch live pages AND hard-assert recorded values; when the publisher
revises data or merely advances a day, such tests break for reasons that
have nothing to do with the code under test. CI and local default runs
therefore stay offline; opt in with FARM_ONLINE_TESTS=1.
"""

from __future__ import annotations

import os
import unittest

ONLINE_ENV = "FARM_ONLINE_TESTS"


def online_gate():
    """Decorator: skip the wrapped test unless FARM_ONLINE_TESTS is truthy."""
    enabled = os.environ.get(ONLINE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}

    def decorate(function):
        return unittest.skipUnless(enabled, f"live fetch; set {ONLINE_ENV}=1")(function)

    return decorate
