"""Closed class C switch.

This module does not read the environment or a data payload.
Opening the switch is a human decision (Q12), not a configuration key.
"""

CLASS_C_POLICY = "closed"
NAMED_REVIEWER = None  # Q13 is unanswered. Promotions do not run.

CLASS_C_USES = frozenset({"Settlement", "hedge", "trigger", "nature-unit"})


def class_c_policy() -> str:
    return CLASS_C_POLICY


def named_reviewer():
    return NAMED_REVIEWER
