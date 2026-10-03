#!/usr/bin/env python3
"""Build EspoCRM enum options, Russian labels and the Vtiger value dictionary (D-19) for stages 03 and 04.2–04.5.

Usage: build_value_maps.py OUTDIR [--check]

Inputs (private audit run, outside Git): OUTDIR/41_picklist_config.tsv (configured picklists in Vtiger order),
OUTDIR/43_sp_labels.tsv (SalesPlatform ru_ru labels of picklist values), OUTDIR/14_picklist_values.tsv
(values used by live records). Only vocabulary (picklist values and their labels) is written to Git.

Outputs (module Itvolga):
- Resources/metadata/vtigerValueMap/<Entity>.json — per enum field: options, source picklists and the
  dictionary `map[source]{vtiger value -> EspoCRM key}` used by the importer (stage 06);
- `options` / `default` of the same fields in Resources/metadata/entityDefs/<Entity>.json;
- option labels in Resources/i18n/ru_RU/<Entity>.json.
With --check nothing is written; the exit code is 1 if any output would change.

Rules (docs/migration/decisions.md, D-38; dictionary approved by the owner 2026-09-30, Q-32):
1. Vocabulary = configured picklist values (Vtiger sort order) plus values used by live records but missing in
   the picklist (webhooks wrote such values). Empty source values stay empty ("" option) — never defaulted.
2. A value stored in English keeps its key; its label is what SalesPlatform showed (ru_ru language file).
3. A Russian value equal to the label of an English key of the same picklist is a synonym: it is merged into
   that key (the raw value survives in vtigerData). Other Russian values are keys as they are.
4. Where EspoCRM logic depends on its own keys (statuses), `core` maps the Vtiger key to the EspoCRM key and the
   EspoCRM option gets the Vtiger label, so users see the same words as before.
"""
import csv
import json
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "custom/Espo/Modules/Itvolga/Resources"
STANDARD_SALUTATIONS = ["Mr.", "Ms.", "Mrs.", "Dr.", "Prof."]

