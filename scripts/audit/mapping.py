"""Proposed Vtiger -> EspoCRM mapping rules used by build_maps.py.

Targets started as PROPOSALS of the stage-01 audit. build_maps.py checks every target against the EspoCRM model
(scripts/model/model_check.py, column `espo_check`); a row whose target exists with a compatible type and length
gets `mapping_status=реализовано (этап 03)`. Rows of later stages stay `предложено`.

Conventions (see docs/migration/decisions.md):
- custom fields on standard EspoCRM entities use the `c` prefix (cInn);
- own entities (Invoice, Act, Payment, ...) use plain camelCase names;
- `vtigerId` (source crmid) and `vtigerNo` (source record number) exist on every imported entity;
- `vtigerData` is a read-only JSON archive field for non-empty source values without a work field;
- VtigerArchive is a read-only archive entity for modules without a work entity;
- change history (vtiger_modtracker_*) is NOT migrated (owner decision Q-27).
"""

# module -> (target entity, module fate)
MODULES = {
    "Accounts": ("Account", "рабочая сущность"),
    "Contacts": ("Contact", "рабочая сущность"),
    "Leads": ("Lead", "рабочая сущность"),
    "Potentials": ("Opportunity", "рабочая сущность"),
    "Calendar": ("Task", "рабочая сущность"),
    "Events": ("Call/Meeting/Task (вид «Письмо») по activitytype", "рабочая сущность"),
    "Emails": ("Email", "рабочая сущность (архивные письма)"),
    "HelpDesk": ("Case", "рабочая сущность"),
    "Faq": ("KnowledgeBaseArticle", "рабочая сущность"),
    "Documents": ("Document", "рабочая сущность"),
    "Products": ("Product (собственная)", "рабочая сущность"),
    "Services": ("Product (собственная, type=service)", "рабочая сущность"),
    "Vendors": ("Vendor (собственная)", "рабочая сущность"),
    "Quotes": ("Quote (собственная)", "рабочая сущность"),
    "SalesOrder": ("SalesOrder (собственная)", "рабочая сущность"),
    "Invoice": ("Invoice (собственная)", "рабочая сущность"),
    "Act": ("Act (собственная)", "рабочая сущность"),
    "SPPayments": ("Payment + PaymentAllocation (собственные)", "рабочая сущность"),
    "PBXManager": ("Call", "исторические данные в рабочей сущности"),
    "SPCallPopup": ("Call (слияние с PBXManager)", "слияние"),
    "ModComments": ("Note (post)", "рабочая сущность"),
    "Project": ("Project (собственная)", "исторический архив в собственной сущности"),
    "ProjectTask": ("ProjectTask (собственная)", "исторический архив в собственной сущности"),
    "Consignment": ("VtigerArchive", "исторический архив"),
    "ServiceContracts": ("VtigerArchive", "исторический архив"),
    "Assets": ("VtigerArchive", "исторический архив"),
    "Jivosite": ("VtigerArchive", "исторический архив"),
    "JVmes": ("VtigerArchive (дочерние сообщения Jivosite)", "исторический архив"),
    "VTEItems": ("—", "исключение: дубль строк документов"),
    "Notifications": ("—", "исключение: служебное уведомление"),
    "Users": ("User", "рабочая сущность"),
}

# Finance modules whose fields and links are fixed by the stage 04.1 contract (docs/migration/finance-contract.md §11).
FINANCE_CONTRACT_MODULES = {"Quotes", "SalesOrder", "Invoice", "Act", "SPPayments"}
FINANCE_CONTRACT_TABLES = {"vtiger_inventoryproductrel", "vtiger_organizationdetails", "vtiger_spcompany", "sp_payments", "sp_paymentscf"}
# Columns whose NULL is information, not absence (fate is not "пусто" even with no non-zero values).
NULL_SIGNIFICANT = {"region_id"}

ARCHIVE_MODULES = {"Consignment", "ServiceContracts", "Assets", "Jivosite", "JVmes"}

# Enum values go through the generated dictionary of stage 03 (scripts/model/build_value_maps.py).
D = "словарь metadata/vtigerValueMap/{} (D-19; утверждён владельцем 2026-09-30, Q-32)"

# Fields shared by most modules (vtiger_crmentity and common columns).
COMMON = {
    "assigned_user_id": ("assignedUser / teams", "owner-map: user→User; group→Team (assignedUser пуст)", "fk"),
    "created_user_id": ("createdBy", "user-map по vtiger_users.id", "fk"),
    "modifiedby": ("modifiedBy", "user-map по vtiger_users.id", "fk"),
    "createdtime": ("createdAt", "datetime → UTC по эпохам D-30 (Europe/Moscow до 2022-11, Europe/Berlin до 2026-06-12, далее UTC)", "count+hash"),
    "modifiedtime": ("modifiedAt", "datetime → UTC по эпохам D-30 (Europe/Moscow до 2022-11, Europe/Berlin до 2026-06-12, далее UTC)", "count+hash"),
    "ModifiedTime": ("modifiedAt", "datetime → UTC по эпохам D-30 (Europe/Moscow до 2022-11, Europe/Berlin до 2026-06-12, далее UTC)", "count+hash"),
    "description": ("description", "text as-is", "count+hash"),
    "source": (None, "исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE)", "count"),
    "starred": (None, "исключено: персональная «звёздочка» пользователя (истинных значений — единицы)", "count"),
    "tags": (None, "пусто в источнике (теги — vtiger_freetagged_objects)", "count"),
    "isconvertedfromlead": ("vtigerData.isconvertedfromlead", "bool→JSON", "count"),
    "notify_owner": (None, "исключено: флаг стандартного workflow уведомления", "count"),
    "emailoptout": ("emailAddressIsOptedOut", "bool '1'→true", "count"),
    "currency_id": ("currency", "1→RUB (единственная валюта)", "count"),
    "conversion_rate": (None, "исключено: всегда 1.000 (одна валюта)", "count"),
    "region_id": ("sourceFormula + vtigerData.region_id", "значимы и NULL, и 0: NULL — документ до 2018-07 (налог строк не входит в итоги), "
                  "0 — после; класс формулы ядра (FormulaClass, этап 04.1) → sourceFormula, исходное значение → vtigerData", "count"),
    "spcompany": ("legalEntity", "'Default', 'По умолчанию' (русская подпись ключа 'Default') и пусто → одна запись LegalEntity "
                  "(D-04, LegalEntityResolver); другое значение — остановка импорта, не второе юрлицо", "count"),
}

ADDRESS_INV = {
    "bill_street": "billingAddressStreet", "bill_city": "billingAddressCity", "bill_state": "billingAddressState",
    "bill_code": "billingAddressPostalCode", "bill_country": "billingAddressCountry", "bill_pobox": "vtigerData.bill_pobox",
    "ship_street": "shippingAddressStreet", "ship_city": "shippingAddressCity", "ship_state": "shippingAddressState",
    "ship_code": "shippingAddressPostalCode", "ship_country": "shippingAddressCountry", "ship_pobox": "vtigerData.ship_pobox",
}

