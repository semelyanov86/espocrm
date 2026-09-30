#!/usr/bin/env python3
"""Check targets of docs/migration/field-map.csv and relations.csv against the EspoCRM model.

The model is the merged metadata of the unpacked EspoCRM core (application/…), the Crm module, the project
module custom/Espo/Modules/Itvolga and custom/Espo/Custom — the same merge order EspoCRM uses. Used by
scripts/audit/build_maps.py (column `espo_check`) and by tests/stage03 (the live stand metadata must agree).

Usage: model_check.py [REPO]   — prints a summary of field-map/relations checks, exit 1 on failures.
"""
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK_DATE = "2026-09-30"

METADATA_DIRS = [
    "application/Espo/Resources/metadata",
    "application/Espo/Modules/Crm/Resources/metadata",
    "custom/Espo/Modules/Itvolga/Resources/metadata",
    "custom/Espo/Custom/Resources/metadata",
]
FIELD_TYPE_DIR = "application/Espo/Resources/metadata/fields"

# Entities of stage 03 (implemented now) and entities of later stages (checked when they exist).
STAGE03 = {"Account", "Contact", "Lead", "Opportunity", "Task", "Call", "Meeting", "Email", "Case",
           "KnowledgeBaseArticle", "KnowledgeBaseCategory", "Document", "DocumentFolder", "Note", "User", "Preferences",
           "Attachment", "Vendor", "Product", "Project", "ProjectTask", "VtigerArchive", "ContactAccess", "Team", "Role"}
LATER = {
    "Quote": "04.2", "QuoteItem": "04.2", "SalesOrder": "04.2", "SalesOrderItem": "04.2", "Invoice": "04.3",
    "InvoiceItem": "04.3", "Payment": "04.4", "PaymentAllocation": "04.4", "Act": "04.5", "ActItem": "04.5",
    "LegalEntity": "04.1", "Template": "05",
}
# Entities that receive imported Vtiger records (vtigerId, unique).
IMPORTED = ["Account", "Contact", "Lead", "Opportunity", "Task", "Call", "Meeting", "Email", "Case",
            "KnowledgeBaseArticle", "Document", "DocumentFolder", "Note", "User", "Attachment", "Vendor", "Product",
            "Project", "ProjectTask", "VtigerArchive", "ContactAccess"]
# target_entity column of field-map → entities (Events rows are split by activitytype).
ENTITY_ALIASES = {
    "Call/Meeting/Task (вид «Письмо») по activitytype": ["Call", "Meeting", "Task"],
    "Payment + PaymentAllocation (собственные)": ["Payment"],
}
# Source tables of rows without a module (physical columns) → entity.
TABLE_ENTITY = {
    "vtiger_attachments": "Attachment", "vtiger_attachmentsfolder": "DocumentFolder", "vtiger_email_track": "Email",
    "vtiger_leaddetails": "Lead", "vtiger_potential": "Opportunity", "vtiger_users": "User",
    "vtiger_sp_consignment": "VtigerArchive", "vtiger_invoice": "Invoice", "vtiger_quotes": "Quote",
    "vtiger_salesorder": "SalesOrder", "vtiger_sp_act": "Act", "vtiger_organizationdetails": "LegalEntity",
}
# Targets that are not model fields: how the value is carried instead.
NON_FIELD = {
    "(ключ записи)": "ключ записи → vtigerId",
    "(тип сущности)": "определяет целевую сущность",
    "(ключ слияния с Call)": "ключ слияния PBXManager ↔ SPCallPopup",
    "links EspoCRM": "связь — проверяется в relations.csv",
    "entityDefs options": "опции enum — metadata/vtigerValueMap (D-19, Q-32)",
    "config": "настройки EspoCRM (валюта RUB, D-37)",
    "Template (собств.)": "этап 05 (печатные формы)",
    "multiEnum": "значения тегов: Case.cTags, KnowledgeBaseArticle.cTags, ProjectTask.tags",
    "DocumentFolder": "запись DocumentFolder",
    "Attachment (файл)": "файл вложения → хранилище EspoCRM, сверка sha256 — этап 06.3",
}
STRING_TARGET_TYPES = {"varchar", "url", "email", "phone", "password", "text", "wysiwyg", "enum", "multiEnum"}
DEFAULT_MAX_LENGTH = {"varchar": 255, "url": 255, "password": 255, "enum": 255, "email": 255, "phone": 36}