# entity, field, picklists (label lookup order), used-value sources (module.field), options
# core: Vtiger key -> EspoCRM key; extra: EspoCRM keys added after the vocabulary; empty: force/forbid "".
ENUMS = [
    dict(entity="Account", field="industry", picklists=["industry"],
         used=["Accounts.industry", "Leads.industry"], empty=True),
    dict(entity="Account", field="type", picklists=["accounttype"], used=["Accounts.accounttype"], empty=True),
    dict(entity="Account", field="cRating", picklists=["rating"], used=["Accounts.rating", "Leads.rating"], empty=True),
    dict(entity="Lead", field="source", picklists=["leadsource"],
         used=["Leads.leadsource", "Contacts.leadsource", "Potentials.leadsource"], empty=True),
    dict(entity="Lead", field="status", picklists=["leadstatus"], used=["Leads.leadstatus"],
         core={"Not Contacted": "New"}, extra=["Converted"], default="New",
         not_actual=["Converted", "Junk Lead", "Lost Lead"]),
    dict(entity="Lead", field="cPriority", picklists=["cf_1107"], used=["Leads.cf_1107"], empty=True),
    dict(entity="Lead", field="salutationName", picklists=["salutationtype"], used=[], empty=True,
         only=STANDARD_SALUTATIONS),
    dict(entity="Contact", field="salutationName", picklists=["salutationtype"], used=[], empty=True,
         only=STANDARD_SALUTATIONS),
    dict(entity="Opportunity", field="stage", picklists=["sales_stage"], used=["Potentials.sales_stage"],
         empty=False, default_first=True, core={"Переговоры": "Negotiation or Review"},
         order=["Qualification", "Needs Analysis", "Value Proposition", "Id. Decision Makers", "Perception Analysis",
                "Proposal or Price Quote", "Negotiation or Review", "Closed Won", "Closed Lost"]),
    dict(entity="Opportunity", field="cOpportunityType", picklists=["opportunity_type"],
         used=["Potentials.opportunity_type"], empty=True),
    dict(entity="Case", field="status", picklists=["ticketstatus"], used=["HelpDesk.ticketstatus"], empty=False,
         core={"Open": "New", "In Progress": "Assigned", "Wait For Response": "Pending", "Closed": "Closed"},
         default="New", not_actual=["Closed"]),
    dict(entity="Case", field="priority", picklists=["ticketpriorities"], used=["HelpDesk.ticketpriorities"],
         empty=False, core={"Высокий": "High"}, default="Normal", order=["Low", "Normal", "High", "Urgent"]),
    dict(entity="Case", field="type", picklists=["ticketcategories"], used=["HelpDesk.ticketcategories"], empty=True),
    dict(entity="Case", field="cSeverity", picklists=["ticketseverities"], used=["HelpDesk.ticketseverities"],
         empty=True),
    # Tasks come from Calendar (taskstatus) and from Events of type «Письмо» (eventstatus, D-24).
    dict(entity="Task", field="status", picklists=["taskstatus"], used=["Calendar.taskstatus"], empty=False,
         core={"In Progress": "Started"}, extra=["Canceled"], default="Not Started",
         extra_sources={"Events.eventstatus": {"Held": "Completed", "Planned": "Planned", "Not Held": "Canceled"}},
         not_actual=["Completed", "Canceled", "Deferred"]),
    dict(entity="Task", field="priority", picklists=["taskpriority"], used=["Calendar.taskpriority", "Events.taskpriority"],
         core={"Medium": "Normal"}, empty=True, default="Normal", order=["Low", "Normal", "High", "Urgent"],
         extra=["Urgent"]),
    dict(entity="Call", field="status", picklists=["eventstatus"], used=["Events.eventstatus"], empty=False,
         default="Planned", extra_sources={"PBXManager.callstatus": {"completed": "Held", "*": "Not Held"}}),
    dict(entity="Meeting", field="status", picklists=["eventstatus"], used=["Events.eventstatus"], empty=False,
         default="Planned"),
    dict(entity="KnowledgeBaseArticle", field="status", picklists=["faqstatus"], used=["Faq.faqstatus"], empty=False,
         core={"Reviewed": "In Review", "Obsolete": "Archived"}, default="Draft"),
    dict(entity="Project", field="status", picklists=["projectstatus"], used=["Project.projectstatus"], empty=True),
    dict(entity="Project", field="type", picklists=["projecttype"], used=["Project.projecttype"], empty=True),
    dict(entity="Project", field="priority", picklists=["projectpriority"], used=["Project.projectpriority"],
         empty=True),
    dict(entity="Project", field="progress", picklists=["progress"], used=["Project.progress"], empty=True,
         sort_numeric=True),
    dict(entity="ProjectTask", field="status", picklists=["projecttaskstatus"],
         used=["ProjectTask.projecttaskstatus"], empty=True),
    dict(entity="ProjectTask", field="priority", picklists=["projecttaskpriority"],
         used=["ProjectTask.projecttaskpriority"], empty=True),
    dict(entity="ProjectTask", field="type", picklists=["projecttasktype"], used=["ProjectTask.projecttasktype"],
         empty=True),
    dict(entity="ProjectTask", field="progress", picklists=["projecttaskprogress"],
         used=["ProjectTask.projecttaskprogress"], empty=True, sort_numeric=True),
    dict(entity="Product", field="unit", picklists=["service_usageunit", "usageunit"],
         used=["Services.service_usageunit", "Products.usageunit"], empty=True),
    dict(entity="Product", field="category", picklists=["servicecategory"], used=["Services.servicecategory"],
         empty=True),
    # Stage 04.2: an empty source status stays empty; new documents start as Created.
    dict(entity="Quote", field="status", picklists=["quotestage"], used=["Quotes.quotestage"], empty=True,
         default="Created"),
    dict(entity="SalesOrder", field="status", picklists=["sostatus"], used=["SalesOrder.sostatus"], empty=True,
         default="Created"),
    # Stage 04.3: the configured list keeps AutoCreated (not used) and Cancel (presence=1, used).
    dict(entity="Invoice", field="status", picklists=["invoicestatus"], used=["Invoice.invoicestatus"], empty=True,
         default="Created"),
    # Stage 04.4: direction and method get the keys of the contract (finance-contract.md §11: Приход → incoming,
    # Expense → outgoing; Наличные → cash, Cashless Transfer → bank); defaults are the Vtiger field defaults
    # (vtiger_field.defaultvalue: Приход, Cashless Transfer, Executed). An empty status stays empty and counts as paid
    # (Q-37, D-49); «Запланирован» is a stored value of its own (no English key of the list has that label).
    dict(entity="Payment", field="direction", picklists=["pay_type"], used=["SPPayments.pay_type"], empty=False,
         core={"Приход": "incoming", "Expense": "outgoing"}, default="incoming"),
    dict(entity="Payment", field="method", picklists=["type_payment"], used=["SPPayments.type_payment"], empty=True,
         core={"Наличные": "cash", "Cashless Transfer": "bank"}, default="bank"),
    dict(entity="Payment", field="status", picklists=["spstatus"], used=["SPPayments.spstatus"], empty=True,
         default="Executed"),
    # Stage 04.5: an empty act status stays empty; new acts start as Created (vtiger_field.defaultvalue).
    dict(entity="Act", field="status", picklists=["sp_actstatus"], used=["Act.sp_actstatus"], empty=True,
         default="Created"),
]
# Fields whose dictionary is fixed by the source semantics (no picklist table).
STATIC = {
    ("Lead", "status"): {"Leads.converted": {"1": "Converted"}},
    ("Document", "status"): {"Documents.filestatus": {"1": "Active", "0": "Draft"}},
    ("Email", "status"): {"Emails.email_flag": {"SENT": "Sent", "MailManager": "Archived"}},
    ("Call", "direction"): {"PBXManager.direction": {"inbound": "Inbound", "outbound": "Outbound"}},
    ("Task", "cTaskType"): {"Events.activitytype": {"Письмо": "Письмо"}},
    ("Product", "type"): {"(module)": {"Products": "product", "Services": "service"}},
    ("Quote", "taxMode"): {"Quotes.hdnTaxType": {"individual": "individual", "group": "group",
                                                  "group_tax_inc": "group_tax_inc"}},
    ("SalesOrder", "taxMode"): {"SalesOrder.hdnTaxType": {"individual": "individual", "group": "group",
                                                          "group_tax_inc": "group_tax_inc"}},
    ("Invoice", "taxMode"): {"Invoice.hdnTaxType": {"individual": "individual", "group": "group",
                                                    "group_tax_inc": "group_tax_inc"}},
    ("Act", "taxMode"): {"Act.hdnTaxType": {"individual": "individual", "group": "group",
                                            "group_tax_inc": "group_tax_inc"}},
}
STATIC_OPTIONS = {
    ("Task", "cTaskType"): (["", "Письмо"], {"Письмо": "Письмо"}, ""),
    ("Product", "type"): (["product", "service"], {"product": "Товар", "service": "Услуга"}, "service"),
}
# Vtiger default probabilities of its stages (approved by the owner 2026-09-30, Q-32).
PROBABILITY = {"Qualification": 20, "Needs Analysis": 25, "Value Proposition": 30, "Id. Decision Makers": 40,
               "Perception Analysis": 50, "Proposal or Price Quote": 65, "Negotiation or Review": 80,
               "Closed Won": 100, "Closed Lost": 0}