INVENTORY_HEADER = {
    "subject": ("name", "string", "count+hash"),
    "txtAdjustment": ("adjustment", "decimal(25,8) как есть", "count+sum"),
    "hdnSubTotal": ("subtotal", "decimal: исходное значение — эталон, не пересчитывать", "count+sum"),
    "hdnGrandTotal": ("grandTotal", "decimal: исходное значение — эталон, не пересчитывать", "count+sum"),
    "pre_tax_total": ("preTaxTotal", "decimal: исходное значение — эталон", "count+sum"),
    "hdnTaxType": ("taxMode", "enum individual|group|group_tax_inc", "count+distribution"),
    "hdnS_H_Amount": ("shippingAmount", "decimal (во всех записях 0)", "count+sum"),
    "hdnS_H_Percent": ("shippingTaxPercent", "decimal (во всех записях 0)", "count+sum"),
    "hdnDiscountAmount": ("discountAmount", "decimal", "count+sum"),
    "hdnDiscountPercent": ("discountPercent", "decimal", "count+sum"),
    "terms_conditions": ("termsAndConditions", "text", "count+hash"),
    "account_id": ("account", "fk Accounts→Account", "fk"),
    "contact_id": ("contact", "fk Contacts→Contact", "fk"),
    "potential_id": ("opportunity", "fk Potentials→Opportunity", "fk"),
    "salesorder_id": ("salesOrder", "fk SalesOrder→SalesOrder", "fk"),
    "quote_id": ("quote", "fk Quotes→Quote", "fk"),
    "salescommission": ("vtigerData.salescommission", "decimal", "count+sum"),
    "exciseduty": ("vtigerData.exciseduty", "decimal", "count+sum"),
    "tax": ("vtigerData.tax", "служебное скрытое поле tax (presence=1)", "count"),
}

LINE_ITEM = {
    "productid": ("<Doc>Item.product", "fk Services/Products→Product", "fk"),
    "quantity": ("<Doc>Item.quantity", "decimal(25,3)", "count+sum"),
    "listprice": ("<Doc>Item.unitPrice", "decimal(27,8)", "count+sum"),
    "comment": ("<Doc>Item.description", "text", "count+hash"),
    "discount_amount": ("<Doc>Item.discountAmount", "decimal", "count+sum"),
    "discount_percent": ("<Doc>Item.discountPercent", "decimal", "count+sum"),
    "tax1": ("<Doc>Item.taxRate", "decimal % (НДС tax1); в итоги входит только у 2 group-счетов (класс формулы — sourceFormula)", "count+sum"),
    "tax2": ("<Doc>Item.vtigerData.tax2", "decimal %", "count+sum"),
    "tax3": ("<Doc>Item.vtigerData.tax3", "decimal %", "count+sum"),
    "purchase_cost": ("<Doc>Item.purchaseCost", "decimal", "count+sum"),
    "margin": ("<Doc>Item.margin", "decimal: исходное значение; ядро проверяет margin = net − purchase_cost или 0 (не вычислялась)", "count+sum"),
    "image": (None, "исключено: пустое служебное поле", "count"),
    "description": ("<Doc>Item.vtigerData.description", "text", "count+hash"),
}

PHONES = {
    "phone": ("phoneNumber[Office]", "phone: исходная строка + нормализация E.164 (без потери исходного вида)", "count+hash"),
    "mobile": ("phoneNumber[Mobile]", "phone", "count+hash"),
    "homephone": ("phoneNumber[Home]", "phone", "count+hash"),
    "otherphone": ("phoneNumber[Other]", "phone", "count+hash"),
    "fax": ("phoneNumber[Fax]", "phone", "count+hash"),
}

F = {}

F["Accounts"] = {
    "accountname": ("name", "string", "count+hash"),
    "account_no": ("vtigerNo", "string (КОНТР_N)", "count+hash"),
    "website": ("website", "url", "count+hash"),
    "tickersymbol": ("cShortName", "string: краткое название организации (подтверждено владельцем, Q-24)", "count+hash"),
    "account_id": ("parent (cParentAccount)", "fk (в источнике пусто)", "fk"),
    "employees": ("cEmployees", "int (0 = пусто)", "count+sum"),
    "email1": ("emailAddress (primary)", "email lower-case", "count+hash"),
    "email2": ("emailAddress (secondary)", "email lower-case", "count+hash"),
    "ownership": ("vtigerData.ownership", "string", "count+hash"),
    "industry": ("industry", "enum: " + D.format("Account.json") + "; исходное значение → vtigerData, если изменено", "count+distribution"),
    "rating": ("cRating", "enum: " + D.format("Account.json"), "count+distribution"),
    "accounttype": ("type", "enum: " + D.format("Account.json") + " (Клиент/Customer → Customer)", "count+distribution"),
    "siccode": ("sicCode", "string", "count+hash"),
    "annual_revenue": ("vtigerData.annual_revenue", "decimal (0 = пусто)", "count+sum"),
    "inn": ("cInn", "string (ключ поиска плательщика при банковском импорте)", "count+hash"),
    "kpp": ("cKpp", "string", "count+hash"),
    "vk_url": ("cVkUrl", "url", "count+hash"),
    "cf_1109": ("cBankAccount", "string (расчётный счёт клиента)", "count+hash"),
    "cf_1111": ("cBankName", "string", "count+hash"),
    "cf_1113": ("cCorrAccount", "string", "count+hash"),
    "cf_1115": ("cBic", "string", "count+hash"),
    **{k: (v, "address", "count+hash") for k, v in ADDRESS_INV.items()},
    **PHONES,
}

F["Contacts"] = {
    "contact_no": ("vtigerNo", "string (КОНТАКТ_N)", "count+hash"),
    "salutationtype": ("salutationName", "enum: только стандартные Mr./Ms./Mrs./Dr./Prof.; прочий текст (2 контакта — сдвиг "
                                         "старого импорта, проверено 2026-09-30) → vtigerData.salutationtype", "count+distribution"),
    "firstname": ("firstName", "string", "count+hash"),
    "lastname": ("lastName", "string", "count+hash"),
    "account_id": ("account (accounts primary)", "fk", "fk"),
    "leadsource": ("cLeadSource", "enum: " + D.format("Lead.json") + " (общий список источников)", "count+distribution"),
    "title": ("title", "string", "count+hash"),
    "department": ("cDepartment", "string", "count+hash"),
    "email": ("emailAddress (primary)", "email lower-case", "count+hash"),
    "secondaryemail": ("emailAddress (secondary)", "email lower-case", "count+hash"),
    "birthday": ("cBirthday", "date", "count+hash"),
    "contact_id": (None, "исключено: во всех живых записях '0' — ссылки нет (relations.csv Contacts.reportsto = 0; "
                         "проверено 2026-09-30)", "count"),
    "donotcall": ("doNotCall", "bool", "count"),
    "reference": (None, "исключено: истинных значений нет", "count"),
    "portal": ("vtigerData.portal", "bool; портал не используется (0 портальных пользователей)", "count"),
    "support_start_date": ("cSupportStartDate", "date", "count+hash"),
    "support_end_date": ("cSupportEndDate", "date", "count+hash"),
    "cf_1372": ("cNeedOriginalDocs", "bool", "count"),
    "cf_1374": ("cSendNews", "bool", "count"),
    "cf_1376": ("cPartnerAds", "bool", "count"),
    "cf_1378": ("cSendAlerts", "bool", "count"),
    "cf_1322": ("ContactAccess.anydeskId", "SECURE: отдельная сущность с ограниченным ACL; значения не логировать", "count+hash (без вывода)"),
    "cf_1324": ("ContactAccess.anydeskPassword", "SECURE: шифрование/отдельное хранилище; значения не логировать и не выводить", "count+hash (без вывода)"),
    "cf_1326": ("ContactAccess.hostname", "SECURE: отдельная сущность с ограниченным ACL", "count+hash (без вывода)"),
    "cf_1328": ("ContactAccess.ipAddress", "SECURE: отдельная сущность с ограниченным ACL", "count+hash (без вывода)"),
    "imagename": ("cPhoto", "image: вложение Contacts Image (1 файл); 5 имён без файла — принятая потеря (D-23)", "file-hash"),
    "vk_url": ("cVkUrl", "url", "count+hash"),
    "mailingstreet": ("addressStreet", "address", "count+hash"), "mailingcity": ("addressCity", "address", "count+hash"),
    "mailingstate": ("addressState", "address", "count+hash"), "mailingzip": ("addressPostalCode", "address", "count+hash"),
    "mailingcountry": ("addressCountry", "address", "count+hash"), "mailingpobox": ("vtigerData.mailingpobox", "string", "count"),
    "otherstreet": ("cOtherAddressStreet", "address", "count+hash"), "othercity": ("cOtherAddressCity", "address", "count+hash"),
    "otherstate": ("cOtherAddressState", "address", "count+hash"), "otherzip": ("cOtherAddressPostalCode", "address", "count+hash"),
    "othercountry": ("cOtherAddressCountry", "address", "count+hash"), "otherpobox": ("vtigerData.otherpobox", "string", "count"),
    **PHONES,
}

