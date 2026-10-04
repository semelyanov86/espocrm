"""Shared helpers of the stage 05.2 acceptance tests (charts, dashlets, key metrics — D-105…D-115) on the local stand.

They reuse the world of the stage 05.1 tests (tests/stage05_1/fixture.py: synthetic users, roles, the reference
invoices with known sums, cleanup registered before anything is created). Expected values of the reference data:

  status     invoices          SUM grandTotal     status → account (SUM)
  Created    i1 i3 i6 i7 (4)   31000.00           a1 20000.00 (i1 i7), a2 10999.99 (i3), a3 0.01 (i6)
  Sent       i2 i4 (2)          3469.62           a1 1000.50 (i2), a2 2469.12 (i4)
  Approved   i5 (1)                7.77           a3 7.77 (i5)
  all        7                 34477.39
"""
import sys
from decimal import ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage05_1"))
from fixture import (D, Client, World, admin_credentials, all_of, cond, drill_down, espo_console, flat,  # noqa: E402,F401
                     label, list_ids, must, num, reference_data, run, sql)

BY_STATUS = {"Created": (4, D("31000.00")), "Sent": (2, D("3469.62")), "Approved": (1, D("7.77"))}
BY_STATUS_ACCOUNT = {("Created", "a1"): D("20000.00"), ("Created", "a2"): D("10999.99"), ("Created", "a3"): D("0.01"),
                     ("Sent", "a1"): D("1000.50"), ("Sent", "a2"): D("2469.12"), ("Approved", "a3"): D("7.77")}
SUM_ALL = D("34477.39")


def avg8(total, count):
    """A quotient as the module computes it (D-93): 8 decimals, rounded half away from zero."""
    return (D(total) / D(count)).quantize(D("1e-8"), rounding=ROUND_HALF_UP)


def progress(values):
    """Running MIN / plain AVG / MAX of the category values (D-107); None before the first value."""
    out = {"MIN": [], "AVG": [], "MAX": []}
    seen = []
    for value in values:
        if value is not None:
            seen.append(value)
        out["MIN"].append(min(seen) if seen else None)
        out["MAX"].append(max(seen) if seen else None)
        out["AVG"].append(avg8(sum(seen), len(seen)) if seen else None)
    return out


def summaries(world, owner, name, groups, charts, **extra):
    """A summaries report of the reference invoices (COUNT and SUM of the total)."""
    return world.report(owner, name, type="summaries", entityType="Invoice", groups=groups,
                        aggregates=[{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"}],
                        filters=all_of(world.name_filter()), charts=charts, **extra)


def metric_values(client, set_id):
    return client.get(f"ReportMetricSet/{set_id}/values")


def flat_where(where):
    """Where items as query parameters of the core list (GET <entity>?where[0][type]=…)."""
    return flat("where", where)