# SalesPlatform labels that were mistranslated or clumsy; corrected by the owner's decision (2026-09-30, Q-32).
# Key: (entity, field, option key) -> label shown in EspoCRM.
LABEL_FIXES = {
    ("Account", "industry", "Retail"): "Розничная торговля",            # SalesPlatform: «Недвижимость»
    ("Account", "industry", "Hospitality"): "Гостиничный бизнес",       # «Скорая помощь»
    ("Account", "industry", "Not For Profit"): "Некоммерческие организации",
    ("Account", "industry", "Government"): "Государственный сектор",
    ("Account", "industry", "Banking"): "Банковское дело",
    ("Account", "industry", "Engineering"): "Инжиниринг",
    ("Account", "industry", "Environmental"): "Экология",
    ("Account", "industry", "Media"): "СМИ",
    ("Lead", "source", "Self Generated"): "Собственная инициатива",
    ("Lead", "source", "Word of mouth"): "Сарафанное радио",
    ("Lead", "source", "Public Relations"): "Связи с общественностью",
    ("Lead", "status", "New"): "Не связывались",
    ("Lead", "status", "Contacted"): "Есть контакт",
    ("Lead", "status", "Pre Qualified"): "Предварительно квалифицирован",
    ("Lead", "status", "Qualified"): "Квалифицирован",
    ("Lead", "status", "Junk Lead"): "Нецелевое обращение",
    ("Lead", "status", "Lost Lead"): "Потерянное обращение",
    ("Opportunity", "stage", "Qualification"): "Квалификация",           # «Оценка»
    ("Opportunity", "stage", "Needs Analysis"): "Анализ потребностей",   # «Нуждается в анализе»
    ("Opportunity", "stage", "Value Proposition"): "Ценностное предложение",
    ("Opportunity", "stage", "Id. Decision Makers"): "Поиск ЛПР",
    ("Opportunity", "stage", "Perception Analysis"): "Анализ восприятия",
    ("Opportunity", "stage", "Proposal or Price Quote"): "Ценовое предложение",
    ("Opportunity", "stage", "Negotiation or Review"): "Переговоры",
    ("Opportunity", "stage", "Closed Won"): "Закрыта успешно",
    ("Opportunity", "stage", "Closed Lost"): "Закрыта неудачно",
    ("Case", "status", "Assigned"): "В работе",
    ("Case", "priority", "Urgent"): "Срочный",
    ("Case", "type", "Small Problem"): "Небольшая проблема",             # «Средняя проблема»
    ("Task", "status", "Started"): "В работе",
    ("Task", "status", "Deferred"): "Отложено",
    ("Task", "status", "Pending Input"): "Ожидает информации",
    ("KnowledgeBaseArticle", "status", "In Review"): "На рассмотрении",
    ("KnowledgeBaseArticle", "status", "Archived"): "В архиве",
    ("Project", "status", "completed"): "Завершён",
    ("Project", "status", "on hold"): "Приостановлен",
    ("Project", "status", "waiting for feedback"): "Ожидание обратной связи",
    ("ProjectTask", "status", "Open"): "Открыта",
    ("ProjectTask", "status", "In Progress"): "В работе",
    ("ProjectTask", "status", "Completed"): "Завершена",
    ("ProjectTask", "status", "Deferred"): "Отложена",
    ("ProjectTask", "status", "Canceled"): "Отменена",
    ("Product", "unit", "Lb"): "фунт",                                   # «кг»
    ("Product", "unit", "Sq Ft"): "кв. фут",                             # «м2»
    ("Product", "unit", "Pieces"): "штуки",
    ("Product", "unit", "Incidents"): "Инциденты",
    ("Product", "category", "Training"): "Обучение",
    ("Lead", "salutationName", "Mr."): "Г-н", ("Contact", "salutationName", "Mr."): "Г-н",
    ("Lead", "salutationName", "Ms."): "Г-жа", ("Contact", "salutationName", "Ms."): "Г-жа",
    ("Lead", "salutationName", "Mrs."): "Г-жа (замужем)", ("Contact", "salutationName", "Mrs."): "Г-жа (замужем)",
    ("Lead", "salutationName", "Dr."): "Д-р", ("Contact", "salutationName", "Dr."): "Д-р",
}
# English keys whose SalesPlatform label meant something else: a Russian value equal to that old label is NOT merged
# into the key, because users picked it for the meaning of the label (e.g. «Недвижимость» = real estate, not Retail).
NO_MERGE = {("industry", "Retail"), ("industry", "Hospitality")}