F["Leads"] = {
    "lead_no": ("vtigerNo", "string (ОБР_N)", "count+hash"),
    "salutationtype": ("salutationName", "enum: только стандартные Mr./Ms./Mrs./Dr./Prof.; прочий текст (6 обращений — сдвиг "
                                         "старого импорта, проверено 2026-09-30) → vtigerData.salutationtype", "count+distribution"),
    "firstname": ("firstName", "string", "count+hash"),
    "lastname": ("lastName", "string", "count+hash"),
    "company": ("accountName", "string", "count+hash"),
    "designation": ("title", "string", "count+hash"),
    "leadsource": ("source", "enum: " + D.format("Lead.json") + "; исходное значение → vtigerData, если изменено", "count+distribution"),
    "email": ("emailAddress (primary)", "email", "count+hash"),
    "secondaryemail": ("emailAddress (secondary)", "email", "count+hash"),
    "industry": ("industry", "enum: " + D.format("Account.json") + " (список общий с Account)", "count+distribution"),
    "website": ("website", "url", "count+hash"),
    "annualrevenue": ("vtigerData.annualrevenue", "decimal (0 = пусто)", "count+sum"),
    "leadstatus": ("status", "enum: " + D.format("Lead.json") + "; Not Contacted → New; converted=1 → Converted", "count+distribution"),
    "noofemployees": ("vtigerData.noofemployees", "int (0 = пусто)", "count+sum"),
    "rating": ("cRating", "enum: " + D.format("Account.json") + " (список общий с Account)", "count+distribution"),
    "vk_url": ("cVkUrl", "url", "count+hash"),
    "cf_1107": ("cPriority", "enum: " + D.format("Lead.json"), "count+distribution"),
    "cf_1165": ("cJivositeId", "int", "count+hash"),
    "lane": ("addressStreet", "address", "count+hash"), "city": ("addressCity", "address", "count+hash"),
    "state": ("addressState", "address", "count+hash"), "code": ("addressPostalCode", "address", "count+hash"),
    "country": ("addressCountry", "address", "count+hash"), "pobox": ("vtigerData.pobox", "string", "count"),
    **PHONES,
}

F["Potentials"] = {
    "potentialname": ("name", "string", "count+hash"),
    "potential_no": ("vtigerNo", "string (СДЕЛКА_N)", "count+hash"),
    "related_to": ("account", "fk", "fk"),
    "contact_id": ("contacts (primary)", "fk", "fk"),
    "amount": ("amount", "currency decimal", "count+sum"),
    "opportunity_type": ("cOpportunityType", "enum: " + D.format("Opportunity.json"), "count+distribution"),
    "closingdate": ("closeDate", "date", "count+hash"),
    "leadsource": ("leadSource", "enum: " + D.format("Lead.json") + " (optionsReference Lead.source)", "count+distribution"),
    "nextstep": ("vtigerData.nextstep", "string", "count+hash"),
    "sales_stage": ("stage", "enum: " + D.format("Opportunity.json") + "; английские стадии Vtiger — ключи, «Переговоры» "
                                   "объединены с Negotiation or Review", "count+distribution"),
    "campaignid": ("campaign", "fk (в источнике пусто)", "fk"),
    "probability": ("probability", "int %: дробных значений нет (13 непустых, проверено 2026-09-30)", "count+sum"),
    "forecast_amount": (None, "исключено: вычисляется workflow (amount×probability) — пересчитывается", "count+sum"),
    "spcompany": ("vtigerData.spcompany", "одно юрлицо; в сделке не используется в расчётах", "count+distribution"),
}

F["Calendar"] = {
    "subject": ("name", "string", "count+hash"),
    "date_start": ("dateStart", "date+time_start → datetime → UTC по эпохам D-30", "count+hash"),
    "time_start": ("dateStart (время)", "склейка с date_start", "count+hash"),
    "due_date": ("dateEnd", "date (срок задачи)", "count+hash"),
    "parent_id": ("parent", "fk из vtiger_seactivityrel", "fk"),
    "contact_id": ("contact", "fk из vtiger_cntactivityrel", "fk"),
    "taskstatus": ("status", "enum: " + D.format("Task.json") + " (In Progress → Started)", "count+distribution"),
    "taskpriority": ("priority", "enum: " + D.format("Task.json") + " (Medium → Normal; пусто остаётся пустым)", "count+distribution"),
    "sendnotification": (None, "исключено: флаг уведомления (все 0)", "count"),
    "activitytype": (None, "служебное: Task", "count"),
    "visibility": (None, "исключено: все Private (ACL задаётся владельцем)", "count"),
    "duration_hours": (None, "вычисляется из dateStart/dateEnd", "count"),
    "duration_minutes": (None, "вычисляется", "count"),
    "notime": (None, "исключено: все 0", "count"),
    "reminder_time": ("reminders", "минуты → reminders (popup)", "count"),
    "popup_reminder_time": (None, "исключено: служебное", "count"),
    "eventstatus": (None, "не используется для задач", "count"),
    "recurringtype": (None, "пусто", "count"),
}

