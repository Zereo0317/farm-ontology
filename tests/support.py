import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from farm_ontology.build import grid_observation, kilometres, millimetres  # noqa: E402
from farm_ontology.model import Observation  # noqa: E402

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)
FIXTURES = ROOT / "fixtures" / "dry_run"


def load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def sample_grid(**changes) -> Observation:
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    end = datetime(2024, 6, 2, tzinfo=timezone.utc)
    availability = datetime(2024, 6, 2, tzinfo=timezone.utc)
    base = grid_observation(
        local="sample-cell",
        feature_local="sample-10km",
        resolution=kilometres(10),
        result=millimetres(12.5),
        phenomenon=(start, end),
        availability=availability,
        product_kind="rfe2",
    )
    if not changes:
        return base
    return Observation(**{**base.__dict__, **changes})
