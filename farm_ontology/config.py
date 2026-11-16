"""Runtime settings. Credentials are never read or stored here."""

from __future__ import annotations

import os
from dataclasses import dataclass


class MissingConfig(Exception):
    """An adapter asked for GCP settings and the environment did not supply them."""


@dataclass(frozen=True)
class Settings:
    gcloud_configuration: str
    gcp_project: str


def load_settings() -> Settings:
    """Read the gcloud configuration name and the GCP project from the environment.

    Expected values for this deployment are configuration ``segescloud`` and
    project ``seges-ai``. They are not embedded as silent defaults.
    """
    configuration = os.environ.get("GCLOUD_CONFIGURATION", "").strip()
    project = (
        os.environ.get("GCP_PROJECT", "").strip()
        or os.environ.get("EE_PROJECT", "").strip()
    )
    missing = []
    if not configuration:
        missing.append("GCLOUD_CONFIGURATION")
    if not project:
        missing.append("GCP_PROJECT or EE_PROJECT")
    if missing:
        raise MissingConfig(
            "Refusing to plan a cloud call. Set " + " and ".join(missing) + "."
        )
    return Settings(gcloud_configuration=configuration, gcp_project=project)