F["Events"] = {
    "subject": ("name", "string", "count+hash"),
    "date_start": ("dateStart", "date+time_start → datetime → UTC по эпохам D-30", "count+hash"),
    "time_start": ("dateStart (время)", "склейка", "count+hash"),
    "due_date": ("dateEnd", "date+time_end → datetime → UTC по эпохам D-30", "count+hash"),
    "time_end": ("dateEnd (время)", "склейка", "count+hash"),
    "duration_hours": ("Call.duration|Meeting.duration", "часы+минуты → секунды; у Task («Письмо») длительность "
                                                         "не хранится — определяется датами", "count+sum"),
    "duration_minutes": ("Call.duration|Meeting.duration", "часы+минуты → секунды", "count+sum"),
    "eventstatus": ("status", "enum: " + D.format("Call.json, Meeting.json, Task.json") + "; Call/Meeting как есть; "
                              "Task «Письмо»: Held→Completed, Planned→Planned, Not Held→Canceled", "count+distribution"),
    "activitytype": ("Task.cTaskType", "Call→Call; Meeting→Meeting; 'Письмо'→Task с cTaskType=«Письмо» (Q-10, D-24)", "count+distribution"),
    "taskpriority": ("vtigerData.taskpriority", "enum", "count"),
    "visibility": (None, "исключено: все Public", "count"),
    "sendnotification": (None, "исключено: все 0", "count"),
    "notime": (None, "исключено: все 0", "count"),
    "reminder_time": ("reminders", "минуты → reminders", "count"),
    "popup_reminder_time": (None, "исключено: служебное", "count"),
    "recurringtype": (None, "исключено: все --None--", "count"),
    "invoiceid": ("vtigerData.invoiceid", "кастомная ссылка (в источнике пусто)", "fk"),
    "salesorder_id": ("vtigerData.salesorder_id", "кастомная ссылка (пусто)", "fk"),
    "timesheet_id": ("vtigerData.timesheet_id", "кастомная ссылка (пусто)", "fk"),
    "duration_seconds": ("vtigerData.duration_seconds", "string", "count"),
    "contact_id": ("Call.contacts|Meeting.contacts|Task.contact", "fk из vtiger_cntactivityrel", "fk"),
    "parent_id": ("parent", "fk из vtiger_seactivityrel", "fk"),
    "taskstatus": (None, "не используется для событий", "count"),
}

F["Emails"] = {
    "subject": ("name", "string", "count+hash"),
    "description": ("body", "html", "count+hash"),
    "date_start": ("dateSent", "date+time_start → UTC по эпохам D-30", "count+hash"),
    "time_start": ("dateSent (время)", "склейка", "count+hash"),
    "from_email": ("fromString / from", "email", "count+hash"),
    "saved_toid": ("to", "список адресов (JSON/строка)", "count+hash"),
    "ccmail": ("cc", "JSON-список → адреса", "count+hash"),
    "bccmail": ("bcc", "JSON-список → адреса", "count+hash"),
    "parent_id": ("parent", "формат 'crmid@fieldid|…' → первая ссылка + связи", "fk"),
    "parent_type": ("vtigerData.parent_type", "string", "count"),
    "email_flag": ("status", "SENT→Sent; MailManager→Archived", "count+distribution"),
    "access_count": ("vtigerData.access_count", "int (трекинг открытий)", "count+sum"),
    "click_count": ("vtigerData.click_count", "int", "count+sum"),
    "activitytype": (None, "служебное: Emails", "count"),
    "filename": ("attachments", "attachment", "file-hash"),
}

F["HelpDesk"] = {
    "ticket_title": ("name", "string", "count+hash"),
    "ticket_no": ("vtigerNo", "string (ЗАЯВКА_N)", "count+hash"),
    "parent_id": ("account", "fk", "fk"),
    "contact_id": ("contact", "fk", "fk"),
    "product_id": ("vtigerData.product_id", "fk (пусто)", "fk"),
    "ticketpriorities": ("priority", "enum: " + D.format("Case.json") + " (Высокий → High)", "count+distribution"),
    "ticketstatus": ("status", "enum: " + D.format("Case.json") + " (Open→New, In Progress→Assigned, Wait For Response→Pending; "
                               "подписи — как в Vtiger)", "count+distribution"),
    "ticketseverities": ("cSeverity", "enum: " + D.format("Case.json") + " (Незначительная → Minor)", "count+distribution"),
    "ticketcategories": ("type", "enum: " + D.format("Case.json"), "count+distribution"),
    "hours": ("vtigerData.hours", "decimal (0 = пусто)", "count+sum"),
    "days": ("vtigerData.days", "decimal (0 = пусто)", "count+sum"),
    "from_portal": (None, "исключено: все 0 (портал не используется)", "count"),
    "solution": ("cSolution", "text", "count+hash"),
}

F["Faq"] = {
    "question": ("name", "text → varchar(500): максимум 375 символов в живых записях, без обрезки (проверено 2026-09-30)", "count+hash"),
    "faq_answer": ("body", "html", "count+hash"),
    "faq_no": ("vtigerNo", "string (БЗ_N)", "count+hash"),
    "faqstatus": ("status", "enum: " + D.format("KnowledgeBaseArticle.json") + " (Reviewed→In Review, Obsolete→Archived)", "count+distribution"),
    "faqcategories": ("categories", "запись KnowledgeBaseCategory «Общее» (General)", "count+distribution"),
    "product_id": ("vtigerData.product_id", "fk (пусто)", "fk"),
}

F["Documents"] = {
    "notes_title": ("name", "string", "count+hash"),
    "folderid": ("folder", "DocumentFolder 'По умолчанию'", "fk"),
    "note_no": ("vtigerNo", "string (ДОК_N)", "count+hash"),
    "filelocationtype": ("(file|cExternalUrl)", "I→Attachment в file; E→cExternalUrl", "count+distribution"),
    "filename": ("file / cExternalUrl", "Attachment (I) или URL (E)", "file-hash"),
    "filestatus": ("status", "1→Active; 0→Draft", "count+distribution"),
    "filesize": ("file.size", "производное от файла", "file-hash"),
    "filetype": ("file.type", "mime", "count"),
    "fileversion": ("vtigerData.fileversion", "string", "count"),
    "filedownloadcount": ("vtigerData.filedownloadcount", "int", "count+sum"),
    "notecontent": ("description", "html", "count+hash"),
    "cf_for_field": ("vtigerData.cf_for_field", "string; назначение не проверено", "count"),
}

F["Products"] = {
    "productname": ("name", "string", "count+hash"),
    "product_no": ("vtigerNo", "string (ТОВ_N)", "count+hash"),
    "discontinued": ("isActive", "в Vtiger discontinued=1 означает «активен»", "count"),
    "productcode": ("code", "string", "count+hash"),
    "vendor_id": ("vendor", "fk Vendor (в источнике пусто)", "fk"),
    "unit_price": ("unitPrice", "decimal", "count+sum"),
    "purchase_cost": ("purchaseCost", "decimal", "count+sum"),
    "usageunit": ("unit", "enum: " + D.format("Product.json") + " (единицы товаров и услуг — один список)", "count+distribution"),
    "commissionrate": ("vtigerData.commissionrate", "decimal", "count+sum"),
    "qtyinstock": ("vtigerData.qtyinstock", "decimal (складской учёт не ведётся)", "count+sum"),
    "qty_per_unit": ("vtigerData.qty_per_unit", "decimal", "count+sum"),
}

F["Services"] = {
    "servicename": ("name", "string", "count+hash"),
    "service_no": ("vtigerNo", "string (СЕР_N)", "count+hash"),
    "discontinued": ("isActive", "discontinued=1 → активна", "count"),
    "service_usageunit": ("unit", "enum: " + D.format("Product.json") + " (Дни → Days, Часы → Hours)", "count+distribution"),
    "servicecategory": ("category", "enum: " + D.format("Product.json"), "count+distribution"),
    "unit_price": ("unitPrice", "decimal", "count+sum"),
    "purchase_cost": ("purchaseCost", "decimal", "count+sum"),
    "website": ("vtigerData.website", "url", "count"),
    "sales_start_date": ("vtigerData.sales_start_date", "date", "count"),
    "sales_end_date": ("vtigerData.sales_end_date", "date", "count"),
    "start_date": ("vtigerData.start_date", "date", "count"),
    "commissionrate": ("vtigerData.commissionrate", "decimal", "count+sum"),
    "cf_billable_time_tracker": ("isBillableTime", "bool: флаг расширения TimeTracker (логика не переносится)", "count"),
    "qty_per_unit": ("qtyPerUnit", "decimal: количество единиц (подтверждено владельцем, Q-24)", "count+sum"),
}