def deep_merge(base, extra):
    if isinstance(base, dict) and isinstance(extra, dict):
        out = dict(base)
        for k, v in extra.items():
            out[k] = deep_merge(base[k], v) if k in base else v
        return out
    if isinstance(extra, list) and extra and extra[0] == "__APPEND__":
        return (base if isinstance(base, list) else []) + extra[1:]
    return extra


class Model:
    def __init__(self, repo=REPO):
        self.repo = Path(repo)
        core = self.repo / METADATA_DIRS[0] / "entityDefs"
        if not core.is_dir():
            raise SystemExit(f"EspoCRM core metadata not found in {core} (unpack the core: task stand:install)")
        self.entity_defs = self.load("entityDefs")
        self.scopes = self.load("scopes")
        self.value_maps = self.load("vtigerValueMap")
        self.field_types = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                            for p in (self.repo / FIELD_TYPE_DIR).glob("*.json")}

    def load(self, kind):
        result = {}
        for d in METADATA_DIRS:
            for p in sorted((self.repo / d / kind).glob("*.json")):
                data = json.loads(p.read_text(encoding="utf-8"))
                result[p.stem] = deep_merge(result.get(p.stem, {}), data)
        return result

    def field(self, entity, name):
        return self.entity_defs.get(entity, {}).get("fields", {}).get(name)

    def link(self, entity, name):
        return self.entity_defs.get(entity, {}).get("links", {}).get(name)

    def options(self, entity, name):
        f = self.field(entity, name) or {}
        ref = f.get("optionsReference")
        if ref:
            e, n = ref.split(".")
            return self.options(e, n)
        return f.get("options") or []

    def max_length(self, entity, name):
        f = self.field(entity, name) or {}
        if "maxLength" in f:
            return f["maxLength"]
        return address_max_length(self, entity, name) or DEFAULT_MAX_LENGTH.get(f.get("type"))


def entities_for(row):
    target = row.get("target_entity", "")
    if target in ENTITY_ALIASES:
        return ENTITY_ALIASES[target]
    if target in ("", "—"):
        ent = TABLE_ENTITY.get(row.get("source_table", ""))
        return [ent] if ent else []
    return [re.sub(r"\s*\(.*$", "", target).strip()]


def parse_target(target, default_entities):
    """→ list of (entity, field, extra) for a target_field string; extra: phone type / required option."""
    t = target.strip()
    if t in NON_FIELD or t in ("", "—"):
        return None
    phone = None
    m = re.search(r"\[(\w+)\]", t)
    if m:
        phone, t = m.group(1), t.replace(m.group(0), "")
    if not t.startswith("("):
        t = re.sub(r"\([^)]*\)", "", t)  # comments in parentheses
    t = t.strip("() ")
    result = []
    for token in re.split(r"\s*(?:/|\||\+|,)\s*", t):
        token = token.strip()
        if not token:
            continue
        option = None
        if "=" in token:
            token, option = token.split("=", 1)
        parts = token.split(".")
        entities = default_entities
        if parts[0][:1].isupper() and len(parts) > 1:
            entities, parts = [parts[0]], parts[1:]
        if parts[0] == "preferences":
            entities, parts = ["Preferences"], parts[1:] or ["(currency)"]
        name = parts[0]
        for ent in entities:
            result.append((ent, name, {"phone": phone, "option": option}))
    return result