def read_rows(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            yield line.rstrip("\n").split("\t")


def load(outdir):
    config = defaultdict(list)
    for i, p in enumerate(read_rows(outdir / "41_picklist_config.tsv")):
        if len(p) == 5 and p[0] == "picklist":
            order = int(p[3]) if p[3].lstrip("-").isdigit() else 0
            config[p[1]].append((order, i, p[2]))
    config = {pl: [v for _, _, v in sorted(values)] for pl, values in config.items()}  # Vtiger sortorderid
    labels = {}
    for p in read_rows(outdir / "43_sp_labels.tsv"):
        if len(p) == 4 and p[0] != "pl" and p[3]:
            labels[(p[0], p[1])] = p[3]
    used = defaultdict(OrderedDict)
    for p in read_rows(outdir / "14_picklist_values.tsv"):
        if len(p) == 5:
            used[f"{p[0]}.{p[1]}"][p[3]] = int(p[4])
    return config, labels, used


def clean(value):
    return value.strip()


def build_enum(spec, config, labels, used):
    core = spec.get("core", {})
    vocabulary, label_of = [], {}
    for pl in spec["picklists"]:
        for v in config.get(pl, []):
            if v.startswith("(") or v == "--None--":
                continue  # guarded/placeholder values of the audit query
            if v not in vocabulary:
                vocabulary.append(v)
            if (pl, v) in labels and v not in label_of:
                label_of[v] = labels[(pl, v)]
    used_values = OrderedDict()
    for src in spec["used"]:
        for v, n in used.get(src, {}).items():
            if v not in ("(null)",):
                used_values[v] = used_values.get(v, 0) + n
    for v in used_values:
        if v and v not in vocabulary and v != "--None--":
            vocabulary.append(v)
    if spec.get("only"):
        vocabulary = [v for v in spec["only"]]
    # English key -> label; a Russian value equal to such a label is its synonym.
    by_label = {}
    for v in vocabulary:
        lab = label_of.get(v)
        if lab and lab != v and lab not in by_label and not any((pl, v) in NO_MERGE for pl in spec["picklists"]):
            by_label[lab] = v
    mapping, option_labels, synonyms = OrderedDict(), {}, set()
    for v in vocabulary:
        base = by_label.get(v, v) if v not in label_of or label_of.get(v) == v else v
        if base != v:
            synonyms.add(v)
        key = core.get(base, core.get(v, clean(base)))
        mapping[v] = key
        lab = label_of.get(base)
        if lab and key not in option_labels:
            option_labels[key] = lab
        elif key not in option_labels and key != base:
            option_labels[key] = clean(base)
    # Position of an option is defined by its own value, not by a synonym listed earlier.
    options = []
    for v in [v for v in vocabulary if v not in synonyms] + [v for v in vocabulary if v in synonyms]:
        if mapping[v] not in options:
            options.append(mapping[v])
    for key in spec.get("extra", []):
        if key not in options:
            options.append(key)
    if spec.get("order"):
        options = [k for k in spec["order"] if k in options] + [k for k in options if k not in spec["order"]]
    if spec.get("sort_numeric"):
        options.sort(key=lambda k: int(k.rstrip("%")) if k.rstrip("%").isdigit() else -1)
    has_empty = "" in used_values or spec.get("empty")
    if spec.get("empty") is False:
        has_empty = False
    if has_empty:
        options.insert(0, "")
        mapping[""] = ""
    maps = OrderedDict()
    for src in spec["used"]:
        maps[src] = OrderedDict((v, mapping.get(v, mapping.get(clean(v)))) for v in used.get(src, {}) if v != "(null)")
    maps["(picklist)"] = mapping
    for src, m in spec.get("extra_sources", {}).items():
        maps[src] = OrderedDict(m)
        for key in m.values():
            if key not in options:
                options.append(key)
    unmapped = sorted({f"{s}={v}" for s, m in maps.items() for v, k in m.items() if k is None})
    if unmapped:
        raise SystemExit(f"{spec['entity']}.{spec['field']}: unmapped source values {unmapped}")
    default = spec.get("default")
    if spec.get("default_first"):
        default = options[0]
    if default is None:
        default = "" if has_empty else options[0]
    return options, option_labels, maps, default


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=4) + "\n"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    outdir, check = Path(sys.argv[1]), "--check" in sys.argv[2:]
    config, labels, used = load(outdir)
    value_maps, defs, i18n = defaultdict(dict), defaultdict(dict), defaultdict(dict)
    for spec in ENUMS:
        options, option_labels, maps, default = build_enum(spec, config, labels, used)
        entry = {"picklists": spec["picklists"], "options": options, "map": maps}
        if spec.get("not_actual"):
            entry["notActualOptions"] = spec["not_actual"]
        value_maps[spec["entity"]][spec["field"]] = entry
        field_defs = {"options": options, "default": default}
        if spec.get("not_actual"):
            field_defs["notActualOptions"] = spec["not_actual"]
        if (spec["entity"], spec["field"]) == ("Opportunity", "stage"):
            field_defs["probabilityMap"] = {k: PROBABILITY.get(k, 50) for k in options}
        defs[spec["entity"]][spec["field"]] = field_defs
        for (entity, field, key), label in LABEL_FIXES.items():
            if (entity, field) == (spec["entity"], spec["field"]) and key in options:
                option_labels[key] = label
        i18n[spec["entity"]][spec["field"]] = {k: v for k, v in option_labels.items() if k != v}
    for (entity, field), maps in STATIC.items():
        entry = value_maps[entity].setdefault(field, {"picklists": [], "options": None, "map": {}})
        entry["map"].update(maps)
        if (entity, field) in STATIC_OPTIONS:
            options, option_labels, default = STATIC_OPTIONS[(entity, field)]
            entry["options"] = options
            defs[entity][field] = {"options": options, "default": default}
            i18n[entity][field] = {k: v for k, v in option_labels.items() if k != v}
        elif entry["options"] is None:
            del entry["options"]
    changed = []

    def write(path, text):
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != text:
            changed.append(str(path.relative_to(REPO)))
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

    for entity, fields in sorted(value_maps.items()):
        write(MODULE / "metadata/vtigerValueMap" / f"{entity}.json", dump({"fields": fields}))
    for entity, fields in sorted(defs.items()):
        path = MODULE / "metadata/entityDefs" / f"{entity}.json"
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)
        for field, values in fields.items():
            if field not in data["fields"]:
                raise SystemExit(f"{entity}.{field} is missing in {path.relative_to(REPO)}")
            data["fields"][field].update(values)
        write(path, dump(data))
    for entity, fields in sorted(i18n.items()):
        path = MODULE / "i18n/ru_RU" / f"{entity}.json"
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict) if path.exists() else {}
        opts = data.setdefault("options", OrderedDict())
        for field, labels_ in fields.items():
            if labels_:
                opts[field] = OrderedDict(labels_)
            else:
                opts.pop(field, None)
        if not opts:
            data.pop("options")
        write(path, dump(data))
    print(("would change: " if check else "changed: ") + (", ".join(changed) or "nothing"))
    if check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