F["Vendors"] = {
    "vendorname": ("name", "string", "count+hash"),
    "vendor_no": ("vtigerNo", "string (ПОСТ_N)", "count+hash"),
    "email": ("emailAddress", "email", "count+hash"),
    "phone": ("phoneNumber[Office]", "phone", "count+hash"),
    "website": ("website", "url", "count+hash"),
    "cf_1206": ("inn", "string (ИНН поставщика)", "count+hash"),
}

_INV_COMMON = dict(INVENTORY_HEADER, **{k: (v, "address", "count+hash") for k, v in ADDRESS_INV.items()})

F["Invoice"] = dict(_INV_COMMON, **{
    "invoice_no": ("number", "string как есть (форматы С-N и СЧЕТ_N; 2 пустых)", "count+hash"),
    "invoicedate": ("dateInvoiced", "date", "count+hash"),
    "duedate": ("dateDue", "date", "count+hash"),
    "invoicestatus": ("status", "enum: Created/Sent/Paid/Cancel/Credit Invoice/Approved + пусто", "count+distribution"),
    "customerno": ("vtigerData.customerno", "string", "count"),
    "sp_act_id": ("act", "fk Act (0..1; ни один акт не связан с >1 счётом)", "fk"),
    "received": ("vtigerData.received", "decimal: во всех записях 0 — оплата считается по Payment", "count+sum"),
    "balance": ("balanceSource", "decimal: исходное значение как контроль (не поддерживается Vtiger)", "count+sum"),
    "purchaseorder": ("vtigerData.purchaseorder", "string", "count"),
})
F["Quotes"] = dict(_INV_COMMON, **{
    "quote_no": ("number", "string (ПРЕД_N)", "count+hash"),
    "quotestage": ("status", "enum: словарь синонимов (D-19), исходное значение → vtigerData", "count+distribution"),
    "validtill": ("dateValidUntil", "date", "count+hash"),
    "potential_id": ("opportunity", "fk", "fk"),
    "assigned_user_id1": ("inventoryManager", "fk User", "fk"),
    "carrier": ("vtigerData.carrier", "enum", "count"),
    "shipping": ("vtigerData.shipping", "string", "count"),
})
F["SalesOrder"] = dict(_INV_COMMON, **{
    "salesorder_no": ("number", "string (ЗАКАЗ_N)", "count+hash"),
    "sostatus": ("status", "enum (Одобрено/Создано/Created)", "count+distribution"),
    "duedate": ("dateDue", "date", "count+hash"),
    "potential_id": ("opportunity", "fk", "fk"),
    "carrier": ("vtigerData.carrier", "enum", "count"),
    "pending": ("vtigerData.pending", "string", "count"),
    "fromsite": ("vtigerData.fromsite", "int", "count"),
    "enable_recurring": ("vtigerData.enable_recurring", "bool; периодичность закончилась в 2016", "count"),
    "recurring_frequency": ("vtigerData.recurring_frequency", "enum", "count"),
    "start_period": ("vtigerData.start_period", "date", "count"),
    "end_period": ("vtigerData.end_period", "date", "count"),
    "payment_duration": ("vtigerData.payment_duration", "enum", "count"),
    "invoicestatus": ("vtigerData.recurring_invoice_status", "enum", "count"),
    "vendor_id": ("vtigerData.vendor_id", "fk", "fk"),
})
F["Act"] = dict(_INV_COMMON, **{
    "act_no": ("number", "string: цифры; 2 дубля номера и 1 пустой (см. open-questions)", "count+hash"),
    "actdate": ("dateAct", "date", "count+hash"),
    "sp_actstatus": ("status", "enum Created/Sent/Received/Done + пусто", "count+distribution"),
})
F["Consignment"] = {}

F["SPPayments"] = {
    "pay_no": ("number", "string (цифры, уникальны)", "count+hash"),
    "pay_date": ("datePaid", "date", "count+hash"),
    "pay_type": ("direction", "Приход→incoming; Expense→outgoing", "count+distribution"),
    "payer": ("payer (Account|Contact|Vendor)", "fk (link-parent); Vendors→Vendor", "fk"),
    "related_to": ("PaymentAllocation.invoice|salesOrder", "D-11 (SourceAllocationResolver): related_to — основной, связь vtiger_crmentityrel — "
                   "только при пустом related_to; сумма = сумма платежа; расходы со связью со счётом — Q-36", "fk"),
    "type_payment": ("method", "Наличные→cash; Cashless Transfer→bank", "count+distribution"),
    "amount": ("amount", "decimal(25,8), всегда ≥0; знак задаётся direction", "count+sum"),
    "spstatus": ("status", "Executed/Запланирован/Canceled/пусто (оплатой считается только Executed; пусто — Q-37)", "count+distribution"),
    "doc_no": ("documentNumber", "int→string (номер платёжного документа)", "count+hash"),
    "pay_details": ("purpose", "string (назначение платежа)", "count+hash"),
    "analytics_code": ("vtigerData.analytics_code", "string", "count"),
    "debit": ("vtigerData.debit", "string (пусто)", "count"),
    "coracc_subacc": ("vtigerData.coracc_subacc", "string (пусто)", "count"),
    "target_code": ("vtigerData.target_code", "string (пусто)", "count"),
    "cf_1198": ("counterpartyAccount", "string (счёт контрагента)", "count+hash"),
    "cf_1200": ("counterpartyBic", "string", "count+hash"),
    "cf_1202": ("counterpartyBankName", "string", "count+hash"),
    "cf_1204": ("bankTransactionId", "string; ключ дедупликации банковского импорта", "count+hash"),
    "cf_1380": ("isForeignCurrencyAccount", "bool", "count"),
}

F["PBXManager"] = {
    "direction": ("direction", "enum: " + D.format("Call.json") + " (inbound→Inbound; outbound→Outbound)", "count+distribution"),
    "callstatus": ("status + cCallStatusRaw", "completed→Held; прочие→Not Held; исходный статус — в cCallStatusRaw", "count+distribution"),
    "customer": ("parent", "fk Contacts/Leads/Accounts (23 ссылки на удалённые контакты)", "fk"),
    "user": ("assignedUser", "user-map", "fk"),
    "customernumber": ("cPhoneNumber", "phone (для сопоставления с клиентом)", "count+hash"),
    "customertype": (None, "производное от parent", "count"),
    "starttime": ("dateStart", "datetime → UTC: до 2020-10-22 Europe/Berlin (время коннектора), далее по эпохам D-30", "count+hash"),
    "endtime": ("dateEnd", "datetime → UTC: до 2020-10-22 Europe/Berlin (время коннектора), далее по эпохам D-30; "
                           "3 звонка без endtime (длительность 0/пусто) → dateEnd = dateStart, исходное пустое значение — "
                           "в vtigerData (проверено 2026-09-30)", "count+hash"),
    "recordingurl": ("cLegacyRecordingUrl", "varchar (не url, не воспроизводится): архивная ссылка на коннектор 127.0.0.1:5000 — "
                                            "аудио недоступно (D-10)", "count"),
    "totalduration": ("duration", "секунды", "count+sum"),
    "billduration": ("cBillDuration", "секунды", "count+sum"),
    "sourceuuid": ("cConnectorCallId", "id записи во внешнем коннекторе (не Asterisk uniqueid)", "count"),
    "gateway": (None, "исключено: константа 'PBXManager'", "count"),
    "incominglinename": ("cIncomingLine", "string", "count+hash"),
    "sp_is_local_cached": (None, "исключено: служебный флаг", "count"),
    "sp_recordingurl": ("vtigerData.sp_recordingurl", "пусто", "count"),
}