# Picklist tables (rows «entityDefs options») that do not become an EspoCRM enum of stage 03.
PICKLIST_FATE = {
    **{pl: "этап 04.x: справочник финансового модуля" for pl in (
        "carrier", "invoicestatus", "pay_type", "payment_duration", "postatus", "quotestage", "recurring_frequency",
        "sostatus", "sp_actstatus", "spcompany", "spstatus", "type_payment")},
    **{pl: "архив: исходные значения в VtigerArchive.data (enum не создаётся)" for pl in (
        "assetstatus", "contract_priority", "contract_status", "contract_type", "tracking_unit",
        "sp_consignmentstatus", "type", "msg_type")},
    "faqcategories": "записи KnowledgeBaseCategory (General → «Общее»)",
    "activitytype": "определяет сущность (Call/Meeting/Task); «Письмо» → Task.cTaskType",
    "status": "статус пользователя → User.isActive",
    "duration_minutes": "служебный список минут; длительность → Call/Meeting.duration",
}


def picklist_check(model, table):
    pl = table[len("vtiger_"):] if table.startswith("vtiger_") else table
    used = [f"{entity}.{field}" for entity, data in sorted(model.value_maps.items())
            for field, spec in data.get("fields", {}).items() if pl in spec.get("picklists", [])]
    if used:
        return True, "ok: опции " + ", ".join(used) + " (metadata/vtigerValueMap, D-19, Q-32)"
    return None, PICKLIST_FATE.get(pl, "не используется: поле без данных, служебное или модуль без записей")


def address_max_length(model, entity, name):
    for part in ("Street", "City", "State", "Country", "PostalCode"):
        if name.endswith("Address" + part) or name == "address" + part:
            key = part[0].lower() + part[1:]
            return model.field_types.get("address", {}).get("fields", {}).get(key, {}).get("maxLength")
    return None


def check_field_row(model, row, max_len=None):
    """→ (ok: bool|None, text). None = not applicable (excluded/empty/later stage)."""
    fate = row.get("fate", "")
    if not (fate.startswith("перенос") or fate.startswith("архив")):
        return None, "—"
    target = row.get("target_field", "")
    if target.strip() == "entityDefs options":
        return picklist_check(model, row.get("source_table", ""))
    if target.strip() in NON_FIELD:
        return None, NON_FIELD[target.strip()]
    entities = entities_for(row)
    if row.get("source_table") == "vtiger_crmentity" and target == "vtigerId":
        missing = [e for e in IMPORTED if not model.field(e, "vtigerId")]
        if missing:
            return False, "ОШИБКА: нет vtigerId у " + ", ".join(missing)
        return True, f"ok: vtigerId (int, unique) у {len(IMPORTED)} сущностей"
    for ent in entities:
        if ent in LATER:
            return None, f"этап {LATER[ent]}"
    if target.startswith("<Doc>Item") or "Item." in target:
        stage = next((LATER[e] for e in LATER if target.startswith(e)), None)
        return None, f"этап {stage or '04.x'} (строки документов)"
    parsed = parse_target(target, entities)
    if not parsed:
        return None, "—"
    problems, notes = [], []
    for ent, name, extra in parsed:
        if ent in LATER:
            notes.append(f"{ent}: этап {LATER[ent]}")
            continue
        if ent not in model.entity_defs:
            problems.append(f"нет сущности {ent}")
            continue
        if ent == "Preferences" and name == "(currency)":
            notes.append("Preferences: валюта RUB по умолчанию")
            continue
        f = model.field(ent, name)
        if f is None:
            if model.link(ent, name):
                notes.append(f"{ent}.{name} link")
                continue
            problems.append(f"нет поля {ent}.{name}")
            continue
        ftype = f.get("type")
        desc = f"{ent}.{name} {ftype}"
        ml = model.max_length(ent, name) if ftype in STRING_TARGET_TYPES else None
        if extra["phone"]:
            types = f.get("typeList") or model.field_types.get("phone", {}).get("typeList") or []
            if types and extra["phone"] not in types:
                problems.append(f"{desc}: нет типа {extra['phone']}")
        if extra["option"] and extra["option"] not in model.options(ent, name):
            problems.append(f"{desc}: нет опции {extra['option']}")
        if max_len and ml and name not in ("vtigerData",) and ftype in ("varchar", "url", "password", "email") \
                and int(max_len) > int(ml):
            problems.append(f"{desc}({ml}) < max {max_len}")
        notes.append(desc + (f"({ml})" if ml and ftype in ("varchar", "url") else ""))
    if problems:
        return False, "ОШИБКА: " + "; ".join(problems)
    return True, "ok: " + "; ".join(dict.fromkeys(notes))


