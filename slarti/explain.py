from __future__ import annotations

CHECKS: dict[str, str] = {
    "OWN-1": (
        "A schema class declares no owning container.\n"
        "Remedy: add 'annotations: {owner: <likec4-element-id>}' to the class, and list the "
        "class under that element's 'owns' metadata."
    ),
    "OWN-2": (
        "A schema class names an owner that is not an element in the LikeC4 model.\n"
        "Remedy: correct the owner annotation, or add the element to the model."
    ),
    "OWN-3": (
        "A schema class names an owner that does not claim it back.\n"
        "Remedy: add the class name to that element's 'owns' metadata."
    ),
    "OWN-4": (
        "A LikeC4 element claims an entity that is not a class in the schema.\n"
        "Remedy: remove the entity from 'owns', or add the class to the schema."
    ),
    "OWN-5": (
        "A schema class is claimed by more than one container.\n"
        "Remedy: leave the class in exactly one element's 'owns' metadata."
    ),
    "REG-1": (
        "A constraint points at an enforcer that does not exist.\n"
        "Remedy: create the enforcer, correct the ref, or record the rule as "
        "'enforced_by: none' with a reason."
    ),
    "REG-2": (
        "A SHACL shape exists that no constraint references.\n"
        "Remedy: add a constraint with enforced_by.kind=shacl_shape and that ref, or delete "
        "the shape."
    ),
    "REG-3": (
        "A constraint is unenforced but gives no reason.\n"
        "Remedy: add a 'reason' explaining why the rule cannot be mechanically enforced."
    ),
    "REG-4": "A constraint ID is declared twice.\nRemedy: give every constraint a unique ID.",
    "REG-5": (
        "A constraint cites a decision the document never records.\n"
        "Remedy: document the decision, or drop the 'decision' field."
    ),
    "REG-6": (
        "A declared negative fixture is missing, unloadable, or conforms.\n"
        "Remedy: make the fixture exist and violate the declared shape."
    ),
    "REG-7": (
        "A negative fixture fails, but the report never names the declared shape.\n"
        "Remedy: narrow the fixture, or correct the declared ref."
    ),
    "DOC-1": (
        "A generated region is stale relative to its source.\n"
        "Remedy: run 'slarti docs' and commit the result."
    ),
    "DOC-2": (
        "A generated diagram differs from what the model generates — it was hand-edited.\n"
        "Remedy: never edit files under the diagrams directory; run 'slarti docs'."
    ),
    "DOC-3": (
        "A region marker is unbalanced, or names a region slarti cannot fill.\n"
        "Remedy: balance the markers; use constraints, unverified, ownership or diagram:<view>."
    ),
    "DOC-4": (
        "A constraint in the registry has no row in the generated tables.\n"
        "Remedy: this is a generation bug in slarti; report it with the registry entry."
    ),
    "ENV-1": (
        "A delegated tool is missing or outside its supported version range.\n"
        "Remedy: run 'slarti doctor' and install a version inside the range."
    ),
}


def explain(identifier: str) -> str | None:
    """Full description of a check ID, with its remedy."""
    return CHECKS.get(identifier.upper())
