"""Farm decision record.

The product is the audit trail. Class C (settlement, hedge, trigger, nature
unit) ships closed and cannot be opened by data.
"""

REASONER = "none"

from farm_ontology.policy import class_c_policy

__all__ = ["REASONER", "class_c_policy"]