# relations.csv: module → entity and the Document link of each entity (senotesrel).
MODULE_ENTITY = {
    "Accounts": "Account", "Contacts": "Contact", "Leads": "Lead", "Potentials": "Opportunity", "Calendar": "Task",
    "Events": "Call", "Emails": "Email", "HelpDesk": "Case", "Faq": "KnowledgeBaseArticle", "Documents": "Document",
    "Products": "Product", "Services": "Product", "Vendors": "Vendor", "PBXManager": "Call", "SPCallPopup": "Call",
    "ModComments": "Note", "Project": "Project", "ProjectTask": "ProjectTask", "Consignment": "VtigerArchive",
    "ServiceContracts": "VtigerArchive", "Assets": "VtigerArchive", "Jivosite": "VtigerArchive",
    "JVmes": "VtigerArchive", "Users": "User", "Quotes": "Quote", "SalesOrder": "SalesOrder", "Invoice": "Invoice",
    "Act": "Act", "SPPayments": "Payment",
}


def check_relation_row(model, row):
    fate = row.get("fate", "")
    if not (fate.startswith("перенос") or fate.startswith("архив") or fate == "слияние"):
        return None, "—"
    target = row.get("target_link", "")
    ent = MODULE_ENTITY.get(row.get("from_module", ""))
    if fate == "слияние" or target.startswith("слияние"):
        return None, "слияние SPCallPopup → Call (поля Call.description / vtigerData)"
    if ent in LATER or any(target.startswith(e + ".") or target.startswith(e + " ") for e in LATER):
        stage = LATER.get(ent) or next(LATER[e] for e in LATER if target.startswith(e))
        return None, f"этап {stage}"
    if row.get("kind") == "acl":
        return None, "роли/команды: itvolga-setup-acl"
    if row.get("kind") == "attachment":
        pass
    t = re.sub(r"\([^)]*\)", "", target).replace("→", " ").strip()
    tokens = [x for x in re.split(r"\s*(?:/|,|\s)\s*", t) if x]
    problems, notes = [], []
    for token in tokens:
        if token in ("—", "") or token.startswith("<"):
            continue
        parts = token.split(".")
        entities = [ent] if ent else []
        if parts[0][:1].isupper() and len(parts) > 1:
            entities = [p for p in parts[0].split("|")]
            parts = parts[1:]
        elif "|" in parts[0] and parts[0][:1].isupper():
            entities, parts = parts[0].split("|"), parts[1:]
        name = parts[0] if parts else ""
        if not name or not name[:1].islower():
            continue
        for e in entities:
            if e in LATER:
                notes.append(f"{e}: этап {LATER[e]}")
                continue
            if model.link(e, name) or (model.field(e, name) and model.field(e, name).get("type") in (
                    "link", "linkMultiple", "linkParent", "file", "image", "attachmentMultiple", "jsonObject",
                    "multiEnum")):
                notes.append(f"{e}.{name}")
            else:
                problems.append(f"нет связи {e}.{name}")
    if problems:
        return False, "ОШИБКА: " + "; ".join(problems)
    if not notes:
        return None, "—"
    return True, "ok: " + "; ".join(dict.fromkeys(notes))


def main():
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO
    model = Model(repo)
    failures = 0
    for name, checker, key in (("field-map.csv", check_field_row, "target_field"),
                               ("relations.csv", check_relation_row, "target_link")):
        with open(repo / "docs/migration" / name, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        ok = bad = na = 0
        for row in rows:
            res, text = checker(model, row) if checker is check_relation_row else checker(model, row, row.get("max_len_live"))
            if res is True:
                ok += 1
            elif res is False:
                bad += 1
                print(f"{name}: {row.get('source_module') or row.get('relation_id')} {row.get('source_column', '')} "
                      f"→ {row.get(key)}: {text}")
            else:
                na += 1
        failures += bad
        print(f"{name}: ok {ok}, failed {bad}, not applicable {na}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
