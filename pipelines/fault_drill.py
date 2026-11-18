"""THROWAWAY controlled-fault entry for the Error Reporting verification drill.

Task-10 deliverable 2 requires proving that an escaping Python traceback
inside a Cloud Run JOB forms a Cloud Error Reporting error group. This
module is the instrument: it does nothing except raise one deliberate,
distinctively-named exception. Run it as a job entry point
(``--args=python,-m,pipelines.fault_drill``).

It is NOT part of the service surface, records nothing, and is safe to
delete once the drill evidence exists (keep it: re-running the drill
after logging/alerting changes benefits from a stable signature).
"""

from __future__ import annotations

FAULT_MARKER = "controlled fault drill (task-10): intentional single-shot error"


def explode() -> None:
    """Raise the drill fault. Signature is stable so the ERR group is comparable across drills."""
    raise RuntimeError(
        f"{FAULT_MARKER}; if this group appears in Cloud Error Reporting, "
        "exception->group wiring is proven for job-based runtimes"
    )


def main() -> int:
    explode()
    return 0  # unreachable; the raise IS the deliverable


if __name__ == "__main__":
    raise SystemExit(main())
