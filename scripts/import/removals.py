"""Records gone from the source (stage 06.4, docs/migration/import.md «Дельта», owner's answers 2026-10-12): which live
target records of the run's entity types the delta removes, and the mass-removal rail. Pure: the plan and the target
inventory (source keys only, no values) in, removal operations out.

A source key of the run is every operation planned or held (a record held by an error or waiting for a later stage is
live in the source and never removed). Task, Call and Meeting share the Calendar key space: a live record whose key the
source now has as another activity type is retired by the upsert of that type (RecordWriter), not removed here. A user
gone from the source is deactivated by the writer; an inactive one is already in that state. Removals run after every
upsert, children before their owners (reverse spec.ORDER: allocations before payments and documents), except that a
finance document goes before its items: its removal takes them in its transaction (the core's cascade, marked by the
same hook), and a document the writer keeps keeps them (review of stage 06.4, round 3).
"""
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

import spec
import spec_finance

EVENT_TYPES = ("Task", "Call", "Meeting")
# Refuse the run before any write when a type would lose more than max(floor, share of its live records) or every one
# of them (owner's answer 2026-10-12): `--allow-mass-removal` lets it through.
RAIL = {"floor": 25, "share": Decimal("0.05")}
DOCUMENT_OF = {item: document for document, item, *_ in spec_finance.DOCUMENTS.values()}  # finance item → document


@dataclass(frozen=True)
class Removal:
    """A `remove` operation (writer protocol 3): the type and the source key only."""
    entityType: str
    vtigerId: int
    module: str = "(removal)"
    file = None
    skip = None
    pending = None

    @property
    def key(self):
        return f"remove:{self.entityType}:{self.vtigerId}"

    def payload(self):
        return {"op": "remove", "key": self.key, "entityType": self.entityType, "vtigerId": self.vtigerId}


@dataclass
class RemovalPlan:
    ops: list = field(default_factory=list)          # Removal, children before owners
    by_type: dict = field(default_factory=dict)      # type → {"live", "source", "remove"}
    retyped: Counter = field(default_factory=Counter)  # "Call": live records retired by their new activity type
    refused: list = field(default_factory=list)      # types beyond the rail

    def report(self):
        return {"by_type": self.by_type, "retyped": dict(self.retyped), "refused": self.refused,
                "operations": len(self.ops)}


def source_keys(plan):
    keys = {}
    for op in plan.ops + plan.held:
        if isinstance(op.vtigerId, int):
            keys.setdefault(op.entityType, set()).add(op.vtigerId)
    for entity, key in getattr(plan, "held_keys", ()):  # e.g. the allocation of a held payment
        keys.setdefault(entity, set()).add(key)
    return keys


def blocked_types(orphans, selected=None):
    """Entity types of the modules with live source records the reader cannot see (no base row, D-145
    `live_without_base_row`): their absence from the plan proves nothing — no removal of those types."""
    modules = set(selected or spec.SCOPE)
    out = set()
    for module, src in spec.SOURCES.items():
        if module in modules and (orphans or {}).get(src.setype or module):
            out |= set(spec.MODULE_ENTITIES.get(module, ()))
    return out


def plan_removals(plan, inventory, types, key_range, rail=None, blocked=()):
    """`inventory`: entity type → the writer's inventory answer ({"live", "deleted", "inactive"?}); `types`: the types
    whose every source module is in the run (spec.owned_types); `blocked`: types not removed (blocked_types). Only live
    records with a key in `key_range`."""
    rail = RAIL if rail is None else rail
    source = source_keys(plan)
    events = set().union(*(source.get(t, set()) for t in EVENT_TYPES))
    order = {e: i for i, e in enumerate(spec.ORDER)}
    rank = {e: -order[DOCUMENT_OF[e]] + 0.5 if e in DOCUMENT_OF else -i for e, i in order.items()}
    out = RemovalPlan()
    for entity in sorted(types, key=lambda t: (rank.get(t, 1), t)):
        if entity in spec.NATURAL_KEY_TYPES or entity not in inventory or entity in blocked:
            continue
        inv = inventory[entity]
        live = sorted(k for k in inv.get("live", []) if key_range[0] <= k <= key_range[1])
        inactive = set(inv.get("inactive", []))
        keys = source.get(entity, set())
        remove = []
        for k in live:
            if k in keys:
                continue
            if entity in EVENT_TYPES and k in events:
                out.retyped[entity] += 1
                continue
            if entity == "User" and k in inactive:
                continue
            remove.append(k)
        out.by_type[entity] = {"live": len(live), "source": len(keys), "remove": len(remove)}
        out.ops += [Removal(entity, k) for k in remove]
        limit = max(Decimal(rail["floor"]), rail["share"] * len(live))
        if remove and (len(remove) > limit or not keys):
            out.refused.append(entity)
    return out
