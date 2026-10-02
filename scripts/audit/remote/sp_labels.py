#!/usr/bin/env python3
"""Run ON the source host. Reads `mysql --batch` rows `k, pl, value, sortorderid, presence` (41_picklist_config)
from stdin and prints the Russian UI label SalesPlatform shows for each configured picklist value:
`pl, value, module, label` (label found in languages/ru_ru/<Module>.php, then Vtiger.php).

Only translations of picklist values are printed: language files are UI strings, and only keys that are
picklist values are looked up. Usage: sp_labels.py <vtiger root>
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
# picklist -> modules whose language files may translate it (first match wins, Vtiger.php is the fallback)
MODULES = {
    "industry": ["Accounts", "Leads"], "leadsource": ["Leads", "Contacts", "Potentials"],
    "leadstatus": ["Leads"], "rating": ["Accounts", "Leads"], "accounttype": ["Accounts"],
    "opportunity_type": ["Potentials"], "sales_stage": ["Potentials"], "salutationtype": ["Contacts", "Leads"],
    "cf_1107": ["Leads"], "ticketpriorities": ["HelpDesk"], "ticketstatus": ["HelpDesk"],
    "ticketseverities": ["HelpDesk"], "ticketcategories": ["HelpDesk"], "faqstatus": ["Faq"],
    "faqcategories": ["Faq"], "taskstatus": ["Calendar"], "taskpriority": ["Calendar"],
    "eventstatus": ["Events", "Calendar"], "activitytype": ["Events", "Calendar"],
    "projectstatus": ["Project"], "projecttype": ["Project"], "projectpriority": ["Project"],
    "progress": ["Project"], "projecttaskstatus": ["ProjectTask"], "projecttaskpriority": ["ProjectTask"],
    "projecttasktype": ["ProjectTask"], "projecttaskprogress": ["ProjectTask"], "usageunit": ["Products"],
    "service_usageunit": ["Services"], "servicecategory": ["Services"],
    "quotestage": ["Quotes"], "sostatus": ["SalesOrder"],
}
PAIR = re.compile(r"""(['"])((?:\\.|(?!\1).)*)\1\s*=>\s*(['"])((?:\\.|(?!\3).)*)\3""", re.S)


def load(module):
    path = ROOT / "languages" / "ru_ru" / f"{module}.php"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {m.group(2).replace("\\'", "'"): m.group(4).replace("\\'", "'") for m in PAIR.finditer(text)}


cache = {}
print("pl\tvalue\tmodule\tlabel")
for line in sys.stdin:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 5 or parts[0] != "picklist":
        continue
    pl, value = parts[1], parts[2]
    found = ("", "")
    for module in MODULES.get(pl, []) + ["Vtiger"]:
        strings = cache.setdefault(module, load(module))
        if value in strings:
            found = (module, strings[value])
            break
    print(f"{pl}\t{value}\t{found[0]}\t{found[1]}")
