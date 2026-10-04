#!/usr/bin/env python3
"""Synthetic fixture for the stage-05.2 browser check (charts, dashlets, key metrics; Playwriter, evidence.md).

  python3 tests/stage05_2/ui_fixture.py create   → the users and records of the stage-05.1 fixture, plus reports with
                                                   charts, a key-metrics set and a dashboard tab of the manager;
                                                   passwords → <private>/ui-users.env (600)
  python3 tests/stage05_2/ui_fixture.py delete   → removes the sets, reports, folders, records, team and users

<private> is /data/itvolga/espo-private/stand/evidence/stage05.2 (UI_FIXTURE_DIR overrides it), mode 700. Records and
users are those of tests/stage05_1/ui_fixture.py («SYNTH-REP …», synth-rep-manager/-manager2/-access/-deputy). Reports
of the manager (public): «SYNTH-REP Счета по статусам» (summaries by status, SUM of the total and COUNT, a bar chart,
main filter «ответственный»), «SYNTH-REP Счета: статус → контрагент» (two levels, stacked bars on the axis
«group 1 → group 2»), «SYNTH-REP Позиции: товар × месяц» (matrix, a line), «SYNTH-REP Счета список» (tabular with
totals); a private tabular report of manager2 for the «no access» check. The set «SYNTH-REP показатели» has report
rows and a system-filter row, the set «SYNTH-REP набор второго» of manager2 a row of their private report; the manager's dashboard gets a tab with the dashlets «Отчёт» and «Ключевые показатели». Only ids and
counts are printed.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/stage05.2")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage05_1"))
import ui_fixture as base  # noqa: E402
from fixture import Client, admin_credentials  # noqa: E402

TAG = base.TAG


def name_filter():
    return {"type": "and", "items": [{"field": "name", "where": {"type": "startsWith", "attribute": "name",
                                                                  "value": TAG}}]}


def create():
    base.create()
    state = json.loads(base.STATE.read_text(encoding="utf-8"))
    admin = Client(*admin_credentials())
    manager, manager2 = state["users"]["manager"], state["users"]["manager2"]
    reports = {}

    def report(key, owner, body):
        payload = base.must(admin.post("Report", {"accessType": "public", "assignedUserId": owner,
                                                  "filters": name_filter(), **body}))
        reports[key] = payload["id"]
        state.setdefault("reports", {})[key] = payload["id"]
        base.save_state(state)

    report("byStatus", manager, {
        "name": f"{TAG} Счета по статусам", "type": "summaries", "entityType": "Invoice",
        "groups": [{"field": "status", "direction": "asc"}],
        "aggregates": [{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"}],
        "charts": {"title": "Счета", "position": "top", "items": [{"type": "bar", "aggregate": "SUM:grandTotal"}]},
        "dashboard": {"filterField": "assignedUser", "mode": "chart"}})
    report("statusAccount", manager, {
        "name": f"{TAG} Счета: статус → контрагент", "type": "summaries", "entityType": "Invoice",
        "groups": [{"field": "status", "direction": "asc"}, {"field": "account", "direction": "asc"}],
        "aggregates": [{"function": "COUNT"}, {"function": "SUM", "field": "grandTotal"}],
        "charts": {"axis": "group1group2", "position": "bottom", "collapseTable": True,
                   "items": [{"type": "stackedBar", "aggregate": "SUM:grandTotal"}]}})
    report("matrix", manager, {
        "name": f"{TAG} Позиции: товар × месяц", "type": "matrix", "entityType": "InvoiceItem",
        "groups": [{"field": "product", "direction": "asc"},
                   {"field": "invoice.dateInvoiced", "granularity": "month", "direction": "asc"}],
        "aggregates": [{"function": "SUM", "field": "quantity"}],
        "filters": {"type": "and", "items": [{"field": "invoice.name", "where": {"type": "startsWith",
                                                                                 "attribute": "name", "value": TAG}}]},
        "charts": {"items": [{"type": "line", "aggregate": "SUM:quantity"}]}})
    report("list", manager, {
        "name": f"{TAG} Счета список", "type": "tabular", "entityType": "Invoice",
        "columns": ["name", "account.name", "status", "grandTotal"],
        "totals": [{"column": "grandTotal", "functions": ["SUM", "AVG"]}], "rowLimit": 20})
    report("private2", manager2, {
        "name": f"{TAG} Личный отчёт второго", "type": "tabular", "entityType": "Invoice", "accessType": "private",
        "columns": ["name", "grandTotal"]})

    manager_client = Client(*base_credentials("manager"))
    metric = base.must(manager_client.post("ReportMetricSet", {"name": f"{TAG} показатели", "rows": [
        {"label": "Сумма счетов", "source": "report", "reportId": reports["list"], "function": "SUM",
         "column": "grandTotal"},
        {"label": "Число счетов", "source": "report", "reportId": reports["list"], "function": "COUNT"},
        {"label": "Открытые сделки", "source": "filter", "entityType": "Opportunity",
         "filter": {"kind": "system", "name": "open"}},
    ]}))
    state["metricSet"] = metric["id"]
    # A set of manager2 with a row of their private report: other viewers get «нет доступа» in that row.
    other = base.must(Client(*base_credentials("manager2")).post("ReportMetricSet", {
        "name": f"{TAG} набор второго", "rows": [
            {"label": "Личный отчёт второго", "source": "report", "reportId": reports["private2"], "function": "SUM",
             "column": "grandTotal"},
            {"label": "Число счетов", "source": "report", "reportId": reports["list"]}]}))
    state["metricSet2"] = other["id"]
    base.save_state(state)

    layout = [{"id": "itvTab", "name": f"{TAG} дашборд", "layout": [
        {"id": "itvReport", "name": "Report", "x": 0, "y": 0, "width": 2, "height": 4},
        {"id": "itvMetrics", "name": "ReportMetrics", "x": 2, "y": 0, "width": 2, "height": 4},
    ]}]
    options = {"itvReport": {"title": "Счета по статусам", "reportId": reports["byStatus"],
                             "reportName": f"{TAG} Счета по статусам", "mode": ""},
               "itvMetrics": {"title": "Ключевые показатели", "metricSetId": metric["id"],
                              "metricSetName": f"{TAG} показатели"}}
    base.must(admin.put(f"Preferences/{manager}", {"dashboardLayout": layout, "dashletsOptions": options}))
    print(json.dumps({"reports": reports, "metricSet": metric["id"]}, indent=2))


def base_credentials(key):
    values = {}

    for line in base.USERS_ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()

    return values[f"UI_{key.upper()}_USERNAME"], values[f"UI_{key.upper()}_PASSWORD"]


def delete():
    admin = Client(*admin_credentials())
    state = json.loads(base.STATE.read_text(encoding="utf-8"))
    user_ids = list(state.get("users", {}).values())
    if user_ids:
        params = {"where[0][type]": "in", "where[0][attribute]": "createdById", "select": "id", "maxSize": 200}
        params.update({f"where[0][value][{i}]": uid for i, uid in enumerate(user_ids)})
        for row in base.must(admin.get("ReportMetricSet", **params))["list"]:
            admin.delete(f"ReportMetricSet/{row['id']}")
    for rid in state.get("reports", {}).values():
        admin.delete(f"Report/{rid}")
    base.delete()


if __name__ == "__main__":
    {"create": create, "delete": delete}[sys.argv[1]]()