F["SPCallPopup"] = {
    "callid": ("(ключ слияния с Call)", "fk PBXManager 1:1", "fk"),
    "status": (None, "исключено: служебный статус попапа", "count"),
    "comment": ("Call.description (дополнение)", "text", "count+hash"),
    "firstname": ("Call.vtigerData.popup_firstname", "string", "count"),
    "lastname": ("Call.vtigerData.popup_lastname", "string", "count"),
    "client_type": ("Call.vtigerData.popup_client_type", "string", "count"),
    "accountname": ("Call.vtigerData.popup_accountname", "string", "count"),
    "call_no": ("Call.vtigerData.popup_call_no", "string", "count"),
}

F["ModComments"] = {
    "commentcontent": ("post", "text", "count+hash"),
    "assigned_user_id": ("vtigerData.assigned_user_id", "у Note нет ответственного: автор — createdBy (userid), владелец "
                                                        "комментария сохраняется в vtigerData", "fk"),
    "related_to": ("parent", "fk на запись-родителя", "fk"),
    "customer": ("vtigerData.customer", "fk Contact", "fk"),
    "userid": ("createdBy", "vtiger_users.id (все значения — пользователи)", "fk"),
    "creator": ("createdBy", "user-map", "fk"),
    "is_private": ("vtigerData.is_private", "int", "count"),
    "filename": ("attachments", "ModComments Attachment (2 файла)", "file-hash"),
    "related_email_id": (None, "исключено: служебное", "count"),
    "parent_comments": ("vtigerData.parent_comments", "fk (пусто)", "fk"),
    "cf_comment_picklist": ("vtigerData.cf_comment_picklist", "пусто", "count"),
    "cf_comment_picklist_two": ("vtigerData.cf_comment_picklist_two", "пусто", "count"),
}

F["Project"] = {
    "projectname": ("name", "string", "count+hash"),
    "project_no": ("vtigerNo", "string (PROJ N)", "count+hash"),
    "startdate": ("dateStart", "date", "count+hash"),
    "targetenddate": ("dateEndPlanned", "date", "count+hash"),
    "actualenddate": ("dateEnd", "date", "count+hash"),
    "projectstatus": ("status", "enum: " + D.format("Project.json"), "count+distribution"),
    "projecttype": ("type", "enum: " + D.format("Project.json"), "count+distribution"),
    "linktoaccountscontacts": ("account", "fk Accounts", "fk"),
    "potentialid": ("opportunity", "fk", "fk"),
    "targetbudget": ("budget", "varchar → currency(decimal): 50 из 51 значения числовые; нечисловое → vtigerData.targetbudget "
                               "(проверено 2026-09-30)", "count+sum"),
    "projecturl": ("url", "url", "count"),
    "projectpriority": ("priority", "enum: " + D.format("Project.json"), "count+distribution"),
    "progress": ("progress", "enum: " + D.format("Project.json") + " (10%…100%)", "count+distribution"),
    "isconvertedfrompotential": ("vtigerData.isconvertedfrompotential", "bool", "count"),
}

F["ProjectTask"] = {
    "projecttaskname": ("name", "string", "count+hash"),
    "projecttask_no": ("vtigerNo", "string (PT N)", "count+hash"),
    "projecttaskpriority": ("priority", "enum: " + D.format("ProjectTask.json"), "count+distribution"),
    "projecttasktype": ("type", "enum: " + D.format("ProjectTask.json"), "count+distribution"),
    "projecttasknumber": ("orderNumber", "int", "count+sum"),
    "projectid": ("project", "fk Project", "fk"),
    "projecttaskstatus": ("status", "enum: " + D.format("ProjectTask.json") + " («Canceled » без концевого пробела)", "count+distribution"),
    "projecttaskprogress": ("progress", "enum: " + D.format("ProjectTask.json") + " (10%…100%)", "count+distribution"),
    "projecttaskhours": ("hours", "int (0…1500 в живых записях)", "count+sum"),
    "startdate": ("dateStart", "date", "count+hash"),
    "enddate": ("dateEnd", "date", "count+hash"),
    "cf_1354": ("showInStat", "bool", "count"),
    "cf_1320": ("gitCommit", "url", "count+hash"),
}

F["Users"] = {
    "user_name": ("userName", "string", "count+hash"),
    "email1": ("emailAddress", "email", "count+hash"),
    "first_name": ("firstName", "string", "count+hash"),
    "last_name": ("lastName", "string", "count+hash"),
    "user_password": (None, "исключено: секрет; пароли задаются заново", "count"),
    "confirm_password": (None, "исключено: секрет", "count"),
    "accesskey": (None, "исключено: секрет API", "count"),
    "is_admin": ("type", "эффективный флаг Vtiger ($is_admin в user_privileges): 'on' → admin (1 пользователь); '1' у user#8 "
                         "прав администратора не даёт → regular (проверено 2026-09-30; подтверждено владельцем, Q-35)", "count+distribution"),
    "roleid": ("roles", "H2→Директор, H3→Заместитель директора, H4→Менеджер по продажам, H10→Менеджер клиентов "
                        "(роли EspoCRM: itvolga-setup-acl, D-22)", "count+distribution"),
    "status": ("isActive", "Active→true", "count+distribution"),
    "title": ("title", "string", "count+hash"),
    "department": ("vtigerData.department", "string", "count"),
    "phone_work": ("phoneNumber[Office]", "phone", "count+hash"),
    "phone_mobile": ("phoneNumber[Mobile]", "phone", "count+hash"),
    "phone_home": (None, "исключено: личный телефон сотрудника (решение владельца, Q-09)", "count"),
    "phone_crm_extension": ("cPhoneExtension", "string: внутренний номер для телефонии", "count+hash"),
    "signature": ("preferences.signature", "html", "count+hash"),
    "language": ("preferences.language", "ru_ru→ru_RU", "count+distribution"),
    "time_zone": ("preferences.timeZone", "IANA", "count+distribution"),
    "date_format": ("preferences.dateFormat", "dd-mm-yyyy→DD.MM.YYYY (решить)", "count+distribution"),
    "hour_format": ("preferences.timeFormat", "24→HH:mm", "count"),
    "dayoftheweek": ("preferences.weekStart", "Monday→1", "count"),
    "currency_id": ("preferences (валюта)", "RUB", "count"),
    "imagename": ("avatar", "Users Image", "file-hash"),
    "address_street": (None, "исключено: адрес сотрудника (решение владельца, Q-09)", "count"),
    "address_city": (None, "исключено: адрес сотрудника (решение владельца, Q-09)", "count"),
    "address_state": (None, "исключено: адрес сотрудника (решение владельца, Q-09)", "count"),
    "address_postalcode": (None, "исключено: адрес сотрудника (решение владельца, Q-09)", "count"),
    "address_country": (None, "исключено: адрес сотрудника (решение владельца, Q-09)", "count"),
}
USERS_UI_PREFS = {
    "lead_view", "end_hour", "is_owner", "currency_grouping_pattern", "currency_decimal_separator",
    "currency_grouping_separator", "currency_symbol_placement", "no_of_currency_decimals", "truncate_trailing_zeros",
    "internal_mailer", "theme", "default_record_view", "leftpanelhide", "rowheight", "start_hour", "activity_view",
    "callduration", "othereventduration", "defaulteventstatus", "defaultactivitytype", "reminder_interval",
    "calendarsharedtype", "hidecompletedevents", "defaultcalendarview",
}

