"""Closed class C switch.

Class C is not opened here. A settlement, hedge, trigger, or nature-unit
gate is delegated to ontolaw's human gate
(src/ontolaw/human_gate.py). This module does not read a payload that
could open the switch.
"""

from farm_ontology.config import named_reviewer_placeholder

CLASS_C_POLICY = "closed"
CLASS_C_USES = frozenset({"Settlement", "hedge", "trigger", "nature-unit"})

# Q10. No instrument is selected. The user will choose with Hiroki Tomiyasu
# in Hokkaido. A separate note is being researched.
INSTRUMENT = None

# Q21. An internal score is not an independent error.
INDEPENDENT_VALIDATOR = "宇辰 洪"

# Q18. The target is named. No backtest has run, and no GPS metres are invented.
ACCURACY_TARGET = "yield for long and short futures and stocks"
BACKTEST_RAN = False


def class_c_policy() -> str:
    return CLASS_C_POLICY


def named_reviewer():
    name = named_reviewer_placeholder()
    return name or None