# Undeclared physical columns of module tables.
UNDECLARED = {
    ("vtiger_crmentity", "setype"): ("(тип сущности)", "определяет целевую сущность", "count"),
    ("vtiger_crmentity", "deleted"): ("—", "deleted=1 не переносится в рабочие сущности (остаётся в защищённом снимке)", "count"),
    ("vtiger_crmentity", "label"): (None, "производное (имя записи)", "count"),
    ("vtiger_crmentity", "version"): (None, "служебное", "count"),
    ("vtiger_crmentity", "presence"): (None, "служебное", "count"),
    ("vtiger_crmentity", "smgroupid"): (None, "служебное (все 0)", "count"),
    ("vtiger_crmentity", "crmid"): ("vtigerId", "исходный id — ключ идемпотентности импорта", "count"),
    ("vtiger_attachments", "attachmentsid"): ("Attachment.vtigerId", "id вложения", "file-hash"),
    ("vtiger_attachments", "type"): ("Attachment.type", "mime", "count"),
    ("vtiger_attachments", "path"): ("Attachment (файл)", "storage/<path>/<id>_<name> → хранилище EspoCRM", "file-hash"),
    ("vtiger_attachments", "description"): ("Attachment.vtigerData.description", "string", "count"),
    ("vtiger_attachments", "name"): ("Attachment.name", "string", "count+hash"),
    ("vtiger_inventoryproductrel", "id"): ("<Doc>Item.<документ>", "fk документа: InvoiceItem.invoice, ActItem.act, QuoteItem.quote, SalesOrderItem.salesOrder", "fk"),
    ("vtiger_inventoryproductrel", "sequence_no"): ("<Doc>Item.order", "int", "count"),
    ("vtiger_inventoryproductrel", "lineitem_id"): ("<Doc>Item.vtigerId", "id строки", "count"),
    ("vtiger_inventoryproductrel", "incrementondel"): (None, "исключено: складской флаг Vtiger", "count"),
    ("vtiger_inventoryproductrel", "description"): (None, "пусто", "count"),
    ("vtiger_invoice", "compound_taxes_info"): ("vtigerData.compound_taxes_info", "JSON (пустые списки/служебное)", "count"),
    ("vtiger_quotes", "compound_taxes_info"): ("vtigerData.compound_taxes_info", "JSON", "count"),
    ("vtiger_salesorder", "compound_taxes_info"): ("vtigerData.compound_taxes_info", "JSON", "count"),
    ("vtiger_sp_act", "compound_taxes_info"): ("vtigerData.compound_taxes_info", "JSON", "count"),
    ("vtiger_sp_consignment", "compound_taxes_info"): ("VtigerArchive.data", "JSON", "count"),
    ("vtiger_leaddetails", "converted"): ("status=Converted", "converted=1 → статус Converted", "count"),
    ("vtiger_potential", "converted"): ("vtigerData.converted", "bool", "count"),
    ("vtiger_activity_reminder", "reminder_sent"): (None, "служебное", "count"),
    ("vtiger_activity_reminder", "recurringid"): (None, "служебное", "count"),
    ("vtiger_users", "user_hash"): (None, "исключено: секрет", "count"),
    ("vtiger_users", "crypt_type"): (None, "исключено: служебное", "count"),
    ("vtiger_users", "cal_color"): (None, "исключено: UI", "count"),
    ("vtiger_users", "date_entered"): ("createdAt", "datetime", "count"),
    ("vtiger_users", "deleted"): (None, "служебное (все 0)", "count"),
    ("vtiger_vteitems", "sequence"): (None, "исключено вместе с VTEItems", "count"),
    ("vtiger_vteitems", "level"): (None, "исключено вместе с VTEItems", "count"),
    ("vtiger_crmentity_user_field", "recordid"): (None, "исключено: персональные звёздочки", "count"),
    ("vtiger_crmentity_user_field", "userid"): (None, "исключено: персональные звёздочки", "count"),
    ("vtiger_email_track", "crmid"): ("Email.vtigerData.track", "трекинг открытий писем", "count"),
    ("vtiger_email_track", "mailid"): ("Email.vtigerData.track", "трекинг открытий писем", "count"),
    ("vtiger_products", "currency_id"): (None, "одна валюта", "count"),
    ("vtiger_products", "is_subproducts_viewable"): (None, "служебное", "count"),
    ("vtiger_service", "currency_id"): (None, "одна валюта", "count"),
    ("vtiger_leadaddress", "leadaddresstype"): (None, "служебное", "count"),
    ("vtiger_contactsubdetails", "laststayintouchrequest"): (None, "служебное (0)", "count"),
    ("vtiger_contactsubdetails", "laststayintouchsavedate"): (None, "служебное (0)", "count"),
    ("vtiger_leadsubdetails", "callornot"): (None, "служебное (0)", "count"),
    ("vtiger_leadsubdetails", "readornot"): (None, "служебное (0)", "count"),
    ("vtiger_leadsubdetails", "empct"): (None, "служебное (0)", "count"),
    ("vtiger_leaddetails", "assignleadchk"): (None, "служебное (0)", "count"),
    ("vtiger_potential", "private"): (None, "служебное (0)", "count"),
    ("vtiger_potential", "runtimefee"): (None, "служебное (0)", "count"),
    ("vtiger_potential", "forecastcategory"): (None, "служебное (0)", "count"),
    ("vtiger_potential", "outcomeanalysis"): (None, "служебное (0)", "count"),
    ("vtiger_campaignrelstatus", "campaignrelstatusid"): (None, "справочник пикл-листа", "count"),
    ("vtiger_campaignrelstatus", "sortorderid"): (None, "справочник пикл-листа", "count"),
    ("vtiger_campaignrelstatus", "presence"): (None, "справочник пикл-листа", "count"),
}

# Requisites of the single legal entity (vtiger_organizationdetails, one row) → LegalEntity fields
# (finance-contract.md §11; stage 04.2). Values come only from the import and never reach Git.
ORGANIZATION = {
    "organizationname": "name", "address": "addressStreet", "city": "addressCity", "state": "addressState",
    "country": "addressCountry", "code": "addressPostalCode", "phone": "phoneNumber", "fax": "fax",
    "website": "website", "logoname": "logo", "inn": "inn", "kpp": "kpp", "okpo": "okpo",
    "bankaccount": "bankAccount", "bankname": "bankName", "bankid": "bic", "corraccount": "corrAccount",
    "director": "director", "bookkeeper": "bookkeeper", "entrepreneur": "entrepreneur",
    "entrepreneurreg": "entrepreneurRegistration", "company": "vtigerCompanyKey",
}
ORGANIZATION_NOTES = {
    "logoname": "имя файла логотипа; файл переносится при импорте (этап 06)",
    "company": "ключ юрлица SalesPlatform ('Default', D-04)",
}
ORGANIZATION_EXCLUDED = {
    "organization_id": "служебный ключ единственной строки",
    "vatid": "пусто; поле не создаётся (finance-contract.md §11)",
    "logo": "пусто: логотип хранится файлом (logoname)",
}

# Non-module tables: (regex, category, fate, target)
TABLE_RULES = [
    (r"_seq$", "последовательность", "не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации", "—"),
    (r"^vtiger_(crmentityrel|seactivityrel|cntactivityrel|salesmanactivityrel|salesmanattachmentsrel|senotesrel|seattachmentsrel|contpotentialrel|freetagged_objects|invitees)$",
     "связь", "переносится как связь (см. relations.csv)", "links EspoCRM"),
    (r"^vtiger_(modtracker_basic|modtracker_detail|modtracker_relations)$", "история изменений",
     "не переносится (решение владельца, Q-27): остаётся в защищённом снимке", "—"),
    (r"^vtiger_modtracker_tabs$", "настройка истории", "не переносится: включить аудит полей в EspoCRM", "—"),
    (r"^vtiger_(invoicestatushistory|sp_actstatushistory|potstagehistory)$", "история статусов",
     "не переносится (решение владельца, Q-27): остаётся в защищённом снимке", "—"),
    (r"^vtiger_loginhistory$", "журнал входов", "не переносится: журнал безопасности остаётся в защищённом снимке", "—"),
    (r"^vtiger_(profile|profile2.*|role|role2profile|role2picklist|def_org_share|def_org_field|org_share_.*|datashare_.*|tmp_(read|write)_user_sharing_per|groups|group2.*|users2group|user2role)$",
     "ACL", "не переносится как данные: права воспроизводятся ролями/командами EspoCRM по module-decisions.md", "Role/Team"),
    (r"^vtiger_(field|tab|tab_info|blocks|relatedlists|relatedlists_rb|fieldmodulerel|entityname|links|app2tab|parenttab|parenttabrel|settings_.*|language|version|systems|crmsetup|actionmapping|eventhandler.*|ws_.*|picklist|modentity_num|convertleadmapping|convertpotentialmapping|customerportal_.*|portal|dashboard_tabs|homedefault|homestuff|module_dashboard_widgets|user_module_preferences|mobile_alerts|import_\d+|asteriskextensions)$",
     "метаданные/настройки Vtiger", "не переносится: используется как источник проектирования модели и настроек", "—"),
    (r"^vtiger_(customview|cvadvfilter|cvadvfilter_grouping|cvcolumnlist|cvstdfilter)$", "фильтры списков",
     "не переносится автоматически: ключевые фильтры воссоздаются вручную", "—"),
    (r"^vtiger_(report|reportmodules|selectquery|selectcolumn|relcriteria|relcriteria_grouping|reportfilters|reportsortcol|reportsummary|reportdatefilter|reportfolder)$",
     "отчёты", "не переносится: отчёты не нужны (решение владельца, Q-16)", "—"),
    (r"^com_vtiger_workflow", "workflows", "не переносится как данные: логика реализуется собственными hooks/formula по decisions.md", "—"),
    (r"^vtiger_cron_task$", "планировщик", "не переносится: задачи EspoCRM Scheduled Jobs", "—"),
    (r"^(sp_templates|vtiger_emailtemplates|vtiger_quotingtool.*|vtiger_inventory_tandc|vtiger_notificationscheduler|vtiger_inventorynotification)$",
     "шаблоны", "переносится как спецификация (print-forms.md); реализация собственным кодом", "Template (собств.)"),
    (r"^vtiger_(organizationdetails)$", "реквизиты организации", "переносится в настройку юрлица (LegalEntity) — значения вне Git", "LegalEntity"),
    (r"^vtiger_spcompany$", "справочник юрлиц SalesPlatform",
     "не переносится как опции: 'Default' и 'По умолчанию' — одно юрлицо, одна запись LegalEntity (D-04)", "LegalEntity"),
    (r"^vtiger_(currency_info|currencies|inventorytaxinfo|shippingtaxinfo|inventorycharges|taxclass)$", "финансовые настройки",
     "переносится как конфигурация (валюта RUB, НДС 18% исторически)", "config"),
    (r"^vtiger_inventorychargesrel$", "доп. расходы документов", "исключено: во всех записях значения 0 (проверено)", "—"),
    (r"^vtiger_attachmentsfolder$", "папки документов", "переносится: DocumentFolder", "DocumentFolder"),
    (r"^vtiger_freetags$", "теги", "переносится как значения multiEnum tags (Faq/HelpDesk/ProjectTask)", "multiEnum"),
    (r"^vtiger_(mail_accounts|google_oauth2|google_sync.*|google_event_calendar_mapping|wsapp.*|pbxmanager_gateway|sp_voipintegration_.*|sp_voip_default_provider|sp_socialconnector_.*|ws_userauthtoken)$",
     "интеграции/секреты", "не переносится: секреты и состояние синхронизации; интеграции настраиваются заново", "—"),
    (r"^vtiger_(mailmanager_.*|mailscanner_ids|emailslookup|pbxmanager_phonelookup|activity_reminder_popup|sp_callpopup_last_call)$",
     "кэш/индексы", "не переносится: производные данные", "—"),
    (r"^berli_globalsearch", "поисковый индекс", "не переносится: производные данные", "—"),
    (r"^(vte_|vtestore_|vteemailmarketing_|vtepopupreminder_|its4you_|quoter_|kanban_|masked_|fieldautofill_|realtimefieldformulas_|relatedblockslists_|notifications_settings|time_tracker_settings|sp_tips_|sp_cml_)",
     "настройки расширений", "не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md", "—"),
    (r"^vtiger_(calendar_.*|activity_view|lead_view|default_record_view|defaultactivitytype|defaultcalendarview|defaulteventstatus|dayoftheweek|start_hour|hour_format|date_format|time_zone|rowheight|reminder_interval|callduration|othereventduration|currency_decimal_separator|currency_grouping_pattern|currency_grouping_separator|currency_symbol_placement|no_of_currency_decimals)$",
     "пользовательские настройки", "не переносится: настройки Preferences EspoCRM", "—"),
    (r"^vtiger_(productcurrencyrel)$", "цены по валютам", "исключено: одна валюта, цена берётся из unit_price", "—"),
    (r"^vtiger_sp_convert_popup_mapping$", "настройка SPCallPopup", "не переносится", "—"),
    (r"^vtiger_projecttask_status_color$", "настройка цветов статусов", "не переносится: оформление задаётся в EspoCRM", "—"),
    (r"^vtiger_[a-z0-9_]+cf$", "таблица кастомных полей без данных", "только ключ записи; кастомных колонок с данными нет", "—"),
    (r"^vtiger_", "справочник значений пикл-листа", "переносится как опции enum в метаданных EspoCRM (фактически используемые значения — в source-inventory)", "entityDefs options"),
]
