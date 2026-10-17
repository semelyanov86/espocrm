# Импорт Vtiger — каждая колонка (этап 08)

Генерируется вместе с `import-summary.md`: `task import:summary -- <прогон>` (`scripts/import/importer.py summary`). Только имена колонок, судьбы и счётчики — ни значений, ни идентификаторов записей. Контракт сверки — `import.md` («Сверка», «Полная сверка колонок»).

- Прогон: `20261017T141529`; снимок: `20261012T191003`; код: `d4a3bf1` (незакоммиченных файлов инструмента: 0).

## Колонки, которые читает импорт

Все колонки всех прочитанных таблиц по живым записям модуля (`links` — колонки таблиц связей). Категория: `rule` — переносится правилом (значения сверены проверочным проходом), `key` — ключ, `excluded`/`empty` — судьба из карты, `relation` — пара связи, `unmapped` — без строки карты (непустое значение — сбой прогона). Цель — `field-map.csv` (у CDR — в судьбе `cdr.COLUMN_FATES`).

| Модуль | Схема | Колонка | Категория | Судьба | Цель | Значений | Сверено | Расхождений | Неучтённых | Исходы |
|---|---|---|---|---|---|---|---|---|---|---|
| Accounts | vtiger7 | `vtiger_account.account_no` | rule | перенос | Account.vtigerNo | 180 | 180 | 0 | 0 | carried=180 |
| Accounts | vtiger7 | `vtiger_account.account_type` | rule | перенос | Account.type | 29 | 29 | 0 | 0 | carried=1, mapped=28 |
| Accounts | vtiger7 | `vtiger_account.accountid` | key | перенос |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_account.accountname` | rule | перенос | Account.name | 180 | 180 | 0 | 0 | carried=180 |
| Accounts | vtiger7 | `vtiger_account.annualrevenue` | empty | пусто — данных нет | Account.vtigerData.annual_revenue | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_account.email1` | rule | перенос | Account.emailAddress (primary) | 117 | 117 | 0 | 0 | carried=114, normalized=3 |
| Accounts | vtiger7 | `vtiger_account.email2` | rule | перенос | Account.emailAddress (secondary) | 15 | 15 | 0 | 0 | carried=15 |
| Accounts | vtiger7 | `vtiger_account.emailoptout` | empty | пусто — данных нет | Account.emailAddressIsOptedOut | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_account.employees` | rule | перенос | Account.cEmployees | 180 | 43 | 0 | 0 | carried=43, zero_empty=137 |
| Accounts | vtiger7 | `vtiger_account.fax` | rule | перенос | Account.phoneNumber[Fax] | 40 | 40 | 0 | 0 | carried=9, duplicate=6, normalized=25 |
| Accounts | vtiger7 | `vtiger_account.industry` | rule | перенос | Account.industry | 89 | 89 | 0 | 0 | carried=25, mapped=64 |
| Accounts | vtiger7 | `vtiger_account.inn` | rule | перенос | Account.cInn | 90 | 90 | 0 | 0 | carried=90 |
| Accounts | vtiger7 | `vtiger_account.isconvertedfromlead` | rule | архив (только чтение) | Account.vtigerData.isconvertedfromlead | 180 | 180 | 0 | 0 | archived=180 |
| Accounts | vtiger7 | `vtiger_account.kpp` | rule | перенос | Account.cKpp | 76 | 76 | 0 | 0 | carried=76 |
| Accounts | vtiger7 | `vtiger_account.notify_owner` | excluded | исключено: исключено: флаг стандартного workflow уведомления |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_account.one_s_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_account.otherphone` | rule | перенос | Account.phoneNumber[Other] | 27 | 27 | 0 | 0 | carried=12, normalized=15 |
| Accounts | vtiger7 | `vtiger_account.ownership` | rule | архив (только чтение) | Account.vtigerData.ownership | 8 | 8 | 0 | 0 | archived=8 |
| Accounts | vtiger7 | `vtiger_account.parentid` | empty | пусто — данных нет | Account.parent (cParentAccount) | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_account.phone` | rule | перенос | Account.phoneNumber[Office] | 46 | 46 | 0 | 0 | carried=19, normalized=26, type_conflict=1 |
| Accounts | vtiger7 | `vtiger_account.rating` | rule | перенос | Account.cRating | 55 | 55 | 0 | 0 | mapped=55 |
| Accounts | vtiger7 | `vtiger_account.siccode` | rule | перенос | Account.sicCode | 66 | 66 | 0 | 0 | carried=66 |
| Accounts | vtiger7 | `vtiger_account.splastsms` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_account.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_account.tickersymbol` | rule | перенос | Account.cShortName | 99 | 99 | 0 | 0 | carried=99 |
| Accounts | vtiger7 | `vtiger_account.website` | rule | перенос | Account.website | 95 | 95 | 0 | 0 | carried=95 |
| Accounts | vtiger7 | `vtiger_accountbillads.accountaddressid` | key | перенос |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_accountbillads.bill_city` | rule | перенос | Account.billingAddressCity | 128 | 128 | 0 | 0 | carried=128 |
| Accounts | vtiger7 | `vtiger_accountbillads.bill_code` | rule | перенос | Account.billingAddressPostalCode | 100 | 100 | 0 | 0 | carried=100 |
| Accounts | vtiger7 | `vtiger_accountbillads.bill_country` | rule | перенос | Account.billingAddressCountry | 116 | 116 | 0 | 0 | carried=116 |
| Accounts | vtiger7 | `vtiger_accountbillads.bill_pobox` | empty | пусто — данных нет | Account.vtigerData.bill_pobox | 0 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_accountbillads.bill_state` | rule | перенос | Account.billingAddressState | 75 | 75 | 0 | 0 | carried=75 |
| Accounts | vtiger7 | `vtiger_accountbillads.bill_street` | rule | перенос | Account.billingAddressStreet | 127 | 127 | 0 | 0 | carried=127 |
| Accounts | vtiger7 | `vtiger_accountscf.accountid` | key | перенос |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_accountscf.cf_1109` | rule | перенос | Account.cBankAccount | 156 | 156 | 0 | 0 | carried=156 |
| Accounts | vtiger7 | `vtiger_accountscf.cf_1111` | rule | перенос | Account.cBankName | 78 | 78 | 0 | 0 | carried=78 |
| Accounts | vtiger7 | `vtiger_accountscf.cf_1113` | rule | перенос | Account.cCorrAccount | 154 | 154 | 0 | 0 | carried=154 |
| Accounts | vtiger7 | `vtiger_accountscf.cf_1115` | rule | перенос | Account.cBic | 155 | 155 | 0 | 0 | carried=155 |
| Accounts | vtiger7 | `vtiger_accountscf.tw_url` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_accountscf.vk_url` | rule | перенос | Account.cVkUrl | 3 | 3 | 0 | 0 | carried=3 |
| Accounts | vtiger7 | `vtiger_accountshipads.accountaddressid` | key | перенос |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_accountshipads.ship_city` | rule | перенос | Account.shippingAddressCity | 128 | 128 | 0 | 0 | carried=128 |
| Accounts | vtiger7 | `vtiger_accountshipads.ship_code` | rule | перенос | Account.shippingAddressPostalCode | 97 | 97 | 0 | 0 | carried=97 |
| Accounts | vtiger7 | `vtiger_accountshipads.ship_country` | rule | перенос | Account.shippingAddressCountry | 116 | 116 | 0 | 0 | carried=116 |
| Accounts | vtiger7 | `vtiger_accountshipads.ship_pobox` | rule | архив (только чтение) | Account.vtigerData.ship_pobox | 1 | 1 | 0 | 0 | archived=1 |
| Accounts | vtiger7 | `vtiger_accountshipads.ship_state` | rule | перенос | Account.shippingAddressState | 75 | 75 | 0 | 0 | carried=75 |
| Accounts | vtiger7 | `vtiger_accountshipads.ship_street` | rule | перенос | Account.shippingAddressStreet | 127 | 127 | 0 | 0 | carried=127 |
| Accounts | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Account.createdAt | 180 | 180 | 0 | 0 | carried=180 |
| Accounts | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Account.description | 82 | 82 | 0 | 0 | carried=82 |
| Accounts | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Account.modifiedBy | 180 | 180 | 0 | 0 | linked=180 |
| Accounts | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Account.modifiedAt | 180 | 180 | 0 | 0 | carried=180 |
| Accounts | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Account.createdBy | 180 | 180 | 0 | 0 | linked=180 |
| Accounts | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Account.assignedUser / teams | 180 | 180 | 0 | 0 | linked=180 |
| Accounts | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 180 |  |  |  |  |
| Accounts | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Act (собственная).createdAt | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Act (собственная).description | 1 | 1 | 0 | 0 | carried=1 |
| Act | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 402 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Act (собственная).modifiedBy | 404 | 404 | 0 | 0 | linked=404 |
| Act | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Act (собственная).modifiedAt | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Act (собственная).createdBy | 404 | 404 | 0 | 0 | linked=404 |
| Act | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Act (собственная).assignedUser / teams | 404 | 404 | 0 | 0 | linked=404 |
| Act | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_inventoryproductrel.comment` | rule | перенос | Act (собственная).ActItem.description | 406 | 406 | 0 | 0 | carried=406 |
| Act | vtiger7 | `vtiger_inventoryproductrel.description` | excluded | исключено: пусто |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_inventoryproductrel.discount_amount` | rule | перенос | Act (собственная).ActItem.discountAmount | 1 | 1 | 0 | 0 | carried=1 |
| Act | vtiger7 | `vtiger_inventoryproductrel.discount_percent` | rule | пусто — данных нет | Act (собственная).ActItem.discountPercent | 0 | 0 | 0 | 0 |  |
| Act | vtiger7 | `vtiger_inventoryproductrel.id` | rule | перенос |  | 417 | 417 | 0 | 0 | linked=417 |
| Act | vtiger7 | `vtiger_inventoryproductrel.image` | excluded | исключено: исключено: пустое служебное поле |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_inventoryproductrel.incrementondel` | excluded | исключено: исключено: складской флаг Vtiger |  | 417 |  |  |  |  |
| Act | vtiger7 | `vtiger_inventoryproductrel.lineitem_id` | key | перенос |  | 417 |  |  |  |  |
| Act | vtiger7 | `vtiger_inventoryproductrel.listprice` | rule | перенос | Act (собственная).ActItem.unitPrice | 417 | 417 | 0 | 0 | carried=417 |
| Act | vtiger7 | `vtiger_inventoryproductrel.margin` | rule | перенос | Act (собственная).ActItem.margin | 417 | 417 | 0 | 0 | carried=417 |
| Act | vtiger7 | `vtiger_inventoryproductrel.productid` | rule | перенос | Act (собственная).ActItem.product | 417 | 417 | 0 | 0 | linked=417 |
| Act | vtiger7 | `vtiger_inventoryproductrel.purchase_cost` | rule | пусто — данных нет | Act (собственная).ActItem.purchaseCost | 417 | 417 | 0 | 0 | carried=417 |
| Act | vtiger7 | `vtiger_inventoryproductrel.quantity` | rule | перенос | Act (собственная).ActItem.quantity | 417 | 417 | 0 | 0 | carried=417 |
| Act | vtiger7 | `vtiger_inventoryproductrel.sequence_no` | rule | перенос |  | 417 | 417 | 0 | 0 | carried=417 |
| Act | vtiger7 | `vtiger_inventoryproductrel.tax1` | rule | пусто — данных нет | Act (собственная).ActItem.taxRate | 0 | 0 | 0 | 0 |  |
| Act | vtiger7 | `vtiger_inventoryproductrel.tax2` | rule | пусто — данных нет | Act (собственная).ActItem.vtigerData.tax2 | 0 | 0 | 0 | 0 |  |
| Act | vtiger7 | `vtiger_inventoryproductrel.tax3` | rule | пусто — данных нет | Act (собственная).ActItem.vtigerData.tax3 | 0 | 0 | 0 | 0 |  |
| Act | vtiger7 | `vtiger_sp_act.accountid` | rule | перенос | Act (собственная).account | 404 | 404 | 0 | 0 | linked=404 |
| Act | vtiger7 | `vtiger_sp_act.act_no` | rule | перенос | Act (собственная).number | 403 | 403 | 0 | 0 | carried=403 |
| Act | vtiger7 | `vtiger_sp_act.actdate` | rule | перенос | Act (собственная).dateAct | 403 | 403 | 0 | 0 | carried=403 |
| Act | vtiger7 | `vtiger_sp_act.actid` | key | перенос |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_sp_act.adjustment` | rule | пусто — данных нет | Act (собственная).adjustment | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_act.compound_taxes_info` | rule | архив (только чтение) |  | 404 | 404 | 0 | 0 | archived=404 |
| Act | vtiger7 | `vtiger_sp_act.contactid` | rule | перенос | Act (собственная).contact | 404 | 6 | 0 | 0 | linked=6, zero_empty=398 |
| Act | vtiger7 | `vtiger_sp_act.conversion_rate` | excluded | исключено: исключено: всегда 1.000 (одна валюта) |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_sp_act.currency_id` | rule | перенос | Act (собственная).currency | 404 | 404 | 0 | 0 | mapped=404 |
| Act | vtiger7 | `vtiger_sp_act.discount_amount` | rule | пусто — данных нет | Act (собственная).discountAmount | 0 | 0 | 0 | 0 |  |
| Act | vtiger7 | `vtiger_sp_act.discount_percent` | rule | пусто — данных нет | Act (собственная).discountPercent | 0 | 0 | 0 | 0 |  |
| Act | vtiger7 | `vtiger_sp_act.pre_tax_total` | rule | перенос | Act (собственная).preTaxTotal | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_act.region_id` | rule | перенос (значимы NULL и 0) | Act (собственная).sourceFormula + vtigerData.region_id | 404 | 404 | 0 | 0 | archived=404 |
| Act | vtiger7 | `vtiger_sp_act.s_h_amount` | rule | пусто — данных нет | Act (собственная).shippingAmount | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_act.s_h_percent` | rule | пусто — данных нет | Act (собственная).shippingTaxPercent | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_act.salesorderid` | excluded | исключено: у актов пусто — поле не создаётся (finance-contract.md §11, Act) |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_sp_act.shipping` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_sp_act.sp_actstatus` | rule | перенос | Act (собственная).status | 390 | 390 | 0 | 0 | carried=390 |
| Act | vtiger7 | `vtiger_sp_act.spcompany` | rule | перенос | Act (собственная).legalEntity + vtigerData.spcompany | 404 | 404 | 0 | 0 | archived=404 |
| Act | vtiger7 | `vtiger_sp_act.subject` | rule | перенос | Act (собственная).name | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_act.subtotal` | rule | перенос | Act (собственная).subtotal | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_act.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Act | vtiger7 | `vtiger_sp_act.taxtype` | rule | перенос | Act (собственная).taxMode | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_act.total` | rule | перенос | Act (собственная).grandTotal | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_actbillads.actbilladdressid` | key | перенос |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_sp_actbillads.bill_city` | rule | перенос | Act (собственная).billingAddressCity | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_actbillads.bill_code` | rule | перенос | Act (собственная).billingAddressPostalCode | 401 | 401 | 0 | 0 | carried=401 |
| Act | vtiger7 | `vtiger_sp_actbillads.bill_country` | rule | перенос | Act (собственная).billingAddressCountry | 403 | 403 | 0 | 0 | carried=403 |
| Act | vtiger7 | `vtiger_sp_actbillads.bill_pobox` | rule | пусто — данных нет | Act (собственная).vtigerData.bill_pobox | 0 | 0 | 0 | 0 |  |
| Act | vtiger7 | `vtiger_sp_actbillads.bill_state` | rule | перенос | Act (собственная).billingAddressState | 202 | 202 | 0 | 0 | carried=202 |
| Act | vtiger7 | `vtiger_sp_actbillads.bill_street` | rule | перенос | Act (собственная).billingAddressStreet | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_actcf.actid` | excluded | только ключ записи; кастомных колонок с данными нет |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_sp_actshipads.actshipaddressid` | key | перенос |  | 404 |  |  |  |  |
| Act | vtiger7 | `vtiger_sp_actshipads.ship_city` | rule | перенос | Act (собственная).shippingAddressCity | 404 | 404 | 0 | 0 | carried=404 |
| Act | vtiger7 | `vtiger_sp_actshipads.ship_code` | rule | перенос | Act (собственная).shippingAddressPostalCode | 401 | 401 | 0 | 0 | carried=401 |
| Act | vtiger7 | `vtiger_sp_actshipads.ship_country` | rule | перенос | Act (собственная).shippingAddressCountry | 403 | 403 | 0 | 0 | carried=403 |
| Act | vtiger7 | `vtiger_sp_actshipads.ship_pobox` | rule | архив (только чтение) | Act (собственная).vtigerData.ship_pobox | 40 | 40 | 0 | 0 | archived=40 |
| Act | vtiger7 | `vtiger_sp_actshipads.ship_state` | rule | перенос | Act (собственная).shippingAddressState | 206 | 206 | 0 | 0 | carried=206 |
| Act | vtiger7 | `vtiger_sp_actshipads.ship_street` | rule | перенос | Act (собственная).shippingAddressStreet | 404 | 404 | 0 | 0 | carried=404 |
| Assets | vtiger7 | `vtiger_assets.account` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.account | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.asset_no` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.asset_no | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.assetname` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.assetname | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.assetsid` | key | перенос |  | 3 |  |  |  |  |
| Assets | vtiger7 | `vtiger_assets.assetstatus` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.assetstatus | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.contact` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.contact | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.dateinservice` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.dateinservice | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.datesold` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.datesold | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.invoiceid` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.invoiceid | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.product` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.product | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.serialnumber` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.serialnumber | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_assets.shippingmethod` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.shippingmethod | 0 | 0 | 0 | 0 |  |
| Assets | vtiger7 | `vtiger_assets.shippingtrackingnumber` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.shippingtrackingnumber | 0 | 0 | 0 | 0 |  |
| Assets | vtiger7 | `vtiger_assets.tagnumber` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.tagnumber | 0 | 0 | 0 | 0 |  |
| Assets | vtiger7 | `vtiger_assets.tags` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.tags | 0 | 0 | 0 | 0 |  |
| Assets | vtiger7 | `vtiger_assetscf.assetsid` | excluded | только ключ записи; кастомных колонок с данными нет |  | 3 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.createdtime` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.createdtime | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 3 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 3 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.description` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.description | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 3 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.modifiedby` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.modifiedby | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.modifiedtime | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 3 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 3 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.created_user_id | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 3 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.smownerid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.assigned_user_id | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_crmentity.source` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.source | 3 | 3 | 0 | 0 | archived=3 |
| Assets | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 3 |  |  |  |  |
| Assets | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Attachments | vtiger7 | `vtiger_attachments.attachmentsid` | key | перенос |  | 204 |  |  |  |  |
| Attachments | vtiger7 | `vtiger_attachments.description` | rule | архив (только чтение) |  | 3 | 3 | 0 | 0 | archived=3 |
| Attachments | vtiger7 | `vtiger_attachments.name` | rule | правило без строки карты: Attachment.name |  | 204 | 204 | 0 | 0 | carried=204 |
| Attachments | vtiger7 | `vtiger_attachments.path` | rule | перенос |  | 204 | 204 | 0 | 0 | carried=204 |
| Attachments | vtiger7 | `vtiger_attachments.subject` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Attachments | vtiger7 | `vtiger_attachments.type` | rule | перенос |  | 204 | 204 | 0 | 0 | carried=204 |
| CDR | asteriskcdrdb | `cdr.accountcode` | rule | исключено: диалпланом не заполняется |  | 0 | 0 | 0 | 0 |  |
| CDR | asteriskcdrdb | `cdr.amaflags` | rule | исключено: служебный флаг учёта Asterisk |  | 124 | 0 | 0 | 0 | excluded=124 |
| CDR | asteriskcdrdb | `cdr.billsec` | rule | перенос: Call.cBillDuration, cAnsweredAt |  | 124 | 65 | 0 | 0 | carried=65, not_applicable:trainer=59 |
| CDR | asteriskcdrdb | `cdr.calldate` | rule | перенос: Call.dateStart/dateEnd (местное время АТС Europe/Berlin → UTC; у строки с парой в CSV — время CSV) |  | 124 | 65 | 0 | 0 | carried=65, not_applicable:trainer=59 |
| CDR | asteriskcdrdb | `cdr.channel` | rule | перенос: направление звонка, внутренний номер звонящего |  | 124 | 65 | 0 | 0 | carried=65, not_applicable:trainer=59 |
| CDR | asteriskcdrdb | `cdr.clid` | rule | исключено: имя и номер звонящего — то же, что src (Call.cPhoneNumber) |  | 124 | 0 | 0 | 0 | excluded=124 |
| CDR | asteriskcdrdb | `cdr.dcontext` | rule | перенос: признак класса звонка (тренажёр, конференция, линия), отдельного поля нет |  | 124 | 65 | 0 | 0 | carried=65, not_applicable:trainer=59 |
| CDR | asteriskcdrdb | `cdr.disposition` | rule | перенос: Call.status, cCallStatusRaw |  | 124 | 65 | 0 | 0 | carried=65, not_applicable:trainer=59 |
| CDR | asteriskcdrdb | `cdr.dst` | rule | перенос: Call.cPhoneNumber исходящего, cIncomingLine |  | 124 | 65 | 0 | 0 | carried=65, not_applicable:trainer=59 |
| CDR | asteriskcdrdb | `cdr.dstchannel` | rule | перенос: ответственный и участники (телефоны, которые звонили и ответили) |  | 50 | 50 | 0 | 0 | carried=50 |
| CDR | asteriskcdrdb | `cdr.duration` | rule | перенос: Call.dateEnd (начало + duration) |  | 124 | 65 | 0 | 0 | carried=65, not_applicable:trainer=59 |
| CDR | asteriskcdrdb | `cdr.id` | key | только ключ записи: номер строки CDR MySQL (в приватном отчёте) |  | 124 |  |  |  | key=124 |
| CDR | asteriskcdrdb | `cdr.lastapp` | rule | перенос: признак ответа человека (плечо Dial) и класса звонка, отдельного поля нет |  | 124 | 65 | 0 | 0 | carried=65, not_applicable:trainer=59 |
| CDR | asteriskcdrdb | `cdr.lastdata` | rule | исключено: аргументы приложения диалплана (строки набора, параметры) |  | 110 | 0 | 0 | 0 | excluded=110 |
| CDR | asteriskcdrdb | `cdr.linkedid` | key | только ключ записи: Call.cAsteriskLinkedId (плечи одного звонка) |  | 124 |  |  |  | key=124 |
| CDR | asteriskcdrdb | `cdr.peeraccount` | rule | исключено: диалпланом не заполняется |  | 0 | 0 | 0 | 0 |  |
| CDR | asteriskcdrdb | `cdr.recordingpath` | rule | перенос: Call.cRecordingPath/cRecording после проверки размера и sha256 |  | 107 | 51 | 0 | 0 | carried=51, not_applicable:recording_without_audio=1, not_applicable:trainer=55 |
| CDR | asteriskcdrdb | `cdr.sequence` | key | только ключ записи: строка CDR (uniqueid, sequence) |  | 124 |  |  |  | key=124 |
| CDR | asteriskcdrdb | `cdr.src` | rule | перенос: Call.cPhoneNumber входящего, звонящий для сопоставления записи (D-31) |  | 116 | 65 | 0 | 0 | carried=65, not_applicable:trainer=51 |
| CDR | asteriskcdrdb | `cdr.uniqueid` | key | только ключ записи: строка CDR (uniqueid, sequence), ключ звонка CSV |  | 124 |  |  |  | key=124 |
| CDR | asteriskcdrdb | `cdr.userfield` | rule | исключено: диалпланом не заполняется |  | 0 | 0 | 0 | 0 |  |
| Calendar | vtiger7 | `vtiger_activity.activityid` | key | перенос |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.activitytype` | rule | исключено: служебное: Task |  | 34 | 34 | 0 | 0 | carried=34 |
| Calendar | vtiger7 | `vtiger_activity.date_start` | rule | перенос | Task.dateStart | 34 | 34 | 0 | 0 | carried=34 |
| Calendar | vtiger7 | `vtiger_activity.due_date` | rule | перенос | Task.dateEnd | 34 | 34 | 0 | 0 | carried=34 |
| Calendar | vtiger7 | `vtiger_activity.duration_hours` | excluded | исключено: вычисляется из dateStart/dateEnd |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.duration_minutes` | excluded | исключено: вычисляется |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.duration_seconds` | unmapped |  |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.eventstatus` | excluded | исключено: не используется для задач |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.invoiceid` | unmapped |  |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.location` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.notime` | excluded | исключено: исключено: все 0 |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.popup_reminder_date` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.popup_reminder_time` | excluded | исключено: исключено: служебное |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.priority` | rule | перенос | Task.priority | 8 | 8 | 0 | 0 | carried=6, mapped=2 |
| Calendar | vtiger7 | `vtiger_activity.recurringtype` | excluded | исключено: пусто |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.salesorder_id` | unmapped |  |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.semodule` | unmapped |  |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.sendnotification` | excluded | исключено: исключено: флаг уведомления (все 0) |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.status` | rule | перенос | Task.status | 34 | 34 | 0 | 0 | carried=32, mapped=2 |
| Calendar | vtiger7 | `vtiger_activity.subject` | rule | перенос | Task.name | 34 | 34 | 0 | 0 | carried=34 |
| Calendar | vtiger7 | `vtiger_activity.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.time_end` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.time_start` | rule | перенос | Task.dateStart (время) | 34 | 34 | 0 | 0 | carried=34 |
| Calendar | vtiger7 | `vtiger_activity.timesheet_id` | unmapped |  |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_activity.visibility` | excluded | исключено: исключено: все Private (ACL задаётся владельцем) |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Task.createdAt | 34 | 34 | 0 | 0 | carried=34 |
| Calendar | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Task.description | 16 | 16 | 0 | 0 | carried=16 |
| Calendar | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Task.modifiedBy | 34 | 34 | 0 | 0 | linked=34 |
| Calendar | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Task.modifiedAt | 34 | 34 | 0 | 0 | carried=34 |
| Calendar | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Task.createdBy | 34 | 34 | 0 | 0 | linked=34 |
| Calendar | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Task.assignedUser / teams | 34 | 34 | 0 | 0 | linked=34 |
| Calendar | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 34 |  |  |  |  |
| Calendar | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.createdtime` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.createdtime | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.description` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.description | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.modifiedby` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.modifiedby | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.modifiedtime | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.created_user_id | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.smownerid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.assigned_user_id | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_crmentity.source` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.source | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.comment` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.comment | 3 | 3 | 0 | 0 | archived=3 |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.description` | excluded | исключено: пусто |  | 0 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.discount_amount` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.discount_amount | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.discount_percent` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.discount_percent | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.id` | rule | перенос |  | 3 | 3 | 0 | 0 | archived=3 |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.image` | empty | пусто — данных нет | VtigerArchive.VtigerArchive.data.image | 0 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.incrementondel` | excluded | исключено: исключено: складской флаг Vtiger |  | 3 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.lineitem_id` | key | перенос |  | 3 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.listprice` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.listprice | 3 | 3 | 0 | 0 | archived=3 |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.margin` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.margin | 3 | 3 | 0 | 0 | archived=3 |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.productid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.productid | 3 | 3 | 0 | 0 | archived=3 |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.purchase_cost` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.purchase_cost | 3 | 3 | 0 | 0 | archived=3 |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.quantity` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.quantity | 3 | 3 | 0 | 0 | archived=3 |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.sequence_no` | rule | перенос |  | 3 | 3 | 0 | 0 | archived=3 |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.tax1` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.tax1 | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.tax2` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.tax2 | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_inventoryproductrel.tax3` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.tax3 | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_sp_consignment.accountid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.account_id | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.adjustment` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.txtAdjustment | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.compound_taxes_info` | rule | перенос |  | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.consignment_no` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.consignment_no | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.consignmentdate` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.consignmentdate | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.consignmentid` | key | перенос |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_sp_consignment.contactid` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.contact_id | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.conversion_rate` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.conversion_rate | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.currency_id` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.currency_id | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.discount_amount` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.hdnDiscountAmount | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_sp_consignment.discount_percent` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.hdnDiscountPercent | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_sp_consignment.goods_consignment_no` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.goods_consignment_no | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.has_goods_consignment` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.has_goods_consignment | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.invoiceid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.invoice_id | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.pre_tax_total` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.pre_tax_total | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.region_id` | rule | перенос (значимы NULL и 0) | VtigerArchive.VtigerArchive.data.region_id | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.s_h_amount` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.hdnS_H_Amount | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.s_h_percent` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.hdnS_H_Percent | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.salesorderid` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.salesorder_id | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_sp_consignment.shipping` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_sp_consignment.sp_consignmentstatus` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.sp_consignmentstatus | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_sp_consignment.spcompany` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.spcompany | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.subject` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.subject | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.subtotal` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.hdnSubTotal | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.tags` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.tags | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_sp_consignment.taxtype` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.hdnTaxType | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignment.total` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.hdnGrandTotal | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentbillads.bill_city` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.bill_city | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentbillads.bill_code` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.bill_code | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentbillads.bill_country` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.bill_country | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentbillads.bill_pobox` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.bill_pobox | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_sp_consignmentbillads.bill_state` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.bill_state | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentbillads.bill_street` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.bill_street | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentbillads.consignmentbilladdressid` | key | перенос |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_sp_consignmentcf.consignmentid` | excluded | только ключ записи; кастомных колонок с данными нет |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_sp_consignmentshipads.consignmentshipaddressid` | key | перенос |  | 1 |  |  |  |  |
| Consignment | vtiger7 | `vtiger_sp_consignmentshipads.ship_city` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.ship_city | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentshipads.ship_code` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.ship_code | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentshipads.ship_country` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.ship_country | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentshipads.ship_pobox` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.ship_pobox | 0 | 0 | 0 | 0 |  |
| Consignment | vtiger7 | `vtiger_sp_consignmentshipads.ship_state` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.ship_state | 1 | 1 | 0 | 0 | archived=1 |
| Consignment | vtiger7 | `vtiger_sp_consignmentshipads.ship_street` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.ship_street | 1 | 1 | 0 | 0 | archived=1 |
| Contacts | vtiger7 | `vtiger_contactaddress.contactaddressid` | key | перенос |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactaddress.mailingcity` | rule | перенос | Contact.addressCity | 212 | 212 | 0 | 0 | carried=212 |
| Contacts | vtiger7 | `vtiger_contactaddress.mailingcountry` | rule | перенос | Contact.addressCountry | 182 | 182 | 0 | 0 | carried=182 |
| Contacts | vtiger7 | `vtiger_contactaddress.mailingpobox` | empty | пусто — данных нет | Contact.vtigerData.mailingpobox | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactaddress.mailingstate` | rule | перенос | Contact.addressState | 159 | 159 | 0 | 0 | carried=159 |
| Contacts | vtiger7 | `vtiger_contactaddress.mailingstreet` | rule | перенос | Contact.addressStreet | 204 | 204 | 0 | 0 | carried=204 |
| Contacts | vtiger7 | `vtiger_contactaddress.mailingzip` | rule | перенос | Contact.addressPostalCode | 151 | 151 | 0 | 0 | carried=151 |
| Contacts | vtiger7 | `vtiger_contactaddress.othercity` | rule | перенос | Contact.cOtherAddressCity | 156 | 156 | 0 | 0 | carried=156 |
| Contacts | vtiger7 | `vtiger_contactaddress.othercountry` | rule | перенос | Contact.cOtherAddressCountry | 154 | 154 | 0 | 0 | carried=154 |
| Contacts | vtiger7 | `vtiger_contactaddress.otherpobox` | empty | пусто — данных нет | Contact.vtigerData.otherpobox | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactaddress.otherstate` | rule | перенос | Contact.cOtherAddressState | 136 | 136 | 0 | 0 | carried=136 |
| Contacts | vtiger7 | `vtiger_contactaddress.otherstreet` | rule | перенос | Contact.cOtherAddressStreet | 154 | 154 | 0 | 0 | carried=154 |
| Contacts | vtiger7 | `vtiger_contactaddress.otherzip` | rule | перенос | Contact.cOtherAddressPostalCode | 151 | 151 | 0 | 0 | carried=151 |
| Contacts | vtiger7 | `vtiger_contactdetails.accountid` | rule | перенос | Contact.account (accounts primary) | 341 | 234 | 0 | 0 | linked=234, zero_empty=107 |
| Contacts | vtiger7 | `vtiger_contactdetails.contact_no` | rule | перенос | Contact.vtigerNo | 341 | 341 | 0 | 0 | carried=341 |
| Contacts | vtiger7 | `vtiger_contactdetails.contactid` | key | перенос |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.contacttype` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.department` | rule | перенос | Contact.cDepartment | 106 | 106 | 0 | 0 | carried=106 |
| Contacts | vtiger7 | `vtiger_contactdetails.donotcall` | empty | пусто — данных нет | Contact.doNotCall | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.email` | rule | перенос | Contact.emailAddress (primary) | 101 | 101 | 0 | 0 | carried=98, normalized=3 |
| Contacts | vtiger7 | `vtiger_contactdetails.emailoptout` | empty | пусто — данных нет | Contact.emailAddressIsOptedOut | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.fax` | rule | перенос | Contact.phoneNumber[Fax] | 18 | 18 | 0 | 0 | carried=5, duplicate=3, normalized=8, type_conflict=2 |
| Contacts | vtiger7 | `vtiger_contactdetails.firstname` | rule | перенос | Contact.firstName | 334 | 334 | 0 | 0 | carried=334 |
| Contacts | vtiger7 | `vtiger_contactdetails.imagename` | rule | перенос | Contact.cPhoto | 6 | 1 | 0 | 0 | linked=1, not_applicable:D-23=5 |
| Contacts | vtiger7 | `vtiger_contactdetails.isconvertedfromlead` | rule | архив (только чтение) | Contact.vtigerData.isconvertedfromlead | 341 | 341 | 0 | 0 | archived=341 |
| Contacts | vtiger7 | `vtiger_contactdetails.lastname` | rule | перенос | Contact.lastName | 341 | 341 | 0 | 0 | carried=341 |
| Contacts | vtiger7 | `vtiger_contactdetails.mobile` | rule | перенос | Contact.phoneNumber[Mobile] | 139 | 139 | 0 | 0 | carried=44, duplicate=2, normalized=85, type_conflict=8 |
| Contacts | vtiger7 | `vtiger_contactdetails.notify_owner` | excluded | исключено: исключено: флаг стандартного workflow уведомления |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.otheremail` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.phone` | rule | перенос | Contact.phoneNumber[Office] | 118 | 118 | 0 | 0 | carried=62, normalized=49, type_conflict=7 |
| Contacts | vtiger7 | `vtiger_contactdetails.reference` | excluded | исключено: исключено: истинных значений нет |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.reportsto` | excluded | исключено: исключено: во всех живых записях '0' — ссылки нет (relations.csv Contacts.reportsto = 0; проверено 2026-09-30) |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.salutation` | rule | перенос | Contact.salutationName | 3 | 3 | 0 | 0 | archived=2, carried=1 |
| Contacts | vtiger7 | `vtiger_contactdetails.secondaryemail` | rule | перенос | Contact.emailAddress (secondary) | 2 | 2 | 0 | 0 | carried=2 |
| Contacts | vtiger7 | `vtiger_contactdetails.splastsms` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.title` | rule | перенос | Contact.title | 164 | 164 | 0 | 0 | carried=150, no_target=14 |
| Contacts | vtiger7 | `vtiger_contactdetails.training` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactdetails.usertype` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactscf.cf_1322` | rule | перенос в защищённое хранилище | Contact.ContactAccess.anydeskId | 122 | 122 | 0 | 0 | protected=122 |
| Contacts | vtiger7 | `vtiger_contactscf.cf_1324` | rule | перенос в защищённое хранилище | Contact.ContactAccess.anydeskPassword | 121 | 121 | 0 | 0 | protected=121 |
| Contacts | vtiger7 | `vtiger_contactscf.cf_1326` | rule | перенос в защищённое хранилище | Contact.ContactAccess.hostname | 125 | 125 | 0 | 0 | protected=125 |
| Contacts | vtiger7 | `vtiger_contactscf.cf_1328` | rule | перенос в защищённое хранилище | Contact.ContactAccess.ipAddress | 125 | 125 | 0 | 0 | protected=125 |
| Contacts | vtiger7 | `vtiger_contactscf.cf_1372` | rule | перенос | Contact.cNeedOriginalDocs | 341 | 341 | 0 | 0 | carried=341 |
| Contacts | vtiger7 | `vtiger_contactscf.cf_1374` | rule | пусто — данных нет | Contact.cSendNews | 341 | 341 | 0 | 0 | carried=341 |
| Contacts | vtiger7 | `vtiger_contactscf.cf_1376` | rule | перенос | Contact.cPartnerAds | 341 | 341 | 0 | 0 | carried=341 |
| Contacts | vtiger7 | `vtiger_contactscf.cf_1378` | rule | пусто — данных нет | Contact.cSendAlerts | 341 | 341 | 0 | 0 | carried=341 |
| Contacts | vtiger7 | `vtiger_contactscf.contactid` | key | перенос |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactscf.tw_url` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactscf.vk_url` | rule | перенос | Contact.cVkUrl | 1 | 1 | 0 | 0 | carried=1 |
| Contacts | vtiger7 | `vtiger_contactsubdetails.assistant` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactsubdetails.assistantphone` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactsubdetails.birthday` | rule | перенос | Contact.cBirthday | 10 | 10 | 0 | 0 | carried=10 |
| Contacts | vtiger7 | `vtiger_contactsubdetails.contactsubscriptionid` | key | перенос |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactsubdetails.homephone` | rule | перенос | Contact.phoneNumber[Home] | 77 | 77 | 0 | 0 | carried=68, normalized=7, type_conflict=2 |
| Contacts | vtiger7 | `vtiger_contactsubdetails.laststayintouchrequest` | excluded | исключено: служебное (0) |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactsubdetails.laststayintouchsavedate` | excluded | исключено: служебное (0) |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_contactsubdetails.leadsource` | rule | перенос | Contact.cLeadSource | 55 | 55 | 0 | 0 | carried=13, mapped=42 |
| Contacts | vtiger7 | `vtiger_contactsubdetails.otherphone` | rule | перенос | Contact.phoneNumber[Other] | 4 | 4 | 0 | 0 | carried=3, type_conflict=1 |
| Contacts | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Contact.createdAt | 341 | 341 | 0 | 0 | carried=341 |
| Contacts | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Contact.description | 66 | 66 | 0 | 0 | carried=66 |
| Contacts | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Contact.modifiedBy | 341 | 341 | 0 | 0 | linked=341 |
| Contacts | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Contact.modifiedAt | 341 | 341 | 0 | 0 | carried=341 |
| Contacts | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Contact.createdBy | 341 | 341 | 0 | 0 | linked=341 |
| Contacts | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Contact.assignedUser / teams | 341 | 341 | 0 | 0 | linked=341 |
| Contacts | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_customerdetails.customerid` | key | перенос |  | 341 |  |  |  |  |
| Contacts | vtiger7 | `vtiger_customerdetails.portal` | rule | архив (только чтение) | Contact.vtigerData.portal | 341 | 341 | 0 | 0 | archived=341 |
| Contacts | vtiger7 | `vtiger_customerdetails.support_end_date` | rule | перенос | Contact.cSupportEndDate | 205 | 205 | 0 | 0 | carried=205 |
| Contacts | vtiger7 | `vtiger_customerdetails.support_start_date` | rule | перенос | Contact.cSupportStartDate | 205 | 205 | 0 | 0 | carried=205 |
| Documents | vtiger7 | `vtiger_attachmentsfolder.createdby` | rule | переносится: DocumentFolder |  | 1 | 1 | 0 | 0 | linked=1 |
| Documents | vtiger7 | `vtiger_attachmentsfolder.description` | rule | переносится: DocumentFolder |  | 1 | 1 | 0 | 0 | carried=1 |
| Documents | vtiger7 | `vtiger_attachmentsfolder.folderid` | rule | переносится: DocumentFolder |  | 1 | 1 | 0 | 0 | carried=1 |
| Documents | vtiger7 | `vtiger_attachmentsfolder.foldername` | rule | переносится: DocumentFolder |  | 1 | 1 | 0 | 0 | carried=1 |
| Documents | vtiger7 | `vtiger_attachmentsfolder.sequence` | rule | переносится: DocumentFolder |  | 1 | 1 | 0 | 0 | archived=1 |
| Documents | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Document.createdAt | 215 | 215 | 0 | 0 | carried=215 |
| Documents | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 215 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 215 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.description` | unmapped |  |  | 0 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 214 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Document.modifiedBy | 215 | 215 | 0 | 0 | linked=215 |
| Documents | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Document.modifiedAt | 215 | 215 | 0 | 0 | carried=215 |
| Documents | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 215 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 215 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Document.createdBy | 215 | 215 | 0 | 0 | linked=215 |
| Documents | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 215 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Document.assignedUser / teams | 215 | 215 | 0 | 0 | linked=215 |
| Documents | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 215 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 215 |  |  |  |  |
| Documents | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Documents | vtiger7 | `vtiger_notes.filedownloadcount` | rule | архив (только чтение) | Document.vtigerData.filedownloadcount | 39 | 38 | 0 | 0 | archived=38, zero_empty=1 |
| Documents | vtiger7 | `vtiger_notes.filelocationtype` | rule | перенос | Document.(file\|cExternalUrl) | 215 | 212 | 0 | 0 | mapped=212, not_applicable:D-23=3 |
| Documents | vtiger7 | `vtiger_notes.filename` | rule | перенос | Document.file / cExternalUrl | 215 | 215 | 0 | 0 | archived=4, carried=12, derived_equal=199 |
| Documents | vtiger7 | `vtiger_notes.filesize` | rule | перенос | Document.file.size | 215 | 202 | 0 | 0 | archived=3, derived_equal=199, zero_empty=13 |
| Documents | vtiger7 | `vtiger_notes.filestatus` | rule | перенос | Document.status | 215 | 215 | 0 | 0 | mapped=215 |
| Documents | vtiger7 | `vtiger_notes.filetype` | rule | перенос | Document.file.type | 202 | 202 | 0 | 0 | archived=32, derived_equal=170 |
| Documents | vtiger7 | `vtiger_notes.fileversion` | rule | архив (только чтение) | Document.vtigerData.fileversion | 3 | 3 | 0 | 0 | archived=3 |
| Documents | vtiger7 | `vtiger_notes.folderid` | rule | перенос | Document.folder | 215 | 215 | 0 | 0 | linked=215 |
| Documents | vtiger7 | `vtiger_notes.note_no` | rule | перенос | Document.vtigerNo | 215 | 215 | 0 | 0 | carried=215 |
| Documents | vtiger7 | `vtiger_notes.notecontent` | rule | перенос | Document.description | 4 | 4 | 0 | 0 | carried=4 |
| Documents | vtiger7 | `vtiger_notes.notesid` | key | перенос |  | 215 |  |  |  |  |
| Documents | vtiger7 | `vtiger_notes.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Documents | vtiger7 | `vtiger_notes.title` | rule | перенос | Document.name | 215 | 215 | 0 | 0 | carried=215 |
| Documents | vtiger7 | `vtiger_notescf.cf_for_field` | rule | архив (только чтение) | Document.vtigerData.cf_for_field | 1 | 1 | 0 | 0 | archived=1 |
| Documents | vtiger7 | `vtiger_notescf.notesid` | key | перенос |  | 215 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.activityid` | key | перенос |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.activitytype` | excluded | исключено: служебное: Emails |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.date_start` | rule | перенос | Email.dateSent | 29 | 29 | 0 | 0 | carried=29 |
| Emails | vtiger7 | `vtiger_activity.due_date` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.duration_hours` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.duration_minutes` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.duration_seconds` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.eventstatus` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.invoiceid` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.location` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.notime` | excluded | исключено: служебное поле события Vtiger, у писем — значение по умолчанию (notime) |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.popup_reminder_date` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.popup_reminder_time` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.priority` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.recurringtype` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.salesorder_id` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.semodule` | rule | архив (только чтение) | Email.vtigerData.parent_type | 2 | 2 | 0 | 0 | archived=2 |
| Emails | vtiger7 | `vtiger_activity.sendnotification` | excluded | исключено: служебное поле события Vtiger, у писем — значение по умолчанию (sendnotification) |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.status` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.subject` | rule | перенос | Email.name | 29 | 29 | 0 | 0 | carried=29 |
| Emails | vtiger7 | `vtiger_activity.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.time_end` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.time_start` | rule | перенос | Email.dateSent (время) | 29 | 29 | 0 | 0 | carried=29 |
| Emails | vtiger7 | `vtiger_activity.timesheet_id` | unmapped |  |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_activity.visibility` | excluded | исключено: служебное поле события Vtiger, у писем — значение по умолчанию (visibility) |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Email.createdAt | 29 | 29 | 0 | 0 | carried=29 |
| Emails | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Email.body | 29 | 29 | 0 | 0 | carried=29 |
| Emails | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Email.modifiedBy | 29 | 29 | 0 | 0 | linked=29 |
| Emails | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Email.modifiedAt | 29 | 29 | 0 | 0 | carried=29 |
| Emails | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | правило без строки карты: Email.createdBy |  | 29 | 29 | 0 | 0 | linked=29 |
| Emails | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Email.assignedUser / teams | 29 | 29 | 0 | 0 | linked=29 |
| Emails | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_emaildetails.assigned_user_email` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Emails | vtiger7 | `vtiger_emaildetails.bcc_email` | rule | перенос | Email.bcc | 29 | 0 | 0 | 0 | zero_empty=29 |
| Emails | vtiger7 | `vtiger_emaildetails.cc_email` | rule | перенос | Email.cc | 29 | 0 | 0 | 0 | zero_empty=29 |
| Emails | vtiger7 | `vtiger_emaildetails.email_flag` | rule | перенос | Email.status | 29 | 29 | 0 | 0 | mapped=29 |
| Emails | vtiger7 | `vtiger_emaildetails.emailid` | key | перенос |  | 29 |  |  |  |  |
| Emails | vtiger7 | `vtiger_emaildetails.from_email` | rule | перенос | Email.fromString / from | 29 | 29 | 0 | 0 | carried=29 |
| Emails | vtiger7 | `vtiger_emaildetails.idlists` | rule | перенос | Email.parent | 29 | 29 | 0 | 0 | duplicate=29 |
| Emails | vtiger7 | `vtiger_emaildetails.to_email` | rule | перенос | Email.to | 29 | 29 | 0 | 0 | normalized=29 |
| Events | vtiger7 | `vtiger_activity.activityid` | key | перенос |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.activitytype` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.Task.cTaskType | 52 | 52 | 0 | 0 | carried=24, mapped=28 |
| Events | vtiger7 | `vtiger_activity.date_start` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.dateStart | 50 | 50 | 0 | 0 | carried=50 |
| Events | vtiger7 | `vtiger_activity.due_date` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.dateEnd | 50 | 50 | 0 | 0 | carried=50 |
| Events | vtiger7 | `vtiger_activity.duration_hours` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.Call.duration\|Meeting.duration | 52 | 52 | 0 | 0 | archived=2, derived_equal=50 |
| Events | vtiger7 | `vtiger_activity.duration_minutes` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.Call.duration\|Meeting.duration | 52 | 52 | 0 | 0 | archived=2, derived_equal=50 |
| Events | vtiger7 | `vtiger_activity.duration_seconds` | empty | пусто — данных нет | Call/Meeting/Task (вид «Письмо») по activitytype.vtigerData.duration_seconds | 0 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.eventstatus` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.status | 52 | 52 | 0 | 0 | carried=24, mapped=28 |
| Events | vtiger7 | `vtiger_activity.invoiceid` | empty | пусто — данных нет | Call/Meeting/Task (вид «Письмо») по activitytype.vtigerData.invoiceid | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.location` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.notime` | excluded | исключено: исключено: все 0 |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.popup_reminder_date` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.popup_reminder_time` | excluded | исключено: исключено: служебное |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.priority` | rule | архив (только чтение) | Call/Meeting/Task (вид «Письмо») по activitytype.vtigerData.taskpriority | 1 | 1 | 0 | 0 | archived=1 |
| Events | vtiger7 | `vtiger_activity.recurringtype` | excluded | исключено: исключено: все --None-- |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.salesorder_id` | empty | пусто — данных нет | Call/Meeting/Task (вид «Письмо») по activitytype.vtigerData.salesorder_id | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.semodule` | unmapped |  |  | 0 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.sendnotification` | excluded | исключено: исключено: все 0 |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.status` | unmapped |  |  | 0 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.subject` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.name | 52 | 52 | 0 | 0 | carried=52 |
| Events | vtiger7 | `vtiger_activity.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.time_end` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.dateEnd (время) | 50 | 50 | 0 | 0 | carried=50 |
| Events | vtiger7 | `vtiger_activity.time_start` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.dateStart (время) | 52 | 52 | 0 | 0 | archived=2, carried=50 |
| Events | vtiger7 | `vtiger_activity.timesheet_id` | empty | пусто — данных нет | Call/Meeting/Task (вид «Письмо») по activitytype.vtigerData.timesheet_id | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_activity.visibility` | excluded | исключено: исключено: все Public |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.createdAt | 52 | 52 | 0 | 0 | carried=52 |
| Events | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.description` | rule | пусто — данных нет | Call/Meeting/Task (вид «Письмо») по activitytype.description | 0 | 0 | 0 | 0 |  |
| Events | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.modifiedBy | 52 | 52 | 0 | 0 | linked=52 |
| Events | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.modifiedAt | 52 | 52 | 0 | 0 | carried=52 |
| Events | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.createdBy | 52 | 52 | 0 | 0 | linked=52 |
| Events | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Call/Meeting/Task (вид «Письмо») по activitytype.assignedUser / teams | 52 | 52 | 0 | 0 | linked=52 |
| Events | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 52 |  |  |  |  |
| Events | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | KnowledgeBaseArticle.createdAt | 63 | 63 | 0 | 0 | carried=63 |
| Faq | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 63 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 63 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.description` | unmapped |  |  | 0 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 63 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | KnowledgeBaseArticle.modifiedBy | 63 | 63 | 0 | 0 | linked=63 |
| Faq | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | KnowledgeBaseArticle.modifiedAt | 63 | 63 | 0 | 0 | carried=63 |
| Faq | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 63 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 63 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | KnowledgeBaseArticle.createdBy | 63 | 63 | 0 | 0 | linked=63 |
| Faq | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 63 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.smownerid` | rule | правило без строки карты: KnowledgeBaseArticle.assignedUser |  | 63 | 63 | 0 | 0 | linked=63 |
| Faq | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 63 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 63 |  |  |  |  |
| Faq | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Faq | vtiger7 | `vtiger_faq.answer` | rule | перенос | KnowledgeBaseArticle.body | 63 | 63 | 0 | 0 | carried=63 |
| Faq | vtiger7 | `vtiger_faq.category` | rule | перенос | KnowledgeBaseArticle.categories | 61 | 61 | 0 | 0 | mapped=61 |
| Faq | vtiger7 | `vtiger_faq.faq_no` | rule | перенос | KnowledgeBaseArticle.vtigerNo | 63 | 63 | 0 | 0 | carried=63 |
| Faq | vtiger7 | `vtiger_faq.id` | key | перенос |  | 63 |  |  |  |  |
| Faq | vtiger7 | `vtiger_faq.product_id` | rule | архив (только чтение) | KnowledgeBaseArticle.vtigerData.product_id | 63 | 0 | 0 | 0 | zero_empty=63 |
| Faq | vtiger7 | `vtiger_faq.question` | rule | перенос | KnowledgeBaseArticle.name | 63 | 63 | 0 | 0 | carried=63 |
| Faq | vtiger7 | `vtiger_faq.status` | rule | перенос | KnowledgeBaseArticle.status | 63 | 63 | 0 | 0 | carried=51, mapped=12 |
| Faq | vtiger7 | `vtiger_faq.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Faq | vtiger7 | `vtiger_faqcf.faqid` | excluded | только ключ записи; кастомных колонок с данными нет |  | 63 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Case.createdAt | 45 | 45 | 0 | 0 | carried=45 |
| HelpDesk | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Case.description | 35 | 35 | 0 | 0 | carried=35 |
| HelpDesk | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Case.modifiedBy | 45 | 45 | 0 | 0 | linked=45 |
| HelpDesk | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Case.modifiedAt | 45 | 45 | 0 | 0 | carried=45 |
| HelpDesk | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Case.createdBy | 45 | 45 | 0 | 0 | linked=45 |
| HelpDesk | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Case.assignedUser / teams | 45 | 45 | 0 | 0 | linked=45 |
| HelpDesk | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_ticketcf.from_portal` | excluded | исключено: исключено: все 0 (портал не используется) |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_ticketcf.ticketid` | key | перенос |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_troubletickets.category` | rule | перенос | Case.type | 28 | 28 | 0 | 0 | carried=28 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.contact_id` | rule | перенос | Case.contact | 45 | 7 | 0 | 0 | linked=7, zero_empty=38 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.days` | rule | архив (только чтение) | Case.vtigerData.days | 45 | 1 | 0 | 0 | archived=1, zero_empty=44 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.groupname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_troubletickets.hours` | rule | архив (только чтение) | Case.vtigerData.hours | 45 | 18 | 0 | 0 | archived=18, zero_empty=27 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.parent_id` | rule | перенос | Case.account | 45 | 42 | 0 | 0 | linked=42, zero_empty=3 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.priority` | rule | перенос | Case.priority | 45 | 45 | 0 | 0 | carried=32, mapped=13 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.product_id` | rule | архив (только чтение) | Case.vtigerData.product_id | 45 | 45 | 0 | 0 | archived=45 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.severity` | rule | перенос | Case.cSeverity | 28 | 28 | 0 | 0 | carried=26, mapped=2 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.solution` | rule | перенос | Case.cSolution | 22 | 22 | 0 | 0 | carried=22 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.status` | rule | перенос | Case.status | 45 | 45 | 0 | 0 | carried=30, mapped=15 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_troubletickets.ticket_no` | rule | перенос | Case.vtigerNo | 45 | 45 | 0 | 0 | carried=45 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.ticketid` | key | перенос |  | 45 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_troubletickets.title` | rule | перенос | Case.name | 45 | 45 | 0 | 0 | carried=45 |
| HelpDesk | vtiger7 | `vtiger_troubletickets.update_log` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| HelpDesk | vtiger7 | `vtiger_troubletickets.version_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Invoice (собственная).createdAt | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Invoice (собственная).description | 6 | 6 | 0 | 0 | carried=6 |
| Invoice | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Invoice (собственная).modifiedBy | 636 | 636 | 0 | 0 | linked=636 |
| Invoice | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Invoice (собственная).modifiedAt | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Invoice (собственная).createdBy | 636 | 636 | 0 | 0 | linked=636 |
| Invoice | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Invoice (собственная).assignedUser / teams | 636 | 636 | 0 | 0 | linked=636 |
| Invoice | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.comment` | rule | перенос | Invoice (собственная).InvoiceItem.description | 685 | 685 | 0 | 0 | carried=685 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.description` | excluded | исключено: пусто |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.discount_amount` | rule | перенос | Invoice (собственная).InvoiceItem.discountAmount | 213 | 213 | 0 | 0 | carried=213 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.discount_percent` | rule | пусто — данных нет | Invoice (собственная).InvoiceItem.discountPercent | 211 | 211 | 0 | 0 | carried=211 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.id` | rule | перенос |  | 712 | 712 | 0 | 0 | linked=712 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.image` | excluded | исключено: исключено: пустое служебное поле |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.incrementondel` | excluded | исключено: исключено: складской флаг Vtiger |  | 712 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.lineitem_id` | key | перенос |  | 712 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.listprice` | rule | перенос | Invoice (собственная).InvoiceItem.unitPrice | 712 | 712 | 0 | 0 | carried=712 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.margin` | rule | перенос | Invoice (собственная).InvoiceItem.margin | 712 | 712 | 0 | 0 | carried=712 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.productid` | rule | перенос | Invoice (собственная).InvoiceItem.product | 712 | 712 | 0 | 0 | linked=712 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.purchase_cost` | rule | пусто — данных нет | Invoice (собственная).InvoiceItem.purchaseCost | 712 | 712 | 0 | 0 | carried=712 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.quantity` | rule | перенос | Invoice (собственная).InvoiceItem.quantity | 712 | 712 | 0 | 0 | carried=712 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.sequence_no` | rule | перенос |  | 712 | 712 | 0 | 0 | carried=712 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.tax1` | rule | перенос | Invoice (собственная).InvoiceItem.taxRate | 213 | 213 | 0 | 0 | carried=213 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.tax2` | rule | пусто — данных нет | Invoice (собственная).InvoiceItem.vtigerData.tax2 | 213 | 0 | 0 | 0 | zero_empty=213 |
| Invoice | vtiger7 | `vtiger_inventoryproductrel.tax3` | rule | пусто — данных нет | Invoice (собственная).InvoiceItem.vtigerData.tax3 | 213 | 0 | 0 | 0 | zero_empty=213 |
| Invoice | vtiger7 | `vtiger_invoice.accountid` | rule | перенос | Invoice (собственная).account | 636 | 636 | 0 | 0 | linked=636 |
| Invoice | vtiger7 | `vtiger_invoice.adjustment` | rule | пусто — данных нет | Invoice (собственная).adjustment | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.balance` | rule | перенос | Invoice (собственная).balanceSource | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.compound_taxes_info` | rule | архив (только чтение) |  | 636 | 636 | 0 | 0 | archived=636 |
| Invoice | vtiger7 | `vtiger_invoice.contactid` | rule | перенос | Invoice (собственная).contact | 636 | 23 | 0 | 0 | linked=23, zero_empty=613 |
| Invoice | vtiger7 | `vtiger_invoice.conversion_rate` | excluded | исключено: исключено: всегда 1.000 (одна валюта) |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoice.currency_id` | rule | перенос | Invoice (собственная).currency | 636 | 636 | 0 | 0 | mapped=636 |
| Invoice | vtiger7 | `vtiger_invoice.customerno` | rule | архив (только чтение) | Invoice (собственная).vtigerData.customerno | 1 | 1 | 0 | 0 | archived=1 |
| Invoice | vtiger7 | `vtiger_invoice.discount_amount` | rule | перенос | Invoice (собственная).discountAmount | 1 | 1 | 0 | 0 | carried=1 |
| Invoice | vtiger7 | `vtiger_invoice.discount_percent` | rule | пусто — данных нет | Invoice (собственная).discountPercent | 0 | 0 | 0 | 0 |  |
| Invoice | vtiger7 | `vtiger_invoice.duedate` | rule | перенос | Invoice (собственная).dateDue | 536 | 536 | 0 | 0 | carried=536 |
| Invoice | vtiger7 | `vtiger_invoice.exciseduty` | rule | пусто — данных нет | Invoice (собственная).vtigerData.exciseduty | 636 | 0 | 0 | 0 | zero_empty=636 |
| Invoice | vtiger7 | `vtiger_invoice.invoice_no` | rule | перенос | Invoice (собственная).number | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.invoicedate` | rule | перенос | Invoice (собственная).dateInvoiced | 635 | 635 | 0 | 0 | carried=635 |
| Invoice | vtiger7 | `vtiger_invoice.invoiceid` | key | перенос |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoice.invoicestatus` | rule | перенос | Invoice (собственная).status | 632 | 632 | 0 | 0 | carried=632 |
| Invoice | vtiger7 | `vtiger_invoice.invoiceterms` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoice.notes` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoice.potential_id` | rule | перенос | Invoice (собственная).opportunity | 636 | 429 | 0 | 0 | linked=429, zero_empty=207 |
| Invoice | vtiger7 | `vtiger_invoice.pre_tax_total` | rule | перенос | Invoice (собственная).preTaxTotal | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.purchaseorder` | rule | пусто — данных нет | Invoice (собственная).vtigerData.purchaseorder | 0 | 0 | 0 | 0 |  |
| Invoice | vtiger7 | `vtiger_invoice.received` | rule | пусто — данных нет | Invoice (собственная).vtigerData.received | 636 | 0 | 0 | 0 | zero_empty=636 |
| Invoice | vtiger7 | `vtiger_invoice.region_id` | rule | перенос (значимы NULL и 0) | Invoice (собственная).sourceFormula + vtigerData.region_id | 485 | 485 | 0 | 0 | archived=485 |
| Invoice | vtiger7 | `vtiger_invoice.s_h_amount` | rule | пусто — данных нет | Invoice (собственная).shippingAmount | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.s_h_percent` | rule | пусто — данных нет | Invoice (собственная).shippingTaxPercent | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.salescommission` | rule | пусто — данных нет | Invoice (собственная).vtigerData.salescommission | 636 | 0 | 0 | 0 | zero_empty=636 |
| Invoice | vtiger7 | `vtiger_invoice.salesorderid` | rule | перенос | Invoice (собственная).salesOrder | 27 | 27 | 0 | 0 | linked=27 |
| Invoice | vtiger7 | `vtiger_invoice.shipping` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoice.sp_act_id` | rule | перенос | Invoice (собственная).act | 636 | 392 | 0 | 0 | linked=392, zero_empty=244 |
| Invoice | vtiger7 | `vtiger_invoice.spcompany` | rule | перенос | Invoice (собственная).legalEntity + vtigerData.spcompany | 636 | 636 | 0 | 0 | archived=636 |
| Invoice | vtiger7 | `vtiger_invoice.subject` | rule | перенос | Invoice (собственная).name | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.subtotal` | rule | перенос | Invoice (собственная).subtotal | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoice.taxtype` | rule | перенос | Invoice (собственная).taxMode | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.terms_conditions` | rule | перенос | Invoice (собственная).termsAndConditions | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.total` | rule | перенос | Invoice (собственная).grandTotal | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoice.type` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoicebillads.bill_city` | rule | перенос | Invoice (собственная).billingAddressCity | 613 | 613 | 0 | 0 | carried=613 |
| Invoice | vtiger7 | `vtiger_invoicebillads.bill_code` | rule | перенос | Invoice (собственная).billingAddressPostalCode | 576 | 576 | 0 | 0 | carried=576 |
| Invoice | vtiger7 | `vtiger_invoicebillads.bill_country` | rule | перенос | Invoice (собственная).billingAddressCountry | 631 | 631 | 0 | 0 | carried=631 |
| Invoice | vtiger7 | `vtiger_invoicebillads.bill_pobox` | rule | пусто — данных нет | Invoice (собственная).vtigerData.bill_pobox | 0 | 0 | 0 | 0 |  |
| Invoice | vtiger7 | `vtiger_invoicebillads.bill_state` | rule | перенос | Invoice (собственная).billingAddressState | 366 | 366 | 0 | 0 | carried=366 |
| Invoice | vtiger7 | `vtiger_invoicebillads.bill_street` | rule | перенос | Invoice (собственная).billingAddressStreet | 636 | 636 | 0 | 0 | carried=636 |
| Invoice | vtiger7 | `vtiger_invoicebillads.invoicebilladdressid` | key | перенос |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoicecf.invoiceid` | key | перенос |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoicecf.tax` | rule | архив (только чтение) | Invoice (собственная).vtigerData.tax | 2 | 2 | 0 | 0 | archived=2 |
| Invoice | vtiger7 | `vtiger_invoiceshipads.invoiceshipaddressid` | key | перенос |  | 636 |  |  |  |  |
| Invoice | vtiger7 | `vtiger_invoiceshipads.ship_city` | rule | перенос | Invoice (собственная).shippingAddressCity | 613 | 613 | 0 | 0 | carried=613 |
| Invoice | vtiger7 | `vtiger_invoiceshipads.ship_code` | rule | перенос | Invoice (собственная).shippingAddressPostalCode | 564 | 564 | 0 | 0 | carried=564 |
| Invoice | vtiger7 | `vtiger_invoiceshipads.ship_country` | rule | перенос | Invoice (собственная).shippingAddressCountry | 631 | 631 | 0 | 0 | carried=631 |
| Invoice | vtiger7 | `vtiger_invoiceshipads.ship_pobox` | rule | архив (только чтение) | Invoice (собственная).vtigerData.ship_pobox | 40 | 40 | 0 | 0 | archived=40 |
| Invoice | vtiger7 | `vtiger_invoiceshipads.ship_state` | rule | перенос | Invoice (собственная).shippingAddressState | 369 | 369 | 0 | 0 | carried=369 |
| Invoice | vtiger7 | `vtiger_invoiceshipads.ship_street` | rule | перенос | Invoice (собственная).shippingAddressStreet | 636 | 636 | 0 | 0 | carried=636 |
| JVmes | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.createdtime` | rule | архив (только чтение) | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.createdtime | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 267 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 267 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.description` | unmapped |  |  | 0 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 267 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.modifiedby` | rule | правило без строки карты: VtigerArchive.data.modifiedby |  | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | архив (только чтение) | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.ModifiedTime | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 267 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 267 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | правило без строки карты: VtigerArchive.data.created_user_id |  | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 267 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.smownerid` | rule | архив (только чтение) | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.assigned_user_id | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_crmentity.source` | rule | архив (только чтение) | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.source | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 267 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_jvmes.agentid` | rule | архив (только чтение) | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.agentid | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_jvmes.datemes` | rule | архив (только чтение) | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.datemes | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_jvmes.jvmesid` | key | перенос |  | 267 |  |  |  |  |
| JVmes | vtiger7 | `vtiger_jvmes.message` | rule | архив (только чтение) | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.message | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_jvmes.relatedjivo` | rule | архив (только чтение) | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.relatedjivo | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_jvmes.tags` | rule | пусто — данных нет | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.tags | 0 | 0 | 0 | 0 |  |
| JVmes | vtiger7 | `vtiger_jvmes.type` | rule | архив (только чтение) | VtigerArchive (дочерние сообщения Jivosite).VtigerArchive.data.type | 267 | 267 | 0 | 0 | archived=267 |
| JVmes | vtiger7 | `vtiger_jvmescf.jvmesid` | excluded | только ключ записи; кастомных колонок с данными нет |  | 267 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.createdtime` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.createdtime | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 49 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 49 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.description` | unmapped |  |  | 0 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 49 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.modifiedby` | rule | правило без строки карты: VtigerArchive.data.modifiedby |  | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.ModifiedTime | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 49 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 49 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | правило без строки карты: VtigerArchive.data.created_user_id |  | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 49 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.smownerid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.assigned_user_id | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_crmentity.source` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.source | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 49 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_jivosite.chatid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.chatid | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_jivosite.ipaddr` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.ipaddr | 39 | 39 | 0 | 0 | archived=39 |
| Jivosite | vtiger7 | `vtiger_jivosite.jivositeid` | key | перенос |  | 49 |  |  |  |  |
| Jivosite | vtiger7 | `vtiger_jivosite.messages` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.messages | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_jivosite.rating` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.rating | 0 | 0 | 0 | 0 |  |
| Jivosite | vtiger7 | `vtiger_jivosite.relatedcontact` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.relatedcontact | 0 | 0 | 0 | 0 |  |
| Jivosite | vtiger7 | `vtiger_jivosite.relatedleads` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.relatedleads | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_jivosite.tags` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.tags | 0 | 0 | 0 | 0 |  |
| Jivosite | vtiger7 | `vtiger_jivosite.widgetid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.widgetid | 49 | 49 | 0 | 0 | archived=49 |
| Jivosite | vtiger7 | `vtiger_jivositecf.jivositeid` | excluded | только ключ записи; кастомных колонок с данными нет |  | 49 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Lead.createdAt | 225 | 225 | 0 | 0 | carried=225 |
| Leads | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Lead.description | 79 | 79 | 0 | 0 | carried=79 |
| Leads | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Lead.modifiedBy | 225 | 225 | 0 | 0 | linked=225 |
| Leads | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Lead.modifiedAt | 225 | 225 | 0 | 0 | carried=225 |
| Leads | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Lead.createdBy | 225 | 225 | 0 | 0 | linked=225 |
| Leads | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Lead.assignedUser / teams | 225 | 225 | 0 | 0 | linked=225 |
| Leads | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadaddress.city` | rule | перенос | Lead.addressCity | 170 | 170 | 0 | 0 | carried=170 |
| Leads | vtiger7 | `vtiger_leadaddress.code` | rule | перенос | Lead.addressPostalCode | 34 | 34 | 0 | 0 | carried=34 |
| Leads | vtiger7 | `vtiger_leadaddress.country` | rule | перенос | Lead.addressCountry | 114 | 114 | 0 | 0 | carried=114 |
| Leads | vtiger7 | `vtiger_leadaddress.fax` | rule | перенос | Lead.phoneNumber[Fax] | 19 | 19 | 0 | 0 | carried=7, duplicate=1, normalized=11 |
| Leads | vtiger7 | `vtiger_leadaddress.lane` | rule | перенос | Lead.addressStreet | 122 | 122 | 0 | 0 | carried=122 |
| Leads | vtiger7 | `vtiger_leadaddress.leadaddressid` | key | перенос |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadaddress.leadaddresstype` | excluded | исключено: служебное |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadaddress.mobile` | rule | перенос | Lead.phoneNumber[Mobile] | 87 | 87 | 0 | 0 | carried=49, normalized=37, type_conflict=1 |
| Leads | vtiger7 | `vtiger_leadaddress.phone` | rule | перенос | Lead.phoneNumber[Office] | 178 | 178 | 0 | 0 | carried=62, normalized=116 |
| Leads | vtiger7 | `vtiger_leadaddress.pobox` | empty | пусто — данных нет | Lead.vtigerData.pobox | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadaddress.state` | rule | перенос | Lead.addressState | 104 | 104 | 0 | 0 | carried=104 |
| Leads | vtiger7 | `vtiger_leaddetails.annualrevenue` | rule | архив (только чтение) | Lead.vtigerData.annualrevenue | 225 | 1 | 0 | 0 | archived=1, zero_empty=224 |
| Leads | vtiger7 | `vtiger_leaddetails.assignleadchk` | excluded | исключено: служебное (0) |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.campaign` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.comments` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.company` | rule | перенос | Lead.accountName | 146 | 146 | 0 | 0 | carried=146 |
| Leads | vtiger7 | `vtiger_leaddetails.converted` | rule | перенос |  | 225 | 5 | 0 | 0 | mapped=5, zero_empty=220 |
| Leads | vtiger7 | `vtiger_leaddetails.demorequest` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.designation` | rule | перенос | Lead.title | 92 | 92 | 0 | 0 | carried=92 |
| Leads | vtiger7 | `vtiger_leaddetails.email` | rule | перенос | Lead.emailAddress (primary) | 176 | 176 | 0 | 0 | carried=170, normalized=6 |
| Leads | vtiger7 | `vtiger_leaddetails.emailoptout` | empty | пусто — данных нет | Lead.emailAddressIsOptedOut | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.evaluationstatus` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.firstname` | rule | перенос | Lead.firstName | 149 | 149 | 0 | 0 | carried=149 |
| Leads | vtiger7 | `vtiger_leaddetails.fundingsituation` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.industry` | rule | перенос | Lead.industry | 90 | 90 | 0 | 0 | carried=50, mapped=40 |
| Leads | vtiger7 | `vtiger_leaddetails.interest` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.lastname` | rule | перенос | Lead.lastName | 225 | 225 | 0 | 0 | carried=225 |
| Leads | vtiger7 | `vtiger_leaddetails.lead_no` | rule | перенос | Lead.vtigerNo | 225 | 225 | 0 | 0 | carried=225 |
| Leads | vtiger7 | `vtiger_leaddetails.leadid` | key | перенос |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.leadsource` | rule | перенос | Lead.source | 163 | 163 | 0 | 0 | carried=30, mapped=133 |
| Leads | vtiger7 | `vtiger_leaddetails.leadstatus` | rule | перенос | Lead.status | 80 | 80 | 0 | 0 | archived=4, carried=2, mapped=74 |
| Leads | vtiger7 | `vtiger_leaddetails.licencekeystatus` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.maildate` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.nextstepdate` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.noofemployees` | rule | архив (только чтение) | Lead.vtigerData.noofemployees | 225 | 19 | 0 | 0 | archived=19, zero_empty=206 |
| Leads | vtiger7 | `vtiger_leaddetails.partnercontact` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.priority` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.product` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.productversion` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.purpose` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.rating` | rule | перенос | Lead.cRating | 36 | 36 | 0 | 0 | mapped=36 |
| Leads | vtiger7 | `vtiger_leaddetails.revenuetype` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.salutation` | rule | перенос | Lead.salutationName | 7 | 7 | 0 | 0 | archived=6, carried=1 |
| Leads | vtiger7 | `vtiger_leaddetails.secondaryemail` | rule | перенос | Lead.emailAddress (secondary) | 8 | 8 | 0 | 0 | carried=8 |
| Leads | vtiger7 | `vtiger_leaddetails.space` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.splastsms` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leaddetails.transferdate` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadscf.cf_1107` | rule | перенос | Lead.cPriority | 187 | 187 | 0 | 0 | carried=187 |
| Leads | vtiger7 | `vtiger_leadscf.cf_1165` | rule | перенос | Lead.cJivositeId | 52 | 52 | 0 | 0 | carried=52 |
| Leads | vtiger7 | `vtiger_leadscf.leadid` | key | перенос |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadscf.tw_url` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadscf.vk_url` | rule | перенос | Lead.cVkUrl | 7 | 7 | 0 | 0 | carried=7 |
| Leads | vtiger7 | `vtiger_leadsubdetails.callornot` | excluded | исключено: служебное (0) |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadsubdetails.empct` | excluded | исключено: служебное (0) |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadsubdetails.leadsubscriptionid` | key | перенос |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadsubdetails.readornot` | excluded | исключено: служебное (0) |  | 225 |  |  |  |  |
| Leads | vtiger7 | `vtiger_leadsubdetails.website` | rule | перенос | Lead.website | 63 | 63 | 0 | 0 | carried=63 |
| ModComments | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Note (post).createdAt | 78 | 78 | 0 | 0 | carried=78 |
| ModComments | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.description` | unmapped |  |  | 0 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.modifiedby` | rule | правило без строки карты: Note.modifiedBy |  | 78 | 78 | 0 | 0 | linked=78 |
| ModComments | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Note (post).modifiedAt | 78 | 78 | 0 | 0 | carried=78 |
| ModComments | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Note (post).createdBy | 78 | 78 | 0 | 0 | linked=78 |
| ModComments | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.smownerid` | rule | архив (только чтение) | Note (post).vtigerData.assigned_user_id | 78 | 78 | 0 | 0 | archived=78 |
| ModComments | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_modcomments.commentcontent` | rule | перенос | Note (post).post | 78 | 78 | 0 | 0 | carried=78 |
| ModComments | vtiger7 | `vtiger_modcomments.customer` | rule | архив (только чтение) | Note (post).vtigerData.customer | 78 | 1 | 0 | 0 | archived=1, zero_empty=77 |
| ModComments | vtiger7 | `vtiger_modcomments.filename` | rule | перенос | Note (post).attachments | 77 | 2 | 0 | 0 | linked=2, zero_empty=75 |
| ModComments | vtiger7 | `vtiger_modcomments.is_private` | empty | пусто — данных нет | Note (post).vtigerData.is_private | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_modcomments.modcommentsid` | key | перенос |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_modcomments.parent_comments` | empty | пусто — данных нет | Note (post).vtigerData.parent_comments | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_modcomments.reasontoedit` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_modcomments.related_email_id` | excluded | исключено: исключено: служебное |  | 78 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_modcomments.related_to` | rule | перенос | Note (post).parent | 78 | 78 | 0 | 0 | linked=78 |
| ModComments | vtiger7 | `vtiger_modcomments.userid` | rule | перенос | Note (post).createdBy | 78 | 77 | 0 | 0 | dangling:not_a_user=1, linked=77 |
| ModComments | vtiger7 | `vtiger_modcommentscf.cf_comment_picklist` | empty | пусто — данных нет | Note (post).vtigerData.cf_comment_picklist | 0 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_modcommentscf.cf_comment_picklist_two` | empty | пусто — данных нет | Note (post).vtigerData.cf_comment_picklist_two | 0 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_modcommentscf.cf_comment_text_field` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ModComments | vtiger7 | `vtiger_modcommentscf.modcommentsid` | key | перенос |  | 78 |  |  |  |  |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.address` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.bankaccount` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.bankid` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.bankname` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.bookkeeper` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.city` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.code` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.company` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.corraccount` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.country` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.director` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.entrepreneur` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.entrepreneurreg` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.fax` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.inn` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.kpp` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.logo` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.logoname` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | linked=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.okpo` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.organization_id` | excluded | исключено: служебный ключ единственной строки |  | 1 |  |  |  |  |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.organizationname` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.phone` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.state` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.vatid` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| OrganizationDetails | vtiger7 | `vtiger_organizationdetails.website` | rule | перенос (значения вне Git) |  | 1 | 1 | 0 | 0 | carried=1 |
| PBXManager | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Call.createdAt | 1116 | 907 | 0 | 0 | carried=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.description` | rule | правило без строки карты: Call.description |  | 0 | 0 | 0 | 0 |  |
| PBXManager | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.modifiedby` | rule | правило без строки карты: Call.modifiedBy |  | 1116 | 907 | 0 | 0 | linked=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Call.modifiedAt | 1116 | 907 | 0 | 0 | carried=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Call.createdBy | 1116 | 907 | 0 | 0 | linked=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Call.assignedUser / teams | 1116 | 907 | 0 | 0 | linked=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.billduration` | rule | перенос | Call.cBillDuration | 1116 | 907 | 0 | 0 | carried=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.callstatus` | rule | перенос | Call.status + cCallStatusRaw | 1116 | 907 | 0 | 0 | mapped=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.customer` | rule | перенос | Call.parent | 36 | 13 | 0 | 0 | dangling:deleted=23, linked=13 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.customernumber` | rule | перенос | Call.cPhoneNumber | 1116 | 907 | 0 | 0 | carried=640, normalized=267, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.customertype` | excluded | исключено: производное от parent |  | 36 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.direction` | rule | перенос | Call.direction | 1116 | 907 | 0 | 0 | mapped=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.endtime` | rule | перенос | Call.dateEnd | 1113 | 907 | 0 | 0 | carried=907, not_applicable:internal_call=206 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.gateway` | excluded | исключено: исключено: константа 'PBXManager' |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.incominglinename` | rule | перенос | Call.cIncomingLine | 921 | 725 | 0 | 0 | carried=725, not_applicable:internal_call=196 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.pbxmanagerid` | key | перенос |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.recordingurl` | rule | перенос | Call.cLegacyRecordingUrl | 1033 | 902 | 0 | 0 | carried=902, not_applicable:internal_call=131 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.sourceuuid` | rule | перенос | Call.cConnectorCallId | 1116 | 907 | 0 | 0 | carried=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.sp_call_status_code` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.sp_called_from_number` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.sp_called_to_number` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.sp_is_local_cached` | excluded | исключено: исключено: служебный флаг |  | 1116 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.sp_is_recorded` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.sp_recorded_call_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.sp_recordingurl` | empty | пусто — данных нет | Call.vtigerData.sp_recordingurl | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.sp_voip_provider` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.starttime` | rule | перенос | Call.dateStart | 1116 | 907 | 0 | 0 | carried=907, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| PBXManager | vtiger7 | `vtiger_pbxmanager.totalduration` | rule | перенос | Call.duration | 1116 | 907 | 0 | 0 | archived=462, derived_equal=445, not_applicable:internal_call=209 |
| PBXManager | vtiger7 | `vtiger_pbxmanager.user` | rule | перенос | Call.assignedUser | 1116 | 907 | 0 | 0 | duplicate=907, not_applicable:internal_call=209 |
| Potentials | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Opportunity.createdAt | 156 | 156 | 0 | 0 | carried=156 |
| Potentials | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Opportunity.description | 58 | 58 | 0 | 0 | carried=58 |
| Potentials | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Opportunity.modifiedBy | 156 | 156 | 0 | 0 | linked=156 |
| Potentials | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Opportunity.modifiedAt | 156 | 156 | 0 | 0 | carried=156 |
| Potentials | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Opportunity.createdBy | 156 | 156 | 0 | 0 | linked=156 |
| Potentials | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Opportunity.assignedUser / teams | 156 | 156 | 0 | 0 | linked=156 |
| Potentials | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.amount` | rule | перенос | Opportunity.amount | 156 | 156 | 0 | 0 | carried=156 |
| Potentials | vtiger7 | `vtiger_potential.campaignid` | empty | пусто — данных нет | Opportunity.campaign | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.closingdate` | rule | перенос | Opportunity.closeDate | 156 | 156 | 0 | 0 | carried=156 |
| Potentials | vtiger7 | `vtiger_potential.contact_id` | rule | перенос | Opportunity.contacts (primary) | 156 | 47 | 0 | 0 | linked=47, zero_empty=109 |
| Potentials | vtiger7 | `vtiger_potential.converted` | rule | архив (только чтение) |  | 156 | 156 | 0 | 0 | archived=156 |
| Potentials | vtiger7 | `vtiger_potential.currency` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.description` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.evaluationstatus` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.followupdate` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.forecast_amount` | excluded | исключено: исключено: вычисляется workflow (amount×probability) — пересчитывается |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.forecastcategory` | excluded | исключено: служебное (0) |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.isconvertedfromlead` | rule | архив (только чтение) | Opportunity.vtigerData.isconvertedfromlead | 156 | 156 | 0 | 0 | archived=156 |
| Potentials | vtiger7 | `vtiger_potential.leadsource` | rule | перенос | Opportunity.leadSource | 77 | 77 | 0 | 0 | carried=2, mapped=75 |
| Potentials | vtiger7 | `vtiger_potential.nextstep` | rule | архив (только чтение) | Opportunity.vtigerData.nextstep | 4 | 4 | 0 | 0 | archived=4 |
| Potentials | vtiger7 | `vtiger_potential.outcomeanalysis` | excluded | исключено: служебное (0) |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.partnercontact` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.potential_no` | rule | перенос | Opportunity.vtigerNo | 156 | 156 | 0 | 0 | carried=156 |
| Potentials | vtiger7 | `vtiger_potential.potentialid` | key | перенос |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.potentialname` | rule | перенос | Opportunity.name | 156 | 156 | 0 | 0 | carried=156 |
| Potentials | vtiger7 | `vtiger_potential.potentialtype` | rule | перенос | Opportunity.cOpportunityType | 59 | 59 | 0 | 0 | carried=59 |
| Potentials | vtiger7 | `vtiger_potential.private` | excluded | исключено: служебное (0) |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.probability` | rule | перенос | Opportunity.probability | 156 | 156 | 0 | 0 | carried=156 |
| Potentials | vtiger7 | `vtiger_potential.productid` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.productversion` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.quotationref` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.related_to` | rule | перенос | Opportunity.account | 156 | 146 | 0 | 0 | linked=146, zero_empty=10 |
| Potentials | vtiger7 | `vtiger_potential.remarks` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.runtimefee` | excluded | исключено: служебное (0) |  | 156 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.sales_stage` | rule | перенос | Opportunity.stage | 156 | 156 | 0 | 0 | carried=134, mapped=22 |
| Potentials | vtiger7 | `vtiger_potential.spcompany` | rule | архив (только чтение) | Opportunity.vtigerData.spcompany | 153 | 153 | 0 | 0 | archived=153 |
| Potentials | vtiger7 | `vtiger_potential.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Potentials | vtiger7 | `vtiger_potential.typeofrevenue` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Product (собственная).createdAt | 3 | 3 | 0 | 0 | carried=3 |
| Products | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.description` | rule | пусто — данных нет | Product (собственная).description | 0 | 0 | 0 | 0 |  |
| Products | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Product (собственная).modifiedBy | 3 | 3 | 0 | 0 | linked=3 |
| Products | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Product (собственная).modifiedAt | 3 | 3 | 0 | 0 | carried=3 |
| Products | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Product (собственная).createdBy | 3 | 3 | 0 | 0 | linked=3 |
| Products | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Product (собственная).assignedUser / teams | 3 | 3 | 0 | 0 | linked=3 |
| Products | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_productcf.productid` | excluded | только ключ записи; кастомных колонок с данными нет |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.commissionmethod` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.commissionrate` | rule | пусто — данных нет | Product (собственная).vtigerData.commissionrate | 3 | 0 | 0 | 0 | zero_empty=3 |
| Products | vtiger7 | `vtiger_products.cost_factor` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.currency_id` | excluded | исключено: одна валюта |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.customs_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.discontinued` | rule | перенос | Product (собственная).isActive | 3 | 3 | 0 | 0 | mapped=3 |
| Products | vtiger7 | `vtiger_products.expiry_date` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.glacct` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.imagename` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.is_subproducts_viewable` | excluded | исключено: служебное |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.manuf_country` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.manuf_country_code` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.manufacturer` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.mfr_part_no` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.one_s_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.pack_size` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.product_no` | rule | перенос | Product (собственная).vtigerNo | 3 | 3 | 0 | 0 | carried=3 |
| Products | vtiger7 | `vtiger_products.productcategory` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.productcode` | rule | перенос | Product (собственная).code | 3 | 3 | 0 | 0 | carried=3 |
| Products | vtiger7 | `vtiger_products.productid` | key | перенос |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.productname` | rule | перенос | Product (собственная).name | 3 | 3 | 0 | 0 | carried=3 |
| Products | vtiger7 | `vtiger_products.productsheet` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.purchase_cost` | empty | пусто — данных нет | Product (собственная).purchaseCost | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.qty_per_unit` | rule | пусто — данных нет | Product (собственная).vtigerData.qty_per_unit | 3 | 0 | 0 | 0 | zero_empty=3 |
| Products | vtiger7 | `vtiger_products.qtyindemand` | empty | пусто — данных нет |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.qtyinstock` | rule | архив (только чтение) | Product (собственная).vtigerData.qtyinstock | 3 | 1 | 0 | 0 | archived=1, zero_empty=2 |
| Products | vtiger7 | `vtiger_products.reorderlevel` | empty | пусто — данных нет |  | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.sales_end_date` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.sales_start_date` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.serialno` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.sp_product_international_code` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.start_date` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.taxclass` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.unit_code` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.unit_price` | rule | перенос | Product (собственная).unitPrice | 3 | 3 | 0 | 0 | carried=3 |
| Products | vtiger7 | `vtiger_products.usageunit` | rule | перенос | Product (собственная).unit | 3 | 3 | 0 | 0 | carried=3 |
| Products | vtiger7 | `vtiger_products.vendor_id` | empty | пусто — данных нет | Product (собственная).vendor | 3 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.vendor_part_no` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.website` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Products | vtiger7 | `vtiger_products.weight` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Project (собственная).createdAt | 54 | 54 | 0 | 0 | carried=54 |
| Project | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 54 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 54 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Project (собственная).description | 29 | 29 | 0 | 0 | carried=29 |
| Project | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 54 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Project (собственная).modifiedBy | 54 | 54 | 0 | 0 | linked=54 |
| Project | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Project (собственная).modifiedAt | 54 | 54 | 0 | 0 | carried=54 |
| Project | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 54 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 54 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Project (собственная).createdBy | 54 | 54 | 0 | 0 | linked=54 |
| Project | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 54 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Project (собственная).assignedUser / teams | 54 | 54 | 0 | 0 | linked=54 |
| Project | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 54 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 54 |  |  |  |  |
| Project | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Project | vtiger7 | `vtiger_project.actualenddate` | rule | перенос | Project (собственная).dateEnd | 33 | 33 | 0 | 0 | carried=33 |
| Project | vtiger7 | `vtiger_project.isconvertedfrompotential` | rule | архив (только чтение) | Project (собственная).vtigerData.isconvertedfrompotential | 54 | 54 | 0 | 0 | archived=54 |
| Project | vtiger7 | `vtiger_project.linktoaccountscontacts` | rule | перенос | Project (собственная).account | 53 | 53 | 0 | 0 | linked=53 |
| Project | vtiger7 | `vtiger_project.potentialid` | rule | перенос | Project (собственная).opportunity | 54 | 36 | 0 | 0 | linked=36, zero_empty=18 |
| Project | vtiger7 | `vtiger_project.progress` | rule | перенос | Project (собственная).progress | 47 | 47 | 0 | 0 | carried=47 |
| Project | vtiger7 | `vtiger_project.project_no` | rule | перенос | Project (собственная).vtigerNo | 54 | 54 | 0 | 0 | carried=54 |
| Project | vtiger7 | `vtiger_project.projectid` | key | перенос |  | 54 |  |  |  |  |
| Project | vtiger7 | `vtiger_project.projectname` | rule | перенос | Project (собственная).name | 54 | 54 | 0 | 0 | carried=54 |
| Project | vtiger7 | `vtiger_project.projectpriority` | rule | перенос | Project (собственная).priority | 47 | 47 | 0 | 0 | carried=47 |
| Project | vtiger7 | `vtiger_project.projectstatus` | rule | перенос | Project (собственная).status | 50 | 50 | 0 | 0 | carried=50 |
| Project | vtiger7 | `vtiger_project.projecttype` | rule | перенос | Project (собственная).type | 45 | 45 | 0 | 0 | carried=45 |
| Project | vtiger7 | `vtiger_project.projecturl` | rule | перенос | Project (собственная).url | 2 | 2 | 0 | 0 | carried=2 |
| Project | vtiger7 | `vtiger_project.startdate` | rule | перенос | Project (собственная).dateStart | 54 | 54 | 0 | 0 | carried=54 |
| Project | vtiger7 | `vtiger_project.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Project | vtiger7 | `vtiger_project.targetbudget` | rule | перенос | Project (собственная).budget | 51 | 51 | 0 | 0 | archived=1, normalized=50 |
| Project | vtiger7 | `vtiger_project.targetenddate` | rule | перенос | Project (собственная).dateEndPlanned | 49 | 49 | 0 | 0 | carried=49 |
| ProjectTask | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | ProjectTask (собственная).createdAt | 493 | 493 | 0 | 0 | carried=493 |
| ProjectTask | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 493 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 493 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.description` | rule | перенос | ProjectTask (собственная).description | 308 | 308 | 0 | 0 | carried=308 |
| ProjectTask | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 493 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | ProjectTask (собственная).modifiedBy | 493 | 493 | 0 | 0 | linked=493 |
| ProjectTask | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | ProjectTask (собственная).modifiedAt | 493 | 493 | 0 | 0 | carried=493 |
| ProjectTask | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 493 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 493 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | ProjectTask (собственная).createdBy | 493 | 493 | 0 | 0 | linked=493 |
| ProjectTask | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 493 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | ProjectTask (собственная).assignedUser / teams | 493 | 493 | 0 | 0 | linked=493 |
| ProjectTask | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 493 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 493 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_projecttask.enddate` | rule | перенос | ProjectTask (собственная).dateEnd | 468 | 468 | 0 | 0 | carried=468 |
| ProjectTask | vtiger7 | `vtiger_projecttask.projectid` | rule | перенос | ProjectTask (собственная).project | 493 | 493 | 0 | 0 | linked=493 |
| ProjectTask | vtiger7 | `vtiger_projecttask.projecttask_no` | rule | перенос | ProjectTask (собственная).vtigerNo | 493 | 493 | 0 | 0 | carried=493 |
| ProjectTask | vtiger7 | `vtiger_projecttask.projecttaskhours` | rule | перенос | ProjectTask (собственная).hours | 493 | 493 | 0 | 0 | carried=493 |
| ProjectTask | vtiger7 | `vtiger_projecttask.projecttaskid` | key | перенос |  | 493 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_projecttask.projecttaskname` | rule | перенос | ProjectTask (собственная).name | 493 | 493 | 0 | 0 | carried=493 |
| ProjectTask | vtiger7 | `vtiger_projecttask.projecttasknumber` | rule | перенос | ProjectTask (собственная).orderNumber | 493 | 493 | 0 | 0 | carried=493 |
| ProjectTask | vtiger7 | `vtiger_projecttask.projecttaskpriority` | rule | перенос | ProjectTask (собственная).priority | 480 | 480 | 0 | 0 | carried=480 |
| ProjectTask | vtiger7 | `vtiger_projecttask.projecttaskprogress` | rule | перенос | ProjectTask (собственная).progress | 488 | 488 | 0 | 0 | carried=488 |
| ProjectTask | vtiger7 | `vtiger_projecttask.projecttaskstatus` | rule | перенос | ProjectTask (собственная).status | 492 | 492 | 0 | 0 | carried=492 |
| ProjectTask | vtiger7 | `vtiger_projecttask.projecttasktype` | rule | перенос | ProjectTask (собственная).type | 489 | 489 | 0 | 0 | carried=489 |
| ProjectTask | vtiger7 | `vtiger_projecttask.startdate` | rule | перенос | ProjectTask (собственная).dateStart | 490 | 490 | 0 | 0 | carried=490 |
| ProjectTask | vtiger7 | `vtiger_projecttask.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| ProjectTask | vtiger7 | `vtiger_projecttaskcf.cf_1320` | rule | перенос | ProjectTask (собственная).gitCommit | 257 | 257 | 0 | 0 | carried=257 |
| ProjectTask | vtiger7 | `vtiger_projecttaskcf.cf_1354` | rule | перенос | ProjectTask (собственная).showInStat | 493 | 493 | 0 | 0 | carried=493 |
| ProjectTask | vtiger7 | `vtiger_projecttaskcf.projecttaskid` | key | перенос |  | 493 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Quote (собственная).createdAt | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.description` | rule | пусто — данных нет | Quote (собственная).description | 0 | 0 | 0 | 0 |  |
| Quotes | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Quote (собственная).modifiedBy | 24 | 24 | 0 | 0 | linked=24 |
| Quotes | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Quote (собственная).modifiedAt | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Quote (собственная).createdBy | 24 | 24 | 0 | 0 | linked=24 |
| Quotes | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Quote (собственная).assignedUser / teams | 24 | 24 | 0 | 0 | linked=24 |
| Quotes | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.comment` | rule | перенос | Quote (собственная).QuoteItem.description | 22 | 22 | 0 | 0 | carried=22 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.description` | excluded | исключено: пусто |  | 0 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.discount_amount` | rule | пусто — данных нет | Quote (собственная).QuoteItem.discountAmount | 26 | 26 | 0 | 0 | carried=26 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.discount_percent` | rule | пусто — данных нет | Quote (собственная).QuoteItem.discountPercent | 26 | 26 | 0 | 0 | carried=26 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.id` | rule | перенос |  | 27 | 27 | 0 | 0 | linked=27 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.image` | excluded | исключено: исключено: пустое служебное поле |  | 0 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.incrementondel` | excluded | исключено: исключено: складской флаг Vtiger |  | 27 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.lineitem_id` | key | перенос |  | 27 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.listprice` | rule | перенос | Quote (собственная).QuoteItem.unitPrice | 27 | 27 | 0 | 0 | carried=27 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.margin` | rule | перенос | Quote (собственная).QuoteItem.margin | 27 | 27 | 0 | 0 | carried=27 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.productid` | rule | перенос | Quote (собственная).QuoteItem.product | 27 | 27 | 0 | 0 | linked=27 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.purchase_cost` | rule | пусто — данных нет | Quote (собственная).QuoteItem.purchaseCost | 27 | 27 | 0 | 0 | carried=27 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.quantity` | rule | перенос | Quote (собственная).QuoteItem.quantity | 27 | 27 | 0 | 0 | carried=27 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.sequence_no` | rule | перенос |  | 27 | 27 | 0 | 0 | carried=27 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.tax1` | rule | перенос | Quote (собственная).QuoteItem.taxRate | 26 | 26 | 0 | 0 | carried=26 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.tax2` | rule | пусто — данных нет | Quote (собственная).QuoteItem.vtigerData.tax2 | 26 | 0 | 0 | 0 | zero_empty=26 |
| Quotes | vtiger7 | `vtiger_inventoryproductrel.tax3` | rule | пусто — данных нет | Quote (собственная).QuoteItem.vtigerData.tax3 | 26 | 0 | 0 | 0 | zero_empty=26 |
| Quotes | vtiger7 | `vtiger_quotes.accountid` | rule | перенос | Quote (собственная).account | 24 | 24 | 0 | 0 | linked=24 |
| Quotes | vtiger7 | `vtiger_quotes.adjustment` | rule | пусто — данных нет | Quote (собственная).adjustment | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.carrier` | rule | пусто — данных нет | Quote (собственная).vtigerData.carrier | 0 | 0 | 0 | 0 |  |
| Quotes | vtiger7 | `vtiger_quotes.compound_taxes_info` | rule | архив (только чтение) |  | 24 | 24 | 0 | 0 | archived=24 |
| Quotes | vtiger7 | `vtiger_quotes.contactid` | rule | перенос | Quote (собственная).contact | 6 | 6 | 0 | 0 | linked=6 |
| Quotes | vtiger7 | `vtiger_quotes.conversion_rate` | excluded | исключено: исключено: всегда 1.000 (одна валюта) |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_quotes.currency_id` | rule | перенос | Quote (собственная).currency | 24 | 24 | 0 | 0 | mapped=24 |
| Quotes | vtiger7 | `vtiger_quotes.discount_amount` | rule | пусто — данных нет | Quote (собственная).discountAmount | 0 | 0 | 0 | 0 |  |
| Quotes | vtiger7 | `vtiger_quotes.discount_percent` | rule | пусто — данных нет | Quote (собственная).discountPercent | 0 | 0 | 0 | 0 |  |
| Quotes | vtiger7 | `vtiger_quotes.inventorymanager` | rule | перенос | Quote (собственная).inventoryManager | 24 | 23 | 0 | 0 | linked=23, zero_empty=1 |
| Quotes | vtiger7 | `vtiger_quotes.potentialid` | rule | перенос | Quote (собственная).opportunity | 24 | 24 | 0 | 0 | linked=24 |
| Quotes | vtiger7 | `vtiger_quotes.pre_tax_total` | rule | перенос | Quote (собственная).preTaxTotal | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.quote_no` | rule | перенос | Quote (собственная).number | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.quoteid` | key | перенос |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_quotes.quotestage` | rule | перенос | Quote (собственная).status | 24 | 24 | 0 | 0 | carried=1, mapped=23 |
| Quotes | vtiger7 | `vtiger_quotes.region_id` | rule | перенос (значимы NULL и 0) | Quote (собственная).sourceFormula + vtigerData.region_id | 1 | 1 | 0 | 0 | archived=1 |
| Quotes | vtiger7 | `vtiger_quotes.s_h_amount` | rule | пусто — данных нет | Quote (собственная).shippingAmount | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.s_h_percent` | rule | пусто — данных нет | Quote (собственная).shippingTaxPercent | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.shipping` | rule | пусто — данных нет | Quote (собственная).vtigerData.shipping | 0 | 0 | 0 | 0 |  |
| Quotes | vtiger7 | `vtiger_quotes.spcompany` | rule | перенос | Quote (собственная).legalEntity + vtigerData.spcompany | 24 | 24 | 0 | 0 | archived=24 |
| Quotes | vtiger7 | `vtiger_quotes.subject` | rule | перенос | Quote (собственная).name | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.subtotal` | rule | перенос | Quote (собственная).subtotal | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_quotes.taxtype` | rule | перенос | Quote (собственная).taxMode | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.terms_conditions` | rule | перенос | Quote (собственная).termsAndConditions | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.total` | rule | перенос | Quote (собственная).grandTotal | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotes.type` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_quotes.validtill` | rule | перенос | Quote (собственная).dateValidUntil | 15 | 15 | 0 | 0 | carried=15 |
| Quotes | vtiger7 | `vtiger_quotesbillads.bill_city` | rule | перенос | Quote (собственная).billingAddressCity | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotesbillads.bill_code` | rule | перенос | Quote (собственная).billingAddressPostalCode | 21 | 21 | 0 | 0 | carried=21 |
| Quotes | vtiger7 | `vtiger_quotesbillads.bill_country` | rule | перенос | Quote (собственная).billingAddressCountry | 20 | 20 | 0 | 0 | carried=20 |
| Quotes | vtiger7 | `vtiger_quotesbillads.bill_pobox` | rule | пусто — данных нет | Quote (собственная).vtigerData.bill_pobox | 0 | 0 | 0 | 0 |  |
| Quotes | vtiger7 | `vtiger_quotesbillads.bill_state` | rule | перенос | Quote (собственная).billingAddressState | 19 | 19 | 0 | 0 | carried=19 |
| Quotes | vtiger7 | `vtiger_quotesbillads.bill_street` | rule | перенос | Quote (собственная).billingAddressStreet | 24 | 24 | 0 | 0 | carried=24 |
| Quotes | vtiger7 | `vtiger_quotesbillads.quotebilladdressid` | key | перенос |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_quotescf.quoteid` | key | перенос |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_quotescf.tax` | rule | пусто — данных нет | Quote (собственная).vtigerData.tax | 0 | 0 | 0 | 0 |  |
| Quotes | vtiger7 | `vtiger_quotesshipads.quoteshipaddressid` | key | перенос |  | 24 |  |  |  |  |
| Quotes | vtiger7 | `vtiger_quotesshipads.ship_city` | rule | перенос | Quote (собственная).shippingAddressCity | 23 | 23 | 0 | 0 | carried=23 |
| Quotes | vtiger7 | `vtiger_quotesshipads.ship_code` | rule | перенос | Quote (собственная).shippingAddressPostalCode | 21 | 21 | 0 | 0 | carried=21 |
| Quotes | vtiger7 | `vtiger_quotesshipads.ship_country` | rule | перенос | Quote (собственная).shippingAddressCountry | 20 | 20 | 0 | 0 | carried=20 |
| Quotes | vtiger7 | `vtiger_quotesshipads.ship_pobox` | rule | пусто — данных нет | Quote (собственная).vtigerData.ship_pobox | 0 | 0 | 0 | 0 |  |
| Quotes | vtiger7 | `vtiger_quotesshipads.ship_state` | rule | перенос | Quote (собственная).shippingAddressState | 18 | 18 | 0 | 0 | carried=18 |
| Quotes | vtiger7 | `vtiger_quotesshipads.ship_street` | rule | перенос | Quote (собственная).shippingAddressStreet | 24 | 24 | 0 | 0 | carried=24 |
| SPCallPopup | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Call (слияние с PBXManager).createdAt | 210 | 204 | 0 | 0 | archived=204, not_applicable:internal_call=6 |
| SPCallPopup | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.description` | rule | правило без строки карты: Call.vtigerData.popup_description |  | 0 | 0 | 0 | 0 |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Call (слияние с PBXManager).modifiedBy | 210 | 204 | 0 | 0 | duplicate=204, not_applicable:internal_call=6 |
| SPCallPopup | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Call (слияние с PBXManager).modifiedAt | 210 | 204 | 0 | 0 | archived=10, duplicate=194, not_applicable:internal_call=6 |
| SPCallPopup | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Call (слияние с PBXManager).createdBy | 210 | 204 | 0 | 0 | duplicate=204, not_applicable:internal_call=6 |
| SPCallPopup | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Call (слияние с PBXManager).assignedUser / teams | 210 | 204 | 0 | 0 | duplicate=204, not_applicable:internal_call=6 |
| SPCallPopup | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.accountname` | rule | пусто — данных нет | Call (слияние с PBXManager).Call.vtigerData.popup_accountname | 0 | 0 | 0 | 0 |  |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.call_no` | rule | пусто — данных нет | Call (слияние с PBXManager).Call.vtigerData.popup_call_no | 0 | 0 | 0 | 0 |  |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.callid` | rule | перенос | Call (слияние с PBXManager).(ключ слияния с Call) | 210 | 204 | 0 | 0 | linked=204, not_applicable:internal_call=6 |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.client_type` | rule | архив (только чтение) | Call (слияние с PBXManager).Call.vtigerData.popup_client_type | 3 | 3 | 0 | 0 | archived=3 |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.comment` | rule | перенос | Call (слияние с PBXManager).Call.description (дополнение) | 2 | 2 | 0 | 0 | carried=2 |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.firstname` | rule | архив (только чтение) | Call (слияние с PBXManager).Call.vtigerData.popup_firstname | 3 | 3 | 0 | 0 | archived=3 |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.lastname` | rule | архив (только чтение) | Call (слияние с PBXManager).Call.vtigerData.popup_lastname | 3 | 3 | 0 | 0 | archived=3 |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.popupid` | key | перенос |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.status` | excluded | исключено: исключено: служебный статус попапа |  | 210 |  |  |  |  |
| SPCallPopup | vtiger7 | `vtiger_sp_callpopup.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| SPPayments | vtiger7 | `sp_payments.amount` | rule | перенос | Payment + PaymentAllocation (собственные).amount | 799 | 799 | 0 | 0 | carried=799 |
| SPPayments | vtiger7 | `sp_payments.analytics_code` | rule | архив (только чтение) | Payment + PaymentAllocation (собственные).vtigerData.analytics_code | 1 | 1 | 0 | 0 | archived=1 |
| SPPayments | vtiger7 | `sp_payments.coracc_subacc` | rule | пусто — данных нет | Payment + PaymentAllocation (собственные).vtigerData.coracc_subacc | 0 | 0 | 0 | 0 |  |
| SPPayments | vtiger7 | `sp_payments.debit` | rule | пусто — данных нет | Payment + PaymentAllocation (собственные).vtigerData.debit | 0 | 0 | 0 | 0 |  |
| SPPayments | vtiger7 | `sp_payments.doc_no` | rule | перенос | Payment + PaymentAllocation (собственные).documentNumber | 799 | 657 | 0 | 0 | carried=657, zero_empty=142 |
| SPPayments | vtiger7 | `sp_payments.pay_date` | rule | перенос | Payment + PaymentAllocation (собственные).datePaid | 799 | 799 | 0 | 0 | carried=799 |
| SPPayments | vtiger7 | `sp_payments.pay_details` | rule | перенос | Payment + PaymentAllocation (собственные).purpose | 663 | 663 | 0 | 0 | carried=663 |
| SPPayments | vtiger7 | `sp_payments.pay_no` | rule | перенос | Payment + PaymentAllocation (собственные).number | 799 | 799 | 0 | 0 | carried=799 |
| SPPayments | vtiger7 | `sp_payments.pay_type` | rule | перенос | Payment + PaymentAllocation (собственные).direction | 799 | 799 | 0 | 0 | mapped=799 |
| SPPayments | vtiger7 | `sp_payments.payer` | rule | перенос | Payment + PaymentAllocation (собственные).payer (Account\|Contact\|Vendor) | 799 | 756 | 0 | 0 | linked=756, zero_empty=43 |
| SPPayments | vtiger7 | `sp_payments.payid` | key | перенос |  | 799 |  |  |  |  |
| SPPayments | vtiger7 | `sp_payments.related_to` | rule | перенос | Payment + PaymentAllocation (собственные).PaymentAllocation.invoice\|salesOrder | 799 | 623 | 0 | 0 | linked=623, zero_empty=176 |
| SPPayments | vtiger7 | `sp_payments.spcompany` | rule | перенос | Payment + PaymentAllocation (собственные).legalEntity + vtigerData.spcompany | 611 | 611 | 0 | 0 | archived=611 |
| SPPayments | vtiger7 | `sp_payments.spstatus` | rule | перенос | Payment + PaymentAllocation (собственные).status | 781 | 781 | 0 | 0 | carried=781 |
| SPPayments | vtiger7 | `sp_payments.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| SPPayments | vtiger7 | `sp_payments.target_code` | rule | пусто — данных нет | Payment + PaymentAllocation (собственные).vtigerData.target_code | 0 | 0 | 0 | 0 |  |
| SPPayments | vtiger7 | `sp_payments.type_payment` | rule | перенос | Payment + PaymentAllocation (собственные).method | 797 | 797 | 0 | 0 | mapped=797 |
| SPPayments | vtiger7 | `sp_paymentscf.cf_1198` | rule | перенос | Payment + PaymentAllocation (собственные).counterpartyAccount | 603 | 603 | 0 | 0 | carried=603 |
| SPPayments | vtiger7 | `sp_paymentscf.cf_1200` | rule | перенос | Payment + PaymentAllocation (собственные).counterpartyBic | 190 | 190 | 0 | 0 | carried=190 |
| SPPayments | vtiger7 | `sp_paymentscf.cf_1202` | rule | перенос | Payment + PaymentAllocation (собственные).counterpartyBankName | 208 | 208 | 0 | 0 | carried=208 |
| SPPayments | vtiger7 | `sp_paymentscf.cf_1204` | rule | перенос | Payment + PaymentAllocation (собственные).bankTransactionId | 188 | 188 | 0 | 0 | carried=188 |
| SPPayments | vtiger7 | `sp_paymentscf.cf_1380` | rule | перенос | Payment + PaymentAllocation (собственные).isForeignCurrencyAccount | 799 | 799 | 0 | 0 | carried=799 |
| SPPayments | vtiger7 | `sp_paymentscf.payid` | key | перенос |  | 799 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Payment + PaymentAllocation (собственные).createdAt | 799 | 799 | 0 | 0 | carried=799 |
| SPPayments | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 799 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 799 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Payment + PaymentAllocation (собственные).description | 41 | 41 | 0 | 0 | carried=41 |
| SPPayments | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 611 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Payment + PaymentAllocation (собственные).modifiedBy | 799 | 799 | 0 | 0 | linked=799 |
| SPPayments | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Payment + PaymentAllocation (собственные).modifiedAt | 799 | 799 | 0 | 0 | carried=799 |
| SPPayments | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 799 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 799 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Payment + PaymentAllocation (собственные).createdBy | 799 | 799 | 0 | 0 | linked=799 |
| SPPayments | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 799 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Payment + PaymentAllocation (собственные).assignedUser / teams | 799 | 799 | 0 | 0 | linked=799 |
| SPPayments | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 799 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 799 |  |  |  |  |
| SPPayments | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | SalesOrder (собственная).createdAt | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.description` | rule | пусто — данных нет | SalesOrder (собственная).description | 0 | 0 | 0 | 0 |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | SalesOrder (собственная).modifiedBy | 14 | 14 | 0 | 0 | linked=14 |
| SalesOrder | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | SalesOrder (собственная).modifiedAt | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | SalesOrder (собственная).createdBy | 14 | 14 | 0 | 0 | linked=14 |
| SalesOrder | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | SalesOrder (собственная).assignedUser / teams | 14 | 14 | 0 | 0 | linked=14 |
| SalesOrder | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.comment` | rule | перенос | SalesOrder (собственная).SalesOrderItem.description | 12 | 12 | 0 | 0 | carried=12 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.description` | excluded | исключено: пусто |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.discount_amount` | rule | пусто — данных нет | SalesOrder (собственная).SalesOrderItem.discountAmount | 13 | 13 | 0 | 0 | carried=13 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.discount_percent` | rule | пусто — данных нет | SalesOrder (собственная).SalesOrderItem.discountPercent | 13 | 13 | 0 | 0 | carried=13 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.id` | rule | перенос |  | 14 | 14 | 0 | 0 | linked=14 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.image` | excluded | исключено: исключено: пустое служебное поле |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.incrementondel` | excluded | исключено: исключено: складской флаг Vtiger |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.lineitem_id` | key | перенос |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.listprice` | rule | перенос | SalesOrder (собственная).SalesOrderItem.unitPrice | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.margin` | rule | перенос | SalesOrder (собственная).SalesOrderItem.margin | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.productid` | rule | перенос | SalesOrder (собственная).SalesOrderItem.product | 14 | 14 | 0 | 0 | linked=14 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.purchase_cost` | rule | пусто — данных нет | SalesOrder (собственная).SalesOrderItem.purchaseCost | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.quantity` | rule | перенос | SalesOrder (собственная).SalesOrderItem.quantity | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.sequence_no` | rule | перенос |  | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.tax1` | rule | перенос | SalesOrder (собственная).SalesOrderItem.taxRate | 13 | 13 | 0 | 0 | carried=13 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.tax2` | rule | пусто — данных нет | SalesOrder (собственная).SalesOrderItem.vtigerData.tax2 | 13 | 0 | 0 | 0 | zero_empty=13 |
| SalesOrder | vtiger7 | `vtiger_inventoryproductrel.tax3` | rule | пусто — данных нет | SalesOrder (собственная).SalesOrderItem.vtigerData.tax3 | 13 | 0 | 0 | 0 | zero_empty=13 |
| SalesOrder | vtiger7 | `vtiger_invoice_recurring_info.end_period` | rule | архив (только чтение) | SalesOrder (собственная).vtigerData.end_period | 3 | 3 | 0 | 0 | archived=3 |
| SalesOrder | vtiger7 | `vtiger_invoice_recurring_info.invoice_status` | rule | архив (только чтение) | SalesOrder (собственная).vtigerData.recurring_invoice_status | 13 | 13 | 0 | 0 | archived=13 |
| SalesOrder | vtiger7 | `vtiger_invoice_recurring_info.last_recurring_date` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_invoice_recurring_info.payment_duration` | rule | архив (только чтение) | SalesOrder (собственная).vtigerData.payment_duration | 3 | 3 | 0 | 0 | archived=3 |
| SalesOrder | vtiger7 | `vtiger_invoice_recurring_info.recurring_frequency` | rule | архив (только чтение) | SalesOrder (собственная).vtigerData.recurring_frequency | 3 | 3 | 0 | 0 | archived=3 |
| SalesOrder | vtiger7 | `vtiger_invoice_recurring_info.salesorderid` | key | перенос |  | 13 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_invoice_recurring_info.start_period` | rule | архив (только чтение) | SalesOrder (собственная).vtigerData.start_period | 3 | 3 | 0 | 0 | archived=3 |
| SalesOrder | vtiger7 | `vtiger_salesorder.accountid` | rule | перенос | SalesOrder (собственная).account | 14 | 14 | 0 | 0 | linked=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.adjustment` | rule | пусто — данных нет | SalesOrder (собственная).adjustment | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.carrier` | rule | архив (только чтение) | SalesOrder (собственная).vtigerData.carrier | 1 | 1 | 0 | 0 | archived=1 |
| SalesOrder | vtiger7 | `vtiger_salesorder.compound_taxes_info` | rule | архив (только чтение) |  | 14 | 14 | 0 | 0 | archived=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.contactid` | rule | перенос | SalesOrder (собственная).contact | 14 | 8 | 0 | 0 | linked=8, zero_empty=6 |
| SalesOrder | vtiger7 | `vtiger_salesorder.conversion_rate` | excluded | исключено: исключено: всегда 1.000 (одна валюта) |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.currency_id` | rule | перенос | SalesOrder (собственная).currency | 14 | 14 | 0 | 0 | mapped=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.customerno` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.discount_amount` | rule | пусто — данных нет | SalesOrder (собственная).discountAmount | 0 | 0 | 0 | 0 |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.discount_percent` | rule | пусто — данных нет | SalesOrder (собственная).discountPercent | 0 | 0 | 0 | 0 |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.duedate` | rule | перенос | SalesOrder (собственная).dateDue | 7 | 7 | 0 | 0 | carried=7 |
| SalesOrder | vtiger7 | `vtiger_salesorder.enable_recurring` | rule | архив (только чтение) | SalesOrder (собственная).vtigerData.enable_recurring | 14 | 14 | 0 | 0 | archived=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.exciseduty` | rule | пусто — данных нет | SalesOrder (собственная).vtigerData.exciseduty | 14 | 0 | 0 | 0 | zero_empty=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.fromsite` | rule | пусто — данных нет | SalesOrder (собственная).vtigerData.fromsite | 14 | 0 | 0 | 0 | zero_empty=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.one_s_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.pending` | rule | архив (только чтение) | SalesOrder (собственная).vtigerData.pending | 1 | 1 | 0 | 0 | archived=1 |
| SalesOrder | vtiger7 | `vtiger_salesorder.potentialid` | rule | перенос | SalesOrder (собственная).opportunity | 14 | 12 | 0 | 0 | linked=12, zero_empty=2 |
| SalesOrder | vtiger7 | `vtiger_salesorder.pre_tax_total` | rule | перенос | SalesOrder (собственная).preTaxTotal | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.purchaseorder` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.quoteid` | rule | пусто — данных нет | SalesOrder (собственная).quote | 14 | 0 | 0 | 0 | zero_empty=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.region_id` | rule | перенос (значимы NULL и 0) | SalesOrder (собственная).sourceFormula + vtigerData.region_id | 1 | 1 | 0 | 0 | archived=1 |
| SalesOrder | vtiger7 | `vtiger_salesorder.s_h_amount` | rule | пусто — данных нет | SalesOrder (собственная).shippingAmount | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.s_h_percent` | rule | пусто — данных нет | SalesOrder (собственная).shippingTaxPercent | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.salescommission` | rule | пусто — данных нет | SalesOrder (собственная).vtigerData.salescommission | 14 | 0 | 0 | 0 | zero_empty=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.salesorder_no` | rule | перенос | SalesOrder (собственная).number | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.salesorderid` | key | перенос |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.sostatus` | rule | перенос | SalesOrder (собственная).status | 14 | 14 | 0 | 0 | carried=1, mapped=13 |
| SalesOrder | vtiger7 | `vtiger_salesorder.spcompany` | rule | перенос | SalesOrder (собственная).legalEntity + vtigerData.spcompany | 14 | 14 | 0 | 0 | archived=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.subject` | rule | перенос | SalesOrder (собственная).name | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.subtotal` | rule | перенос | SalesOrder (собственная).subtotal | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.taxtype` | rule | перенос | SalesOrder (собственная).taxMode | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.terms_conditions` | rule | перенос | SalesOrder (собственная).termsAndConditions | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.total` | rule | перенос | SalesOrder (собственная).grandTotal | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_salesorder.type` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.vendorid` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesorder.vendorterms` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesordercf.salesorderid` | key | перенос |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_salesordercf.tax` | rule | пусто — данных нет | SalesOrder (собственная).vtigerData.tax | 0 | 0 | 0 | 0 |  |
| SalesOrder | vtiger7 | `vtiger_sobillads.bill_city` | rule | перенос | SalesOrder (собственная).billingAddressCity | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_sobillads.bill_code` | rule | перенос | SalesOrder (собственная).billingAddressPostalCode | 12 | 12 | 0 | 0 | carried=12 |
| SalesOrder | vtiger7 | `vtiger_sobillads.bill_country` | rule | перенос | SalesOrder (собственная).billingAddressCountry | 11 | 11 | 0 | 0 | carried=11 |
| SalesOrder | vtiger7 | `vtiger_sobillads.bill_pobox` | rule | пусто — данных нет | SalesOrder (собственная).vtigerData.bill_pobox | 0 | 0 | 0 | 0 |  |
| SalesOrder | vtiger7 | `vtiger_sobillads.bill_state` | rule | перенос | SalesOrder (собственная).billingAddressState | 10 | 10 | 0 | 0 | carried=10 |
| SalesOrder | vtiger7 | `vtiger_sobillads.bill_street` | rule | перенос | SalesOrder (собственная).billingAddressStreet | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_sobillads.sobilladdressid` | key | перенос |  | 14 |  |  |  |  |
| SalesOrder | vtiger7 | `vtiger_soshipads.ship_city` | rule | перенос | SalesOrder (собственная).shippingAddressCity | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_soshipads.ship_code` | rule | перенос | SalesOrder (собственная).shippingAddressPostalCode | 12 | 12 | 0 | 0 | carried=12 |
| SalesOrder | vtiger7 | `vtiger_soshipads.ship_country` | rule | перенос | SalesOrder (собственная).shippingAddressCountry | 11 | 11 | 0 | 0 | carried=11 |
| SalesOrder | vtiger7 | `vtiger_soshipads.ship_pobox` | rule | пусто — данных нет | SalesOrder (собственная).vtigerData.ship_pobox | 0 | 0 | 0 | 0 |  |
| SalesOrder | vtiger7 | `vtiger_soshipads.ship_state` | rule | перенос | SalesOrder (собственная).shippingAddressState | 10 | 10 | 0 | 0 | carried=10 |
| SalesOrder | vtiger7 | `vtiger_soshipads.ship_street` | rule | перенос | SalesOrder (собственная).shippingAddressStreet | 14 | 14 | 0 | 0 | carried=14 |
| SalesOrder | vtiger7 | `vtiger_soshipads.soshipaddressid` | key | перенос |  | 14 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.createdtime` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.createdtime | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 1 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 1 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.description` | unmapped |  |  | 0 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 1 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.modifiedby` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.modifiedby | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.modifiedtime | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 1 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 1 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.created_user_id | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 1 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.smownerid` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.assigned_user_id | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_crmentity.source` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.source | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 1 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.actual_duration` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.actual_duration | 0 | 0 | 0 | 0 |  |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.contract_no` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.contract_no | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.contract_status` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.contract_status | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.contract_type` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.contract_type | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.due_date` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.due_date | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.end_date` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.end_date | 0 | 0 | 0 | 0 |  |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.planned_duration` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.planned_duration | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.priority` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.contract_priority | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.progress` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.progress | 0 | 0 | 0 | 0 |  |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.sc_related_to` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.sc_related_to | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.servicecontractsid` | key | перенос |  | 1 |  |  |  |  |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.start_date` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.start_date | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.subject` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.subject | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.tags` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.tags | 0 | 0 | 0 | 0 |  |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.total_units` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.total_units | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.tracking_unit` | rule | архив (только чтение) | VtigerArchive.VtigerArchive.data.tracking_unit | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontracts.used_units` | rule | пусто — данных нет | VtigerArchive.VtigerArchive.data.used_units | 1 | 1 | 0 | 0 | archived=1 |
| ServiceContracts | vtiger7 | `vtiger_servicecontractscf.servicecontractsid` | excluded | только ключ записи; кастомных колонок с данными нет |  | 1 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Product (собственная, type=service).createdAt | 25 | 25 | 0 | 0 | carried=25 |
| Services | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.description` | rule | перенос | Product (собственная, type=service).description | 5 | 5 | 0 | 0 | carried=5 |
| Services | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Product (собственная, type=service).modifiedBy | 25 | 25 | 0 | 0 | linked=25 |
| Services | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Product (собственная, type=service).modifiedAt | 25 | 25 | 0 | 0 | carried=25 |
| Services | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Product (собственная, type=service).createdBy | 25 | 25 | 0 | 0 | linked=25 |
| Services | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Product (собственная, type=service).assignedUser / teams | 25 | 25 | 0 | 0 | linked=25 |
| Services | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Services | vtiger7 | `vtiger_service.commissionrate` | rule | архив (только чтение) | Product (собственная, type=service).vtigerData.commissionrate | 25 | 4 | 0 | 0 | archived=4, zero_empty=21 |
| Services | vtiger7 | `vtiger_service.currency_id` | excluded | исключено: одна валюта |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_service.discontinued` | rule | перенос | Product (собственная, type=service).isActive | 25 | 25 | 0 | 0 | mapped=25 |
| Services | vtiger7 | `vtiger_service.expiry_date` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Services | vtiger7 | `vtiger_service.one_s_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Services | vtiger7 | `vtiger_service.purchase_cost` | empty | пусто — данных нет | Product (собственная, type=service).purchaseCost | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_service.qty_per_unit` | rule | перенос | Product (собственная, type=service).qtyPerUnit | 25 | 25 | 0 | 0 | carried=25 |
| Services | vtiger7 | `vtiger_service.sales_end_date` | rule | архив (только чтение) | Product (собственная, type=service).vtigerData.sales_end_date | 1 | 1 | 0 | 0 | archived=1 |
| Services | vtiger7 | `vtiger_service.sales_start_date` | rule | архив (только чтение) | Product (собственная, type=service).vtigerData.sales_start_date | 11 | 11 | 0 | 0 | archived=11 |
| Services | vtiger7 | `vtiger_service.service_no` | rule | перенос | Product (собственная, type=service).vtigerNo | 25 | 25 | 0 | 0 | carried=25 |
| Services | vtiger7 | `vtiger_service.service_usageunit` | rule | перенос | Product (собственная, type=service).unit | 19 | 19 | 0 | 0 | carried=4, mapped=15 |
| Services | vtiger7 | `vtiger_service.servicecategory` | rule | перенос | Product (собственная, type=service).category | 15 | 15 | 0 | 0 | carried=4, mapped=11 |
| Services | vtiger7 | `vtiger_service.serviceid` | key | перенос |  | 25 |  |  |  |  |
| Services | vtiger7 | `vtiger_service.servicename` | rule | перенос | Product (собственная, type=service).name | 25 | 25 | 0 | 0 | carried=25 |
| Services | vtiger7 | `vtiger_service.start_date` | rule | архив (только чтение) | Product (собственная, type=service).vtigerData.start_date | 5 | 5 | 0 | 0 | archived=5 |
| Services | vtiger7 | `vtiger_service.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Services | vtiger7 | `vtiger_service.taxclass` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Services | vtiger7 | `vtiger_service.unit_code` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Services | vtiger7 | `vtiger_service.unit_price` | rule | перенос | Product (собственная, type=service).unitPrice | 25 | 25 | 0 | 0 | carried=25 |
| Services | vtiger7 | `vtiger_service.website` | rule | архив (только чтение) | Product (собственная, type=service).vtigerData.website | 3 | 3 | 0 | 0 | archived=3 |
| Services | vtiger7 | `vtiger_servicecf.cf_billable_time_tracker` | rule | перенос | Product (собственная, type=service).isBillableTime | 25 | 25 | 0 | 0 | carried=25 |
| Services | vtiger7 | `vtiger_servicecf.serviceid` | key | перенос |  | 25 |  |  |  |  |
| Users | vtiger7 | `vtiger_user2role.roleid` | rule | перенос | User.roles | 7 | 7 | 0 | 0 | mapped=7 |
| Users | vtiger7 | `vtiger_user2role.userid` | key | перенос |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.accesskey` | excluded | исключено: исключено: секрет API |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.activity_view` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.address_city` | excluded | исключено: исключено: адрес сотрудника (решение владельца, Q-09) |  | 4 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.address_country` | excluded | исключено: исключено: адрес сотрудника (решение владельца, Q-09) |  | 4 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.address_postalcode` | excluded | исключено: исключено: адрес сотрудника (решение владельца, Q-09) |  | 4 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.address_state` | excluded | исключено: исключено: адрес сотрудника (решение владельца, Q-09) |  | 4 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.address_street` | excluded | исключено: исключено: адрес сотрудника (решение владельца, Q-09) |  | 4 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.cal_color` | excluded | исключено: исключено: UI |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.calendarsharedtype` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.callduration` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.confirm_password` | excluded | исключено: исключено: секрет |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.crypt_type` | excluded | исключено: исключено: служебное |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.currency_decimal_separator` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.currency_grouping_pattern` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.currency_grouping_separator` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.currency_id` | rule | перенос | User.preferences (валюта) | 7 | 0 | 0 | 0 | not_applicable:D-37=7 |
| Users | vtiger7 | `vtiger_users.currency_symbol_placement` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.date_entered` | rule | перенос |  | 7 | 7 | 0 | 0 | carried=7 |
| Users | vtiger7 | `vtiger_users.date_format` | rule | перенос | User.preferences.dateFormat | 7 | 7 | 0 | 0 | mapped=7 |
| Users | vtiger7 | `vtiger_users.date_modified` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.dayoftheweek` | rule | перенос | User.preferences.weekStart | 7 | 7 | 0 | 0 | mapped=7 |
| Users | vtiger7 | `vtiger_users.default_record_view` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.defaultactivitytype` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 2 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.defaultcalendarview` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 2 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.defaulteventstatus` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 2 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.deleted` | excluded | исключено: служебное (все 0) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.department` | rule | архив (только чтение) | User.vtigerData.department | 1 | 1 | 0 | 0 | archived=1 |
| Users | vtiger7 | `vtiger_users.description` | empty | пусто — данных нет | User.description | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.email1` | rule | перенос | User.emailAddress | 7 | 7 | 0 | 0 | carried=7 |
| Users | vtiger7 | `vtiger_users.email2` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.end_hour` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 1 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.first_name` | rule | перенос | User.firstName | 6 | 6 | 0 | 0 | carried=6 |
| Users | vtiger7 | `vtiger_users.hidecompletedevents` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.holidays` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.hour_format` | rule | перенос | User.preferences.timeFormat | 7 | 7 | 0 | 0 | mapped=7 |
| Users | vtiger7 | `vtiger_users.id` | key | перенос |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.imagename` | rule | перенос | User.avatar | 1 | 1 | 0 | 0 | linked=1 |
| Users | vtiger7 | `vtiger_users.internal_mailer` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.is_admin` | rule | перенос | User.type | 7 | 7 | 0 | 0 | mapped=7 |
| Users | vtiger7 | `vtiger_users.is_owner` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 1 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.language` | rule | перенос | User.preferences.language | 7 | 7 | 0 | 0 | mapped=7 |
| Users | vtiger7 | `vtiger_users.last_name` | rule | перенос | User.lastName | 7 | 7 | 0 | 0 | carried=7 |
| Users | vtiger7 | `vtiger_users.lead_view` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.leftpanelhide` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.modified_user_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.namedays` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.no_of_currency_decimals` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.othereventduration` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.phone_crm_extension` | rule | перенос | User.cPhoneExtension | 5 | 5 | 0 | 0 | carried=5 |
| Users | vtiger7 | `vtiger_users.phone_fax` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.phone_home` | excluded | исключено: исключено: личный телефон сотрудника (решение владельца, Q-09) |  | 3 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.phone_mobile` | rule | перенос | User.phoneNumber[Mobile] | 5 | 5 | 0 | 0 | carried=5 |
| Users | vtiger7 | `vtiger_users.phone_other` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.phone_work` | rule | перенос | User.phoneNumber[Office] | 5 | 5 | 0 | 0 | carried=2, normalized=3 |
| Users | vtiger7 | `vtiger_users.reminder_interval` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 2 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.reminder_next_time` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.reports_to_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.rowheight` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 6 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.secondaryemail` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.signature` | rule | перенос | User.preferences.signature | 2 | 2 | 0 | 0 | carried=2 |
| Users | vtiger7 | `vtiger_users.sp_domru_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_gravitel_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_mango_extension` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_mcn_extension` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_megafon_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_rostelecom_extension` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_rostelecom_extension_internal` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_rostelecom_extension_sipiru` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_sipuni_extension` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_telphin_extension` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_uiscom_extension` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_uiscom_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_westcall_spb_id` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_yandex_extension` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_yandex_outgoing_number` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_zadarma_extension` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.sp_zebra_login` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.start_hour` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.status` | rule | перенос | User.isActive | 7 | 7 | 0 | 0 | mapped=7 |
| Users | vtiger7 | `vtiger_users.theme` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.time_zone` | rule | перенос | User.preferences.timeZone | 7 | 7 | 0 | 0 | carried=7 |
| Users | vtiger7 | `vtiger_users.title` | rule | перенос | User.title | 5 | 5 | 0 | 0 | carried=5 |
| Users | vtiger7 | `vtiger_users.truncate_trailing_zeros` | excluded | исключено: UI-настройка Vtiger (Preferences EspoCRM задаются заново) |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.tz` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.user_hash` | excluded | исключено: исключено: секрет |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.user_name` | rule | перенос | User.userName | 7 | 7 | 0 | 0 | carried=7 |
| Users | vtiger7 | `vtiger_users.user_password` | excluded | исключено: исключено: секрет; пароли задаются заново |  | 7 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.user_preferences` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.weekstart` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Users | vtiger7 | `vtiger_users.workdays` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.cf_view` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.cf_viewname` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.createdtime` | rule | перенос | Vendor (собственная).createdAt | 3 | 3 | 0 | 0 | carried=3 |
| Vendors | vtiger7 | `vtiger_crmentity.crmid` | key | перенос |  | 3 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.deleted` | empty | пусто — данных нет |  | 3 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.description` | rule | пусто — данных нет | Vendor (собственная).description | 0 | 0 | 0 | 0 |  |
| Vendors | vtiger7 | `vtiger_crmentity.label` | excluded | исключено: производное (имя записи) |  | 3 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.modifiedby` | rule | перенос | Vendor (собственная).modifiedBy | 3 | 3 | 0 | 0 | linked=3 |
| Vendors | vtiger7 | `vtiger_crmentity.modifiedtime` | rule | перенос | Vendor (собственная).modifiedAt | 3 | 3 | 0 | 0 | carried=3 |
| Vendors | vtiger7 | `vtiger_crmentity.presence` | excluded | исключено: служебное |  | 3 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.setype` | key | перенос |  | 3 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.smcreatorid` | rule | перенос | Vendor (собственная).createdBy | 3 | 3 | 0 | 0 | linked=3 |
| Vendors | vtiger7 | `vtiger_crmentity.smgroupid` | excluded | исключено: служебное (все 0) |  | 3 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.smownerid` | rule | перенос | Vendor (собственная).assignedUser / teams | 3 | 3 | 0 | 0 | linked=3 |
| Vendors | vtiger7 | `vtiger_crmentity.source` | excluded | исключено: исключено: технический канал создания записи Vtiger (CRM/WEBSERVICE) |  | 3 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.status` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.version` | excluded | исключено: служебное |  | 3 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_crmentity.viewedtime` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.category` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.city` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.country` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.description` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.email` | rule | перенос | Vendor (собственная).emailAddress | 1 | 1 | 0 | 0 | carried=1 |
| Vendors | vtiger7 | `vtiger_vendor.glacct` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.phone` | rule | перенос | Vendor (собственная).phoneNumber[Office] | 1 | 1 | 0 | 0 | type_conflict=1 |
| Vendors | vtiger7 | `vtiger_vendor.pobox` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.postalcode` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.state` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.street` | empty | пусто — данных нет |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.tags` | excluded | исключено: пусто в источнике (теги — vtiger_freetagged_objects) |  | 0 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.vendor_no` | rule | перенос | Vendor (собственная).vtigerNo | 3 | 3 | 0 | 0 | carried=3 |
| Vendors | vtiger7 | `vtiger_vendor.vendorid` | key | перенос |  | 3 |  |  |  |  |
| Vendors | vtiger7 | `vtiger_vendor.vendorname` | rule | перенос | Vendor (собственная).name | 3 | 3 | 0 | 0 | carried=3 |
| Vendors | vtiger7 | `vtiger_vendor.website` | rule | перенос | Vendor (собственная).website | 2 | 2 | 0 | 0 | carried=2 |
| Vendors | vtiger7 | `vtiger_vendorcf.cf_1206` | rule | перенос | Vendor (собственная).inn | 2 | 2 | 0 | 0 | carried=2 |
| Vendors | vtiger7 | `vtiger_vendorcf.vendorid` | key | перенос |  | 3 |  |  |  |  |
| links | vtiger7 | `vtiger_cntactivityrel.activityid` | relation | pair |  | 6 |  |  |  |  |
| links | vtiger7 | `vtiger_cntactivityrel.contactid` | relation | pair |  | 6 |  |  |  |  |
| links | vtiger7 | `vtiger_contpotentialrel.contactid` | relation | pair |  | 5 |  |  |  |  |
| links | vtiger7 | `vtiger_contpotentialrel.potentialid` | relation | pair |  | 5 |  |  |  |  |
| links | vtiger7 | `vtiger_crmentityrel.crmid` | relation | pair |  | 2356 |  |  |  |  |
| links | vtiger7 | `vtiger_crmentityrel.module` | relation | pair |  | 2356 |  |  |  |  |
| links | vtiger7 | `vtiger_crmentityrel.relcrmid` | relation | pair |  | 2356 |  |  |  |  |
| links | vtiger7 | `vtiger_crmentityrel.relmodule` | relation | pair |  | 2356 |  |  |  |  |
| links | vtiger7 | `vtiger_email_track.access_count` | relation | pair |  | 23 |  |  |  |  |
| links | vtiger7 | `vtiger_email_track.click_count` | relation | pair |  | 23 |  |  |  |  |
| links | vtiger7 | `vtiger_email_track.crmid` | relation | pair |  | 23 |  |  |  |  |
| links | vtiger7 | `vtiger_email_track.mailid` | relation | pair |  | 23 |  |  |  |  |
| links | vtiger7 | `vtiger_freetagged_objects.module` | relation | pair |  | 33 |  |  |  |  |
| links | vtiger7 | `vtiger_freetagged_objects.object_id` | relation | pair |  | 33 |  |  |  |  |
| links | vtiger7 | `vtiger_freetagged_objects.tag_id` | relation | pair |  | 33 |  |  |  |  |
| links | vtiger7 | `vtiger_freetagged_objects.tagged_on` | excluded | excluded: время постановки тега — у значения multiEnum его нет |  | 33 |  |  |  |  |
| links | vtiger7 | `vtiger_freetagged_objects.tagger_id` | excluded | excluded: автор постановки тега — у значения multiEnum его нет |  | 33 |  |  |  |  |
| links | vtiger7 | `vtiger_freetags.id` | relation | pair |  | 14 |  |  |  |  |
| links | vtiger7 | `vtiger_freetags.owner` | excluded | excluded: автор тега Vtiger |  | 14 |  |  |  |  |
| links | vtiger7 | `vtiger_freetags.raw_tag` | relation | pair |  | 14 |  |  |  |  |
| links | vtiger7 | `vtiger_freetags.tag` | excluded | excluded: нормализованная форма raw_tag (значение тега — raw_tag) |  | 14 |  |  |  |  |
| links | vtiger7 | `vtiger_freetags.visibility` | excluded | excluded: видимость тега Vtiger (теги EspoCRM — значения поля) |  | 14 |  |  |  |  |
| links | vtiger7 | `vtiger_groups.description` | excluded | excluded: группы воспроизводятся командами (D-39), описание не переносится |  | 3 |  |  |  |  |
| links | vtiger7 | `vtiger_groups.groupid` | relation | pair |  | 3 |  |  |  |  |
| links | vtiger7 | `vtiger_groups.groupname` | relation | pair |  | 3 |  |  |  |  |
| links | vtiger7 | `vtiger_salesmanactivityrel.activityid` | relation | pair |  | 86 |  |  |  |  |
| links | vtiger7 | `vtiger_salesmanactivityrel.smid` | relation | pair |  | 86 |  |  |  |  |
| links | vtiger7 | `vtiger_salesmanattachmentsrel.attachmentsid` | relation | pair |  | 1 |  |  |  |  |
| links | vtiger7 | `vtiger_salesmanattachmentsrel.smid` | relation | pair |  | 1 |  |  |  |  |
| links | vtiger7 | `vtiger_seactivityrel.activityid` | relation | pair |  | 109 |  |  |  |  |
| links | vtiger7 | `vtiger_seactivityrel.crmid` | relation | pair |  | 109 |  |  |  |  |
| links | vtiger7 | `vtiger_seattachmentsrel.attachmentsid` | relation | pair |  | 203 |  |  |  |  |
| links | vtiger7 | `vtiger_seattachmentsrel.crmid` | relation | pair |  | 203 |  |  |  |  |
| links | vtiger7 | `vtiger_senotesrel.crmid` | relation | pair |  | 221 |  |  |  |  |
| links | vtiger7 | `vtiger_senotesrel.notesid` | relation | pair |  | 221 |  |  |  |  |
| links | vtiger7 | `vtiger_user2role.roleid` | relation | pair |  | 7 |  |  |  |  |
| links | vtiger7 | `vtiger_user2role.userid` | relation | pair |  | 7 |  |  |  |  |
| links | vtiger7 | `vtiger_users2group.groupid` | relation | pair |  | 4 |  |  |  |  |
| links | vtiger7 | `vtiger_users2group.userid` | relation | pair |  | 4 |  |  |  |  |

## Каждая непустая колонка снимка

Обе схемы снимка, счётчики сервера (`tables.json`). Класс — полная сверка (`import.md`): `import` — таблица, которую читает импорт (живые записи сверены по одному, удалённые в Vtiger и строки вне границ импорта — отдельные счётчики), остальные — судьба карты. Ненулевых — для числовых колонок.

| Колонка | Класс | Значений | Ненулевых | Живых | Сверено | Расхождений | Неучтённых | Удалённых в Vtiger | Вне границ | Судьбы |
|---|---|---|---|---|---|---|---|---|---|---|
| `asteriskcdrdb.cdr.amaflags` | import | 124 | 124 | 124 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.billsec` | import | 124 | 112 | 124 | 65 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.calldate` | import | 124 |  | 124 | 65 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.channel` | import | 124 |  | 124 | 65 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.clid` | import | 124 |  | 124 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.dcontext` | import | 124 |  | 124 | 65 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.disposition` | import | 124 |  | 124 | 65 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.dst` | import | 124 |  | 124 | 65 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.dstchannel` | import | 50 |  | 50 | 50 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.duration` | import | 124 | 120 | 124 | 65 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.id` | import | 124 | 124 | 124 | 0 | 0 | 0 | 0 | 0 | key=1 |
| `asteriskcdrdb.cdr.lastapp` | import | 124 |  | 124 | 65 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.lastdata` | import | 110 |  | 110 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.linkedid` | import | 124 |  | 124 | 0 | 0 | 0 | 0 | 0 | key=1 |
| `asteriskcdrdb.cdr.recordingpath` | import | 107 |  | 107 | 51 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.sequence` | import | 124 | 92 | 124 | 0 | 0 | 0 | 0 | 0 | key=1 |
| `asteriskcdrdb.cdr.src` | import | 116 |  | 116 | 65 | 0 | 0 | 0 | 0 | rule=1 |
| `asteriskcdrdb.cdr.uniqueid` | import | 124 |  | 124 | 0 | 0 | 0 | 0 | 0 | key=1 |
| `vtiger7.berli_globalsearch_data.gscrmid` | excluded | 5147 | 5147 |  |  |  |  |  |  | excluded |
| `vtiger7.berli_globalsearch_settings.gstabid` | excluded | 38 | 38 |  |  |  |  |  |  | excluded |
| `vtiger7.berli_globalsearch_settings.searchall` | excluded | 38 | 38 |  |  |  |  |  |  | excluded |
| `vtiger7.berli_globalsearch_settings.sequence` | excluded | 38 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.berli_globalsearch_settings.turn_off` | excluded | 38 | 37 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflow_tasktypes.classname` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflow_tasktypes.classpath` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflow_tasktypes.id` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflow_tasktypes.label` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflow_tasktypes.modules` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflow_tasktypes.sourcemodule` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflow_tasktypes.tasktypename` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflow_tasktypes.templatepath` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflow_tasktypes_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.defaultworkflow` | excluded | 23 | 23 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.execution_condition` | excluded | 26 | 26 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.filtersavedinnew` | excluded | 26 | 26 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.module_name` | excluded | 26 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.status` | excluded | 26 | 26 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.summary` | excluded | 26 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.test` | excluded | 19 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.type` | excluded | 26 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.workflow_id` | excluded | 26 | 26 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows.workflowname` | excluded | 26 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflows_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks.summary` | excluded | 27 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks.task` | excluded | 28 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks.task_id` | excluded | 28 | 28 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks.workflow_id` | excluded | 26 | 26 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks_entitymethod.function_name` | excluded | 14 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks_entitymethod.function_path` | excluded | 14 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks_entitymethod.method_name` | excluded | 14 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks_entitymethod.module_name` | excluded | 14 |  |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks_entitymethod.workflowtasks_entitymethod_id` | excluded | 14 | 14 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks_entitymethod_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.com_vtiger_workflowtasks_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.fieldautofill_mappings.id` | excluded | 139 | 139 |  |  |  |  |  |  | excluded |
| `vtiger7.fieldautofill_mappings.key` | excluded | 139 |  |  |  |  |  |  |  | excluded |
| `vtiger7.fieldautofill_mappings.primary` | excluded | 138 |  |  |  |  |  |  |  | excluded |
| `vtiger7.fieldautofill_mappings.secondary` | excluded | 138 |  |  |  |  |  |  |  | excluded |
| `vtiger7.fieldautofill_mappings.show_popup` | excluded | 138 | 138 |  |  |  |  |  |  | excluded |
| `vtiger7.its4you_reports4you_folder.folderid` | module_code | 13 | 13 |  |  |  |  |  |  | module_code |
| `vtiger7.its4you_reports4you_folder.foldername` | module_code | 13 |  |  |  |  |  |  |  | module_code |
| `vtiger7.its4you_reports4you_folder.ownerid` | module_code | 13 | 0 |  |  |  |  |  |  | module_code |
| `vtiger7.its4you_reports4you_folder.state` | module_code | 13 |  |  |  |  |  |  |  | module_code |
| `vtiger7.its4you_reports4you_reportfilters.filterid` | module_code | 3 | 3 |  |  |  |  |  |  | module_code |
| `vtiger7.its4you_reports4you_reportfilters.name` | module_code | 3 |  |  |  |  |  |  |  | module_code |
| `vtiger7.its4you_reports4you_selectquery_seq.id` | module_code | 1 | 0 |  |  |  |  |  |  | module_code |
| `vtiger7.its4you_reports4you_updates.id` | module_code | 1 | 1 |  |  |  |  |  |  | module_code |
| `vtiger7.its4you_reports4you_updates.name` | module_code | 1 |  |  |  |  |  |  |  | module_code |
| `vtiger7.its4you_reports4you_updates.status` | module_code | 1 | 1 |  |  |  |  |  |  | module_code |
| `vtiger7.kanban_view_settings.enable` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.masked_input_fields.active` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.masked_input_fields.fieldname` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.masked_input_fields.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.masked_input_fields.masked_input` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.masked_input_fields.module` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.masked_inputs.alert` | excluded | 8 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.masked_inputs.alert_text` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.masked_inputs.id` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.masked_inputs.masked_input` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.notifications_settings.enable` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.comment` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.discount_amount` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.discount_percent` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.item_name` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.listprice` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.module` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.net_price` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.quantity` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.tax_total` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.total` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_invoice_settings.total_fields` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.comment` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.discount_amount` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.discount_percent` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.item_name` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.listprice` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.module` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.net_price` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.quantity` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.tax_total` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.total` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_purchaseorder_settings.total_fields` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.comment` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.discount_amount` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.discount_percent` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.item_name` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.listprice` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.module` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.net_price` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.quantity` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.tax_total` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.total` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_quotes_settings.total_fields` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.comment` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.discount_amount` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.discount_percent` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.item_name` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.listprice` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.module` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.net_price` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.quantity` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.tax_total` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.total` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.quoter_salesorder_settings.total_fields` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.realtimefieldformulas_settings.enable` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.relatedblockslists_settings.enable` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_cml_site_settings.id` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_cml_site_settings.key` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.sp_cml_site_settings.setting_type` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.sp_cml_site_settings.value` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.sp_payments.amount` | import | 991 | 989 | 799 | 799 | 0 | 0 | 192 | 0 | rule=1 |
| `vtiger7.sp_payments.analytics_code` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.sp_payments.doc_no` | import | 991 | 847 | 799 | 657 | 0 | 0 | 192 | 0 | rule=1 |
| `vtiger7.sp_payments.pay_date` | import | 991 |  | 799 | 799 | 0 | 0 | 192 | 0 | rule=1 |
| `vtiger7.sp_payments.pay_details` | import | 854 |  | 663 | 663 | 0 | 0 | 191 | 0 | rule=1 |
| `vtiger7.sp_payments.pay_no` | import | 991 |  | 799 | 799 | 0 | 0 | 192 | 0 | rule=1 |
| `vtiger7.sp_payments.pay_type` | import | 991 |  | 799 | 799 | 0 | 0 | 192 | 0 | rule=1 |
| `vtiger7.sp_payments.payer` | import | 991 | 778 | 799 | 756 | 0 | 0 | 192 | 0 | rule=1 |
| `vtiger7.sp_payments.payid` | import | 991 | 991 | 799 | 0 | 0 | 0 | 192 | 0 | key=1, вне границ: key |
| `vtiger7.sp_payments.related_to` | import | 991 | 623 | 799 | 623 | 0 | 0 | 192 | 0 | rule=1 |
| `vtiger7.sp_payments.spcompany` | import | 612 |  | 611 | 611 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.sp_payments.spstatus` | import | 972 |  | 781 | 781 | 0 | 0 | 191 | 0 | rule=1 |
| `vtiger7.sp_payments.type_payment` | import | 988 |  | 797 | 797 | 0 | 0 | 191 | 0 | rule=1 |
| `vtiger7.sp_paymentscf.cf_1198` | import | 794 | 399 | 603 | 603 | 0 | 0 | 191 | 0 | rule=1 |
| `vtiger7.sp_paymentscf.cf_1200` | import | 380 |  | 190 | 190 | 0 | 0 | 190 | 0 | rule=1 |
| `vtiger7.sp_paymentscf.cf_1202` | import | 398 |  | 208 | 208 | 0 | 0 | 190 | 0 | rule=1 |
| `vtiger7.sp_paymentscf.cf_1204` | import | 378 |  | 188 | 188 | 0 | 0 | 190 | 0 | rule=1 |
| `vtiger7.sp_paymentscf.cf_1380` | import | 991 |  | 799 | 799 | 0 | 0 | 192 | 0 | rule=1 |
| `vtiger7.sp_paymentscf.payid` | import | 991 | 991 | 799 | 0 | 0 | 0 | 192 | 0 | key=1, вне границ: key |
| `vtiger7.sp_templates.footer_size` | module_code | 11 | 8 |  |  |  |  |  |  | module_code |
| `vtiger7.sp_templates.header_size` | module_code | 11 | 10 |  |  |  |  |  |  | module_code |
| `vtiger7.sp_templates.module` | module_code | 11 |  |  |  |  |  |  |  | module_code |
| `vtiger7.sp_templates.name` | module_code | 11 |  |  |  |  |  |  |  | module_code |
| `vtiger7.sp_templates.page_orientation` | module_code | 11 |  |  |  |  |  |  |  | module_code |
| `vtiger7.sp_templates.spcompany` | module_code | 11 |  |  |  |  |  |  |  | module_code |
| `vtiger7.sp_templates.template` | module_code | 11 |  |  |  |  |  |  |  | module_code |
| `vtiger7.sp_templates.templateid` | module_code | 11 | 11 |  |  |  |  |  |  | module_code |
| `vtiger7.sp_templates_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_dependent_fields.field_id` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_dependent_fields.provider_fieldname` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_dependent_fields.rule_id` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_dependent_fields.vtiger_fieldname` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_dependent_fields_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_module_rules.field` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_module_rules.module` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_module_rules.provider_id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_module_rules.rule_id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_module_rules.type` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_module_rules_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_providers.provider_id` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_providers.provider_name` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.sp_tips_providers.settings` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.time_tracker_settings.allow_bill_event_invoice` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.time_tracker_settings.allow_bill_event_sales_orders` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.time_tracker_settings.allow_create_comments` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.time_tracker_settings.allow_show_in_timesheets` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.time_tracker_settings.auto_create_comments` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.time_tracker_settings.due_datetime_editable` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.time_tracker_settings.field_settings` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.time_tracker_settings.selected_modules` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.time_tracker_settings.start_datetime_editable` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_groups.active` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_groups.creator` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_groups.group_name` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_groups.groupid` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_groups.modified_by` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu.active` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu.creator` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu.last_module_id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu.menuid` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu.modified_by` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_groups_rel.groupid` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_groups_rel.menuid` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.active` | excluded | 58 | 58 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.creator` | excluded | 58 | 58 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.groupid` | excluded | 58 | 58 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.itemid` | excluded | 58 | 58 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.label` | excluded | 58 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.link` | excluded | 56 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.menuid` | excluded | 58 | 58 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.modified_by` | excluded | 58 | 58 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.module` | excluded | 58 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.sequence` | excluded | 58 | 58 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_advance_menu_settings_menu_items.type` | excluded | 58 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_calendarhorizontal_user_profiles.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_calendarhorizontal_user_profiles.params` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_calendarhorizontal_user_profiles.type` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_calendarhorizontal_user_profiles.user_id` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_calendarpopup_modules.selected_modules` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_comments_settings.always_show` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_comments_settings.enable` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_comments_settings.enable_richtext` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_comments_settings.order_by` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_comments_settings.row_to_show` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_comments_settings.tag_feature` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_comments_settings.text_length` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts.condition` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts.description` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts.module` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts_task.action_title` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts_task.active` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts_task.alert_on_save` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts_task.alert_when_open` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts_task.alert_while_edit` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts_task.cat_id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts_task.description` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts_task.donot_allow_to_save` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_conditional_alerts_task.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.activities_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.all_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.comments_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.contact_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.document_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.helpdesk_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.milestones_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.product_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.tabid` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.tasks_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_default_widgets.update_widget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_duplicate_check_merge_setting.fields` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_duplicate_check_merge_setting.id` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_duplicate_check_merge_setting.module` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_emailconverter_actions.action` | excluded | 4 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_emailconverter_actions.action_name` | excluded | 4 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_emailconverter_actions.id` | excluded | 4 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_emailconverter_actions.modulename1` | excluded | 4 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_emailconverter_actions.modulename2` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_google_apikey.google_apikey` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_googleaddress.address_name` | excluded | 14 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_googleaddress.id` | excluded | 14 | 14 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_googleaddress.module_name` | excluded | 14 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_googleaddress.status` | excluded | 14 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_googleaddress_config.address_id` | excluded | 70 | 70 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_googleaddress_config.google_fields` | excluded | 70 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_googleaddress_config.vtiger_fields` | excluded | 70 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_history_log_settings.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_history_log_settings.params` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_listview_colors.bg_color` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_listview_colors.condition_name` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_listview_colors.conditions` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_listview_colors.conditions_count` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_listview_colors.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_listview_colors.modulename` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_listview_colors.priority` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_listview_colors.status` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_listview_colors.text_color` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_modules.module` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_modules.valid` | excluded | 41 | 26 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_quick_edit.status` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_reports_folder.description` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_reports_folder.folderid` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_reports_folder.foldername` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_reports_folder.ownerid` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_reports_folder.state` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_reports_selectquery_seq.id` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.copyright` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.description` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.header` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.images` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.logo` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.slide_easing` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.slide_speed` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.slide_type` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.social_facebook` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.social_twitter` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_user_login.social_youtube` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_widgets.data` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_widgets.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_widgets.isactive` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_widgets.label` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_widgets.sequence` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_widgets.tabid` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vte_widgets.type` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vte_widgets.wcol` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vteemailmarketing_settings.enable` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtepopupreminder_settings.enable` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtestore_system_info.description` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtestore_system_info.name` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtestore_system_info.value` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_account.account_no` | import | 182 |  | 180 | 180 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.account_type` | import | 29 |  | 29 | 29 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_account.accountid` | import | 182 | 182 | 180 | 0 | 0 | 0 | 2 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_account.accountname` | import | 182 |  | 180 | 180 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.annualrevenue` | import | 182 | 0 | 180 | 0 | 0 | 0 | 2 | 0 | empty=1 |
| `vtiger7.vtiger_account.email1` | import | 119 |  | 117 | 117 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.email2` | import | 15 |  | 15 | 15 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_account.emailoptout` | import | 182 |  | 180 | 0 | 0 | 0 | 2 | 0 | empty=1 |
| `vtiger7.vtiger_account.employees` | import | 182 | 45 | 180 | 43 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.fax` | import | 40 |  | 40 | 40 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_account.industry` | import | 91 |  | 89 | 89 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.inn` | import | 92 |  | 90 | 90 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.isconvertedfromlead` | import | 182 |  | 180 | 180 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.kpp` | import | 78 |  | 76 | 76 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.notify_owner` | import | 182 |  | 180 | 0 | 0 | 0 | 2 | 0 | excluded=1 |
| `vtiger7.vtiger_account.otherphone` | import | 28 |  | 27 | 27 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_account.ownership` | import | 8 |  | 8 | 8 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_account.parentid` | import | 182 | 0 | 180 | 0 | 0 | 0 | 2 | 0 | empty=1 |
| `vtiger7.vtiger_account.phone` | import | 46 |  | 46 | 46 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_account.rating` | import | 57 |  | 55 | 55 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.siccode` | import | 68 |  | 66 | 66 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.tickersymbol` | import | 101 |  | 99 | 99 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_account.website` | import | 97 |  | 95 | 95 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountbillads.accountaddressid` | import | 182 | 182 | 180 | 0 | 0 | 0 | 2 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_accountbillads.bill_city` | import | 130 |  | 128 | 128 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountbillads.bill_code` | import | 102 |  | 100 | 100 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountbillads.bill_country` | import | 118 |  | 116 | 116 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountbillads.bill_state` | import | 77 |  | 75 | 75 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountbillads.bill_street` | import | 129 |  | 127 | 127 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountscf.accountid` | import | 182 | 182 | 180 | 0 | 0 | 0 | 2 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_accountscf.cf_1109` | import | 158 |  | 156 | 156 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountscf.cf_1111` | import | 80 |  | 78 | 78 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountscf.cf_1113` | import | 156 |  | 154 | 154 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountscf.cf_1115` | import | 157 |  | 155 | 155 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountscf.vk_url` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_accountshipads.accountaddressid` | import | 182 | 182 | 180 | 0 | 0 | 0 | 2 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_accountshipads.ship_city` | import | 130 |  | 128 | 128 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountshipads.ship_code` | import | 98 |  | 97 | 97 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_accountshipads.ship_country` | import | 118 |  | 116 | 116 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountshipads.ship_pobox` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_accountshipads.ship_state` | import | 77 |  | 75 | 75 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accountshipads.ship_street` | import | 129 |  | 127 | 127 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_accounttype.accounttype` | configuration | 11 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_accounttype.accounttypeid` | configuration | 11 | 11 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_accounttype.picklist_valueid` | configuration | 11 | 11 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_accounttype.presence` | configuration | 11 | 11 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_accounttype.sortorderid` | configuration | 11 | 11 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_accounttype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_actionmapping.actionid` | excluded | 26 | 23 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_actionmapping.actionname` | excluded | 26 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_actionmapping.securitycheck` | excluded | 26 | 12 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity.activityid` | import | 366 | 366 | 115 | 0 | 0 | 0 | 251 | 0 | key=3, вне границ: key |
| `vtiger7.vtiger_activity.activitytype` | import | 366 |  | 115 | 86 | 0 | 0 | 251 | 0 | excluded=1, rule=2 |
| `vtiger7.vtiger_activity.date_start` | import | 364 |  | 113 | 113 | 0 | 0 | 251 | 0 | rule=3 |
| `vtiger7.vtiger_activity.due_date` | import | 184 |  | 84 | 84 | 0 | 0 | 100 | 0 | rule=2, unmapped=1 |
| `vtiger7.vtiger_activity.duration_hours` | import | 186 |  | 86 | 52 | 0 | 0 | 100 | 0 | excluded=1, rule=1, unmapped=1 |
| `vtiger7.vtiger_activity.duration_minutes` | import | 186 |  | 86 | 52 | 0 | 0 | 100 | 0 | excluded=1, rule=1, unmapped=1 |
| `vtiger7.vtiger_activity.eventstatus` | import | 152 |  | 52 | 52 | 0 | 0 | 100 | 0 | excluded=1, rule=1, unmapped=1 |
| `vtiger7.vtiger_activity.invoiceid` | import | 52 | 0 | 52 | 0 | 0 | 0 | 0 | 0 | empty=1, unmapped=2 |
| `vtiger7.vtiger_activity.location` | import | 5 |  | 0 | 0 | 0 | 0 | 5 | 0 | empty=2, unmapped=1 |
| `vtiger7.vtiger_activity.notime` | import | 366 |  | 115 | 0 | 0 | 0 | 251 | 0 | excluded=3 |
| `vtiger7.vtiger_activity.popup_reminder_time` | import | 86 |  | 86 | 0 | 0 | 0 | 0 | 0 | excluded=2, unmapped=1 |
| `vtiger7.vtiger_activity.priority` | import | 9 |  | 9 | 9 | 0 | 0 | 0 | 0 | rule=2, unmapped=1 |
| `vtiger7.vtiger_activity.recurringtype` | import | 52 |  | 52 | 0 | 0 | 0 | 0 | 0 | excluded=2, unmapped=1 |
| `vtiger7.vtiger_activity.salesorder_id` | import | 52 | 0 | 52 | 0 | 0 | 0 | 0 | 0 | empty=1, unmapped=2 |
| `vtiger7.vtiger_activity.semodule` | import | 2 |  | 2 | 2 | 0 | 0 | 0 | 0 | rule=1, unmapped=2 |
| `vtiger7.vtiger_activity.sendnotification` | import | 366 |  | 115 | 0 | 0 | 0 | 251 | 0 | excluded=3 |
| `vtiger7.vtiger_activity.status` | import | 34 |  | 34 | 34 | 0 | 0 | 0 | 0 | rule=1, unmapped=2 |
| `vtiger7.vtiger_activity.subject` | import | 366 |  | 115 | 115 | 0 | 0 | 251 | 0 | rule=3 |
| `vtiger7.vtiger_activity.time_end` | import | 150 |  | 50 | 50 | 0 | 0 | 100 | 0 | empty=1, rule=1, unmapped=1 |
| `vtiger7.vtiger_activity.time_start` | import | 366 |  | 115 | 115 | 0 | 0 | 251 | 0 | rule=3 |
| `vtiger7.vtiger_activity.timesheet_id` | import | 52 | 0 | 52 | 0 | 0 | 0 | 0 | 0 | empty=1, unmapped=2 |
| `vtiger7.vtiger_activity.visibility` | import | 366 |  | 115 | 0 | 0 | 0 | 251 | 0 | excluded=3 |
| `vtiger7.vtiger_activity_reminder.activity_id` | key | 64 | 64 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_activity_reminder.recurringid` | excluded | 64 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_reminder.reminder_sent` | excluded | 64 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_reminder.reminder_time` | empty | 64 | 0 |  |  |  |  |  |  | empty |
| `vtiger7.vtiger_activity_reminder_popup.date_start` | excluded | 10 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_reminder_popup.recordid` | excluded | 12 | 12 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_reminder_popup.reminderid` | excluded | 12 | 12 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_reminder_popup.semodule` | excluded | 12 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_reminder_popup.status` | excluded | 12 | 11 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_reminder_popup.time_start` | excluded | 12 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_view.activity_view` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_view.activity_viewid` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_view.presence` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_view.sortorderid` | excluded | 5 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activity_view_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_activitycf.activityid` | key | 186 | 186 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_activitytype.activitytype` | configuration | 5 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_activitytype.activitytypeid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_activitytype.color` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_activitytype.picklist_valueid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_activitytype.presence` | configuration | 5 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_activitytype.sortorderid` | configuration | 5 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_activitytype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_app2tab.appname` | excluded | 66 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_app2tab.sequence` | excluded | 66 | 66 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_app2tab.tabid` | excluded | 66 | 66 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_app2tab.visible` | excluded | 66 | 53 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_assets.account` | import | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assets.asset_no` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assets.assetname` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assets.assetsid` | import | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_assets.assetstatus` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assets.contact` | import | 3 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assets.dateinservice` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assets.datesold` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assets.invoiceid` | import | 3 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assets.product` | import | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assets.serialnumber` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_assetscf.assetsid` | import | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: key |
| `vtiger7.vtiger_assetstatus.assetstatus` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_assetstatus.assetstatusid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_assetstatus.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_assetstatus.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_assetstatus.sortorderid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_assetstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_asteriskextensions.userid` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_attachments.attachmentsid` | import | 572 | 572 | 204 | 0 | 0 | 0 | 0 | 368 | key=1, вне границ: key |
| `vtiger7.vtiger_attachments.description` | import | 371 |  | 3 | 3 | 0 | 0 | 0 | 368 | rule=1, вне границ: archive |
| `vtiger7.vtiger_attachments.name` | import | 572 |  | 204 | 204 | 0 | 0 | 0 | 368 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_attachments.path` | import | 572 |  | 204 | 204 | 0 | 0 | 0 | 368 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_attachments.type` | import | 572 |  | 204 | 204 | 0 | 0 | 0 | 368 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_attachmentsfolder.createdby` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_attachmentsfolder.description` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_attachmentsfolder.folderid` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_attachmentsfolder.foldername` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_attachmentsfolder.sequence` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_attachmentsfolder_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.blockid` | excluded | 173 | 173 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.blocklabel` | excluded | 172 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.create_view` | excluded | 173 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.detail_view` | excluded | 173 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.display_status` | excluded | 173 | 173 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.edit_view` | excluded | 173 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.iscustom` | excluded | 173 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.sequence` | excluded | 173 | 173 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.show_title` | excluded | 173 | 6 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.tabid` | excluded | 173 | 173 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks.visible` | excluded | 173 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_blocks_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_default_activitytypes.defaultcolor` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_default_activitytypes.fieldname` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_default_activitytypes.id` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_default_activitytypes.isdefault` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_default_activitytypes.module` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_default_activitytypes_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_user_activitytypes.color` | excluded | 56 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_user_activitytypes.defaultid` | excluded | 56 | 56 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_user_activitytypes.id` | excluded | 56 | 56 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_user_activitytypes.userid` | excluded | 56 | 56 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_user_activitytypes.visible` | excluded | 56 | 56 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendar_user_activitytypes_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_calendarsharedtype.calendarsharedtype` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_calendarsharedtype.calendarsharedtypeid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_calendarsharedtype.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_calendarsharedtype.sortorderid` | configuration | 3 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_calendarsharedtype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_callduration.callduration` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_callduration.calldurationid` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_callduration.presence` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_callduration.sortorderid` | excluded | 5 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_callduration_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_campaignrelstatus.campaignrelstatus` | empty | 3 |  |  |  |  |  |  |  | empty |
| `vtiger7.vtiger_campaignrelstatus.campaignrelstatusid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_campaignrelstatus.presence` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_campaignrelstatus.sortorderid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_campaignrelstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_campaignstatus.campaignstatus` | configuration | 5 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaignstatus.campaignstatusid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaignstatus.picklist_valueid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaignstatus.presence` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaignstatus.sortorderid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaignstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_campaigntype.campaigntype` | configuration | 12 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaigntype.campaigntypeid` | configuration | 12 | 12 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaigntype.picklist_valueid` | configuration | 12 | 12 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaigntype.presence` | configuration | 12 | 12 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaigntype.sortorderid` | configuration | 12 | 12 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_campaigntype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_carrier.carrier` | configuration | 5 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_carrier.carrierid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_carrier.picklist_valueid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_carrier.presence` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_carrier.sortorderid` | configuration | 5 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_carrier_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cf_1107.cf_1107` | configuration | 5 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_1107.cf_1107id` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_1107.presence` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_1107.sortorderid` | configuration | 5 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_1107_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cf_comment_picklist.cf_comment_picklist` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_comment_picklist.cf_comment_picklistid` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_comment_picklist.presence` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_comment_picklist.sortorderid` | configuration | 1 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_comment_picklist_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cf_comment_picklist_two.cf_comment_picklist_two` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_comment_picklist_two.cf_comment_picklist_twoid` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_comment_picklist_two.presence` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_comment_picklist_two.sortorderid` | configuration | 1 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_cf_comment_picklist_two_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cntactivityrel.activityid` | import | 6 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: key |
| `vtiger7.vtiger_cntactivityrel.contactid` | import | 6 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: empty, вне границ: transfer |
| `vtiger7.vtiger_contactaddress.contactaddressid` | import | 345 | 345 | 341 | 0 | 0 | 0 | 4 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_contactaddress.mailingcity` | import | 214 |  | 212 | 212 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactaddress.mailingcountry` | import | 184 |  | 182 | 182 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactaddress.mailingstate` | import | 161 |  | 159 | 159 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactaddress.mailingstreet` | import | 206 |  | 204 | 204 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactaddress.mailingzip` | import | 153 |  | 151 | 151 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactaddress.othercity` | import | 158 |  | 156 | 156 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactaddress.othercountry` | import | 156 |  | 154 | 154 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactaddress.otherstate` | import | 138 |  | 136 | 136 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactaddress.otherstreet` | import | 156 |  | 154 | 154 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactaddress.otherzip` | import | 153 |  | 151 | 151 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.accountid` | import | 345 | 236 | 341 | 234 | 0 | 0 | 4 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.contact_no` | import | 345 |  | 341 | 341 | 0 | 0 | 4 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.contactid` | import | 345 | 345 | 341 | 0 | 0 | 0 | 4 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_contactdetails.department` | import | 106 |  | 106 | 106 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.donotcall` | import | 345 |  | 341 | 0 | 0 | 0 | 4 | 0 | empty=1 |
| `vtiger7.vtiger_contactdetails.email` | import | 102 |  | 101 | 101 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.emailoptout` | import | 345 |  | 341 | 0 | 0 | 0 | 4 | 0 | empty=1 |
| `vtiger7.vtiger_contactdetails.fax` | import | 18 |  | 18 | 18 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.firstname` | import | 337 |  | 334 | 334 | 0 | 0 | 3 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.imagename` | import | 6 |  | 6 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.isconvertedfromlead` | import | 345 |  | 341 | 341 | 0 | 0 | 4 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.lastname` | import | 345 |  | 341 | 341 | 0 | 0 | 4 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.mobile` | import | 140 |  | 139 | 139 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.notify_owner` | import | 345 |  | 341 | 0 | 0 | 0 | 4 | 0 | excluded=1 |
| `vtiger7.vtiger_contactdetails.phone` | import | 120 |  | 118 | 118 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.reference` | import | 345 |  | 341 | 0 | 0 | 0 | 4 | 0 | excluded=1 |
| `vtiger7.vtiger_contactdetails.reportsto` | import | 345 |  | 341 | 0 | 0 | 0 | 4 | 0 | excluded=1 |
| `vtiger7.vtiger_contactdetails.salutation` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.secondaryemail` | import | 2 |  | 2 | 2 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactdetails.title` | import | 164 |  | 164 | 164 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactscf.cf_1322` | import | 123 |  | 122 | 122 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_contactscf.cf_1324` | import | 122 |  | 121 | 121 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_contactscf.cf_1326` | import | 126 |  | 125 | 125 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_contactscf.cf_1328` | import | 126 |  | 125 | 125 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_contactscf.cf_1372` | import | 345 |  | 341 | 341 | 0 | 0 | 4 | 0 | rule=1 |
| `vtiger7.vtiger_contactscf.cf_1374` | import | 345 |  | 341 | 341 | 0 | 0 | 4 | 0 | rule=1 |
| `vtiger7.vtiger_contactscf.cf_1376` | import | 345 |  | 341 | 341 | 0 | 0 | 4 | 0 | rule=1 |
| `vtiger7.vtiger_contactscf.cf_1378` | import | 345 |  | 341 | 341 | 0 | 0 | 4 | 0 | rule=1 |
| `vtiger7.vtiger_contactscf.contactid` | import | 345 | 345 | 341 | 0 | 0 | 0 | 4 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_contactscf.vk_url` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactsubdetails.birthday` | import | 10 |  | 10 | 10 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactsubdetails.contactsubscriptionid` | import | 345 | 345 | 341 | 0 | 0 | 0 | 4 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_contactsubdetails.homephone` | import | 77 |  | 77 | 77 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactsubdetails.laststayintouchrequest` | import | 345 | 0 | 341 | 0 | 0 | 0 | 4 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_contactsubdetails.laststayintouchsavedate` | import | 345 | 0 | 341 | 0 | 0 | 0 | 4 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_contactsubdetails.leadsource` | import | 55 |  | 55 | 55 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contactsubdetails.otherphone` | import | 4 |  | 4 | 4 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_contpotentialrel.contactid` | import | 5 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_contpotentialrel.potentialid` | import | 5 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_contract_priority.contract_priority` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_priority.contract_priorityid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_priority.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_priority.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_priority.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_priority_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_contract_status.contract_status` | configuration | 6 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_status.contract_statusid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_status.picklist_valueid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_status.presence` | configuration | 6 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_status.sortorderid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_status_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_contract_type.contract_type` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_type.contract_typeid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_type.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_type.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_type.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_contract_type_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_convertleadmapping.accountfid` | excluded | 30 | 22 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_convertleadmapping.cfmid` | excluded | 30 | 30 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_convertleadmapping.contactfid` | excluded | 30 | 16 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_convertleadmapping.editable` | excluded | 30 | 26 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_convertleadmapping.leadfid` | excluded | 30 | 30 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_convertleadmapping.potentialfid` | excluded | 30 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_convertpotentialmapping.cfmid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_convertpotentialmapping.potentialfid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_convertpotentialmapping.projectfid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_crmentity.createdtime` | import | 6881 |  | 5520 | 5305 | 0 | 0 | 502 | 859 | rule=28, вне границ: empty, вне границ: excluded |
| `vtiger7.vtiger_crmentity.crmid` | import | 6881 | 6881 | 5520 | 0 | 0 | 0 | 502 | 859 | key=28, вне границ: key |
| `vtiger7.vtiger_crmentity.deleted` | import | 6881 | 836 | 5520 | 0 | 0 | 0 | 502 | 859 | empty=28, вне границ: empty |
| `vtiger7.vtiger_crmentity.description` | import | 1365 |  | 758 | 758 | 0 | 0 | 235 | 372 | rule=22, unmapped=6, вне границ: empty, вне границ: excluded |
| `vtiger7.vtiger_crmentity.label` | import | 5830 |  | 5329 | 0 | 0 | 0 | 501 | 0 | excluded=28, вне границ: excluded |
| `vtiger7.vtiger_crmentity.modifiedby` | import | 6881 | 6679 | 5520 | 5305 | 0 | 0 | 502 | 859 | rule=28, вне границ: empty |
| `vtiger7.vtiger_crmentity.modifiedtime` | import | 6881 |  | 5520 | 5305 | 0 | 0 | 502 | 859 | rule=28, вне границ: empty, вне границ: excluded |
| `vtiger7.vtiger_crmentity.presence` | import | 6881 | 6881 | 5520 | 0 | 0 | 0 | 502 | 859 | excluded=28, вне границ: excluded |
| `vtiger7.vtiger_crmentity.setype` | import | 6881 |  | 5520 | 0 | 0 | 0 | 502 | 859 | key=28, вне границ: key |
| `vtiger7.vtiger_crmentity.smcreatorid` | import | 6881 | 6881 | 5520 | 5305 | 0 | 0 | 502 | 859 | rule=28, вне границ: empty |
| `vtiger7.vtiger_crmentity.smgroupid` | import | 6309 | 0 | 5520 | 0 | 0 | 0 | 502 | 287 | excluded=28, вне границ: excluded |
| `vtiger7.vtiger_crmentity.smownerid` | import | 6881 | 6881 | 5520 | 5305 | 0 | 0 | 502 | 859 | rule=28, вне границ: empty, вне границ: excluded |
| `vtiger7.vtiger_crmentity.source` | import | 6309 |  | 5520 | 321 | 0 | 0 | 502 | 287 | excluded=23, rule=5, вне границ: excluded |
| `vtiger7.vtiger_crmentity.version` | import | 6881 | 0 | 5520 | 0 | 0 | 0 | 502 | 859 | excluded=28, вне границ: excluded |
| `vtiger7.vtiger_crmentity_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_crmentity_user_field.recordid` | excluded | 6272 | 6272 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_crmentity_user_field.starred` | empty/excluded | 5156 |  |  |  |  |  |  |  | empty, excluded |
| `vtiger7.vtiger_crmentity_user_field.userid` | excluded | 6272 | 6272 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_crmentityrel.crmid` | import | 2679 | 2679 | 2356 | 0 | 0 | 0 | 0 | 323 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_crmentityrel.module` | import | 2679 |  | 2356 | 0 | 0 | 0 | 0 | 323 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_crmentityrel.relcrmid` | import | 2679 | 2679 | 2356 | 0 | 0 | 0 | 0 | 323 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_crmentityrel.relmodule` | import | 2679 |  | 2356 | 0 | 0 | 0 | 0 | 323 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_crmsetup.setup_status` | excluded | 6 | 6 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_crmsetup.userid` | excluded | 6 | 6 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.description` | excluded | 10 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.frequency` | excluded | 13 | 13 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.handler_file` | excluded | 13 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.id` | excluded | 13 | 13 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.lastend` | excluded | 13 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.laststart` | excluded | 13 | 10 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.module` | excluded | 13 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.name` | excluded | 13 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.sequence` | excluded | 13 | 13 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cron_task.status` | excluded | 13 | 10 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currencies.currency_code` | configuration | 138 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currencies.currency_name` | configuration | 138 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currencies.currency_symbol` | configuration | 138 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currencies.currencyid` | configuration | 138 | 138 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currencies_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_decimal_separator.currency_decimal_separator` | excluded | 4 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_decimal_separator.currency_decimal_separatorid` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_decimal_separator.presence` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_decimal_separator.sortorderid` | excluded | 5 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_decimal_separator_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_pattern.currency_grouping_pattern` | excluded | 4 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_pattern.currency_grouping_patternid` | excluded | 4 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_pattern.presence` | excluded | 4 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_pattern.sortorderid` | excluded | 4 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_pattern_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_separator.currency_grouping_separator` | excluded | 4 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_separator.currency_grouping_separatorid` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_separator.presence` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_separator.sortorderid` | excluded | 5 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_grouping_separator_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_info.conversion_rate` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currency_info.currency_code` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currency_info.currency_name` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currency_info.currency_status` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currency_info.currency_symbol` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currency_info.defaultid` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currency_info.deleted` | configuration | 1 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currency_info.id` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_currency_info_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_symbol_placement.currency_symbol_placement` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_symbol_placement.currency_symbol_placementid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_symbol_placement.presence` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_symbol_placement.sortorderid` | excluded | 2 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_currency_symbol_placement_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerdetails.customerid` | import | 345 | 345 | 341 | 0 | 0 | 0 | 4 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_customerdetails.portal` | import | 345 |  | 341 | 341 | 0 | 0 | 4 | 0 | rule=1 |
| `vtiger7.vtiger_customerdetails.support_end_date` | import | 205 |  | 205 | 205 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_customerdetails.support_start_date` | import | 205 |  | 205 | 205 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_customerportal_fields.fieldinfo` | excluded | 14 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_fields.records_visible` | excluded | 13 | 13 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_fields.tabid` | excluded | 14 | 14 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_prefs.prefkey` | excluded | 15 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_prefs.prefvalue` | excluded | 15 | 15 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_prefs.tabid` | excluded | 15 | 13 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_relatedmoduleinfo.relatedmodules` | excluded | 11 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_relatedmoduleinfo.tabid` | excluded | 11 | 11 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_settings.charts` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_settings.default_assignee` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_settings.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_settings.shortcuts` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_settings.widgets` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_tabs.createrecord` | excluded | 14 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_tabs.editrecord` | excluded | 14 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_tabs.sequence` | excluded | 14 | 14 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_tabs.tabid` | excluded | 14 | 14 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customerportal_tabs.visible` | excluded | 14 | 12 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customview.cvid` | excluded | 69 | 69 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customview.entitytype` | excluded | 69 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customview.setdefault` | excluded | 69 | 44 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customview.setmetrics` | excluded | 69 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customview.status` | excluded | 69 | 27 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customview.userid` | excluded | 69 | 69 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customview.viewname` | excluded | 69 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_customview_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvadvfilter.column_condition` | excluded | 16 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvadvfilter.columnindex` | excluded | 16 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvadvfilter.columnname` | excluded | 16 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvadvfilter.comparator` | excluded | 16 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvadvfilter.cvid` | excluded | 16 | 16 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvadvfilter.groupid` | excluded | 16 | 16 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvadvfilter.value` | excluded | 16 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvadvfilter_grouping.cvid` | excluded | 15 | 15 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvadvfilter_grouping.groupid` | excluded | 15 | 15 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvcolumnlist.columnindex` | excluded | 407 | 357 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvcolumnlist.columnname` | excluded | 407 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvcolumnlist.cvid` | excluded | 407 | 407 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvstdfilter.columnname` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvstdfilter.cvid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvstdfilter.enddate` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvstdfilter.startdate` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_cvstdfilter.stdfilter` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dashboard_tabs.id` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dashboard_tabs.isdefault` | excluded | 8 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dashboard_tabs.sequence` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dashboard_tabs.tabname` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dashboard_tabs.userid` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_module_rel.relationtype` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_module_rel.shareid` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_module_rel.tabid` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_module_rel_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_relatedmodules.datashare_relatedmodule_id` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_relatedmodules.relatedto_tabid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_relatedmodules.tabid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_relatedmodules_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_role2role.permission` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_role2role.share_roleid` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_role2role.shareid` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_datashare_role2role.to_roleid` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_date_format.date_format` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_date_format.date_formatid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_date_format.presence` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_date_format.sortorderid` | excluded | 3 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_date_format_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dayoftheweek.dayoftheweek` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dayoftheweek.dayoftheweekid` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dayoftheweek.presence` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dayoftheweek.sortorderid` | excluded | 7 | 6 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_dayoftheweek_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_def_org_field.fieldid` | excluded | 1299 | 1299 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_def_org_field.readonly` | excluded | 1299 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_def_org_field.tabid` | excluded | 1299 | 1299 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_def_org_field.visible` | excluded | 1299 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_def_org_share.editstatus` | excluded | 77 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_def_org_share.permission` | excluded | 77 | 77 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_def_org_share.ruleid` | excluded | 77 | 77 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_def_org_share.tabid` | excluded | 77 | 77 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_def_org_share_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_default_record_view.default_record_view` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_default_record_view.default_record_viewid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_default_record_view.presence` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_default_record_view.sortorderid` | excluded | 2 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_default_record_view_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultactivitytype.defaultactivitytype` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultactivitytype.defaultactivitytypeid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultactivitytype.picklist_valueid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultactivitytype.presence` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultactivitytype.sortorderid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultactivitytype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultcalendarview.defaultcalendarview` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultcalendarview.defaultcalendarviewid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultcalendarview.presence` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultcalendarview.sortorderid` | excluded | 3 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaultcalendarview_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaulteventstatus.defaulteventstatus` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaulteventstatus.defaulteventstatusid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaulteventstatus.picklist_valueid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaulteventstatus.presence` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaulteventstatus.sortorderid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_defaulteventstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_duration_minutes.duration_minutes` | configuration | 4 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_duration_minutes.minutesid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_duration_minutes.presence` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_duration_minutes.sortorderid` | configuration | 4 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_duration_minutes_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_email_track.access_count` | import | 174 | 0 | 23 | 0 | 0 | 0 | 0 | 151 | relation=1, вне границ: empty |
| `vtiger7.vtiger_email_track.click_count` | import | 174 | 0 | 23 | 0 | 0 | 0 | 0 | 151 | relation=1, вне границ: empty |
| `vtiger7.vtiger_email_track.crmid` | import | 174 | 174 | 23 | 0 | 0 | 0 | 0 | 151 | relation=1, вне границ: archive |
| `vtiger7.vtiger_email_track.mailid` | import | 174 | 174 | 23 | 0 | 0 | 0 | 0 | 151 | relation=1, вне границ: archive |
| `vtiger7.vtiger_emaildetails.bcc_email` | import | 180 |  | 29 | 0 | 0 | 0 | 151 | 0 | rule=1 |
| `vtiger7.vtiger_emaildetails.cc_email` | import | 180 |  | 29 | 0 | 0 | 0 | 151 | 0 | rule=1 |
| `vtiger7.vtiger_emaildetails.email_flag` | import | 180 |  | 29 | 29 | 0 | 0 | 151 | 0 | rule=1 |
| `vtiger7.vtiger_emaildetails.emailid` | import | 180 | 180 | 29 | 0 | 0 | 0 | 151 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_emaildetails.from_email` | import | 180 |  | 29 | 29 | 0 | 0 | 151 | 0 | rule=1 |
| `vtiger7.vtiger_emaildetails.idlists` | import | 180 |  | 29 | 29 | 0 | 0 | 151 | 0 | rule=1 |
| `vtiger7.vtiger_emaildetails.to_email` | import | 180 |  | 29 | 29 | 0 | 0 | 151 | 0 | rule=1 |
| `vtiger7.vtiger_emailslookup.crmid` | excluded | 127 | 127 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailslookup.fieldid` | excluded | 127 | 127 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailslookup.setype` | excluded | 127 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailslookup.value` | excluded | 127 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates.body` | excluded | 15 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates.deleted` | excluded | 15 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates.description` | excluded | 15 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates.foldername` | excluded | 15 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates.module` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates.subject` | excluded | 15 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates.systemtemplate` | excluded | 15 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates.templateid` | excluded | 15 | 15 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates.templatename` | excluded | 15 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_emailtemplates_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_entityname.entityidcolumn` | excluded | 43 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_entityname.entityidfield` | excluded | 43 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_entityname.fieldname` | excluded | 43 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_entityname.modulename` | excluded | 43 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_entityname.tabid` | excluded | 43 | 43 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_entityname.tablename` | excluded | 43 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandler_module.eventhandler_module_id` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandler_module.handler_class` | excluded | 9 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandler_module.module_name` | excluded | 9 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandler_module_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandlers.dependent_on` | excluded | 34 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandlers.event_name` | excluded | 34 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandlers.eventhandler_id` | excluded | 34 | 34 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandlers.handler_class` | excluded | 34 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandlers.handler_path` | excluded | 34 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandlers.is_active` | excluded | 34 | 34 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventhandlers_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_eventstatus.eventstatus` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_eventstatus.eventstatusid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_eventstatus.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_eventstatus.presence` | configuration | 3 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_eventstatus.sortorderid` | configuration | 3 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_eventstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_expectedresponse.expectedresponse` | configuration | 4 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_expectedresponse.expectedresponseid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_expectedresponse.picklist_valueid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_expectedresponse.presence` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_expectedresponse.sortorderid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_expectedresponse_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_faq.answer` | import | 63 |  | 63 | 63 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_faq.category` | import | 61 |  | 61 | 61 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_faq.faq_no` | import | 63 |  | 63 | 63 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_faq.id` | import | 63 | 63 | 63 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_faq.product_id` | import | 63 |  | 63 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_faq.question` | import | 63 |  | 63 | 63 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_faq.status` | import | 63 |  | 63 | 63 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_faqcategories.faqcategories` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqcategories.faqcategories_id` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqcategories.picklist_valueid` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqcategories.presence` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqcategories.sortorderid` | configuration | 1 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqcategories_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_faqcf.faqid` | import | 63 | 63 | 63 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: key |
| `vtiger7.vtiger_faqstatus.faqstatus` | configuration | 4 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqstatus.faqstatus_id` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqstatus.picklist_valueid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqstatus.presence` | configuration | 4 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqstatus.sortorderid` | configuration | 4 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_faqstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.block` | excluded | 1271 | 1271 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.columnname` | excluded | 1275 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.defaultvalue` | excluded | 76 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.displaytype` | excluded | 1275 | 1275 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.fieldid` | excluded | 1275 | 1275 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.fieldlabel` | excluded | 1275 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.fieldname` | excluded | 1275 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.generatedtype` | excluded | 1275 | 1275 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.headerfield` | excluded | 566 | 36 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.helpinfo` | excluded | 29 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.info_type` | excluded | 1275 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.isunique` | excluded | 1275 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.masseditable` | excluded | 1275 | 826 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.maximumlength` | excluded | 1275 | 1275 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.presence` | excluded | 1275 | 952 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.quickcreate` | excluded | 1275 | 1174 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.quickcreatesequence` | excluded | 799 | 281 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.readonly` | excluded | 1275 | 1187 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.sequence` | excluded | 1275 | 1272 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.summaryfield` | excluded | 1275 | 199 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.tabid` | excluded | 1275 | 1275 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.tablename` | excluded | 1275 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.typeofdata` | excluded | 1271 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field.uitype` | excluded | 1275 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_field_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_fieldmodulerel.fieldid` | excluded | 105 | 105 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_fieldmodulerel.module` | excluded | 105 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_fieldmodulerel.relmodule` | excluded | 105 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_fieldmodulerel.sequence` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_freetagged_objects.module` | import | 33 |  | 33 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_freetagged_objects.object_id` | import | 33 | 33 | 33 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_freetagged_objects.tag_id` | import | 33 | 33 | 33 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_freetagged_objects.tagged_on` | import | 33 |  | 33 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: transfer |
| `vtiger7.vtiger_freetagged_objects.tagger_id` | import | 33 | 33 | 33 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: transfer |
| `vtiger7.vtiger_freetags.id` | import | 14 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_freetags.owner` | import | 14 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: transfer |
| `vtiger7.vtiger_freetags.raw_tag` | import | 14 |  | 14 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_freetags.tag` | import | 14 |  | 14 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: transfer |
| `vtiger7.vtiger_freetags.visibility` | import | 14 |  | 14 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: transfer |
| `vtiger7.vtiger_freetags_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_glacct.glacct` | configuration | 9 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_glacct.glacctid` | configuration | 9 | 9 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_glacct.picklist_valueid` | configuration | 9 | 9 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_glacct.presence` | configuration | 9 | 9 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_glacct.sortorderid` | configuration | 9 | 8 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_glacct_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_event_calendar_mapping.calendar_id` | excluded | 100 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_event_calendar_mapping.event_id` | excluded | 100 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_event_calendar_mapping.user_id` | excluded | 100 | 100 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_oauth2.access_token` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_oauth2.refresh_token` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_oauth2.service` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_oauth2.userid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync.googlemodule` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync.lastsynctime` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync.synctime` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync.user` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync_localization.field_name` | excluded | 14 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync_localization.id` | excluded | 14 | 14 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync_localization.original_field_type` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync_localization.russian_field_type` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync_settings.clientgroup` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync_settings.direction` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync_settings.enabled` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync_settings.module` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_google_sync_settings.user` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_group2role.groupid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_group2role.roleid` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_group2rs.groupid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_group2rs.roleandsubid` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_groups.description` | import | 3 |  | 3 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_groups.groupid` | import | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: excluded |
| `vtiger7.vtiger_groups.groupname` | import | 3 |  | 3 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: excluded |
| `vtiger7.vtiger_homedefault.hometype` | excluded | 98 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homedefault.maxentries` | excluded | 98 | 98 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homedefault.setype` | excluded | 98 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homedefault.stuffid` | excluded | 98 | 98 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homestuff.stuffid` | excluded | 105 | 105 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homestuff.stuffsequence` | excluded | 105 | 105 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homestuff.stufftitle` | excluded | 105 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homestuff.stufftype` | excluded | 105 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homestuff.userid` | excluded | 105 | 105 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homestuff.visible` | excluded | 105 | 95 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_homestuff_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_hour_format.hour_format` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_hour_format.hour_formatid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_hour_format.presence` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_hour_format.sortorderid` | excluded | 2 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_hour_format_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.account_id` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.act_no` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.actdate` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.assigned_user_id` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.bill_city` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.bill_code` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.bill_country` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.bill_state` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.bill_street` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.contact_id` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.conversion_rate` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.createdtime` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.currency_id` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.hdnDiscountAmount` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.hdnDiscountPercent` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.hdnGrandTotal` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.hdnS_H_Amount` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.hdnTaxType` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.pre_tax_total` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.productid` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.salesorder_id` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.ship_city` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.ship_code` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.ship_country` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.ship_state` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.ship_street` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.sp_actstatus` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.status` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_1.txtAdjustment` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_locks_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_import_queue_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_industry.industry` | configuration | 54 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_industry.industryid` | configuration | 54 | 54 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_industry.picklist_valueid` | configuration | 54 | 54 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_industry.presence` | configuration | 54 | 54 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_industry.sortorderid` | configuration | 54 | 54 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_industry_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventory_tandc.id` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventory_tandc.tandc` | configuration | 6 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventory_tandc.type` | configuration | 6 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventory_tandc_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventorycharges.chargeid` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorycharges.deleted` | configuration | 1 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorycharges.format` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorycharges.istaxable` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorycharges.name` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorycharges.regions` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorycharges.taxes` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorycharges.type` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorycharges.value` | configuration | 1 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorychargesrel.charges` | excluded | 1082 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventorychargesrel.recordid` | excluded | 1082 | 1082 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventorynotification.label` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventorynotification.notificationbody` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventorynotification.notificationid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventorynotification.notificationname` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventorynotification.notificationsubject` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventorynotification_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventoryproductrel.comment` | import | 1130 |  | 1128 | 1128 | 0 | 0 | 2 | 0 | rule=5, вне границ: empty |
| `vtiger7.vtiger_inventoryproductrel.discount_amount` | import | 253 | 3 | 253 | 253 | 0 | 0 | 0 | 0 | rule=5, вне границ: empty |
| `vtiger7.vtiger_inventoryproductrel.discount_percent` | import | 250 | 0 | 250 | 250 | 0 | 0 | 0 | 0 | rule=5, вне границ: empty |
| `vtiger7.vtiger_inventoryproductrel.id` | import | 1176 | 1176 | 1173 | 1173 | 0 | 0 | 3 | 0 | rule=5, вне границ: transfer |
| `vtiger7.vtiger_inventoryproductrel.incrementondel` | import | 1176 | 698 | 1173 | 0 | 0 | 0 | 3 | 0 | excluded=5, вне границ: excluded |
| `vtiger7.vtiger_inventoryproductrel.lineitem_id` | import | 1176 | 1176 | 1173 | 0 | 0 | 0 | 3 | 0 | key=5, вне границ: key |
| `vtiger7.vtiger_inventoryproductrel.listprice` | import | 1176 | 1175 | 1173 | 1173 | 0 | 0 | 3 | 0 | rule=5, вне границ: empty |
| `vtiger7.vtiger_inventoryproductrel.margin` | import | 1176 | 910 | 1173 | 1173 | 0 | 0 | 3 | 0 | rule=5 |
| `vtiger7.vtiger_inventoryproductrel.productid` | import | 1176 | 1176 | 1173 | 1173 | 0 | 0 | 3 | 0 | rule=5, вне границ: empty |
| `vtiger7.vtiger_inventoryproductrel.purchase_cost` | import | 1176 | 0 | 1173 | 1173 | 0 | 0 | 3 | 0 | rule=5 |
| `vtiger7.vtiger_inventoryproductrel.quantity` | import | 1176 | 1176 | 1173 | 1173 | 0 | 0 | 3 | 0 | rule=5, вне границ: empty |
| `vtiger7.vtiger_inventoryproductrel.sequence_no` | import | 1176 | 1176 | 1173 | 1173 | 0 | 0 | 3 | 0 | rule=5, вне границ: transfer |
| `vtiger7.vtiger_inventoryproductrel.tax1` | import | 252 | 250 | 252 | 252 | 0 | 0 | 0 | 0 | rule=5, вне границ: empty |
| `vtiger7.vtiger_inventoryproductrel.tax2` | import | 252 | 0 | 252 | 0 | 0 | 0 | 0 | 0 | rule=5, вне границ: empty |
| `vtiger7.vtiger_inventoryproductrel.tax3` | import | 252 | 0 | 252 | 0 | 0 | 0 | 0 | 0 | rule=5, вне границ: empty |
| `vtiger7.vtiger_inventoryproductrel_seq.id` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_inventorytaxinfo.compoundon` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorytaxinfo.deleted` | configuration | 1 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorytaxinfo.method` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorytaxinfo.percentage` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorytaxinfo.regions` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorytaxinfo.taxid` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorytaxinfo.taxlabel` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorytaxinfo.taxname` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorytaxinfo.type` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_inventorytaxinfo_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_invoice.accountid` | import | 638 | 638 | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.adjustment` | import | 638 | 0 | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.balance` | import | 638 | 638 | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.compound_taxes_info` | import | 638 |  | 636 | 636 | 0 | 0 | 2 | 0 | rule=1, вне границ: archive |
| `vtiger7.vtiger_invoice.contactid` | import | 638 | 23 | 636 | 23 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.conversion_rate` | import | 638 | 638 | 636 | 0 | 0 | 0 | 2 | 0 | excluded=1 |
| `vtiger7.vtiger_invoice.currency_id` | import | 638 | 638 | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.customerno` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.discount_amount` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.duedate` | import | 536 |  | 536 | 536 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.exciseduty` | import | 638 | 0 | 636 | 0 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.invoice_no` | import | 636 |  | 636 | 636 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.invoicedate` | import | 637 |  | 635 | 635 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.invoiceid` | import | 638 | 638 | 636 | 0 | 0 | 0 | 2 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_invoice.invoicestatus` | import | 634 |  | 632 | 632 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.potential_id` | import | 638 |  | 636 | 429 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.pre_tax_total` | import | 638 | 638 | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.received` | import | 638 | 0 | 636 | 0 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.region_id` | import | 487 | 0 | 485 | 485 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.s_h_amount` | import | 638 | 0 | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.s_h_percent` | import | 638 | 0 | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.salescommission` | import | 638 | 0 | 636 | 0 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.salesorderid` | import | 27 | 27 | 27 | 27 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.sp_act_id` | import | 638 | 393 | 636 | 392 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.spcompany` | import | 638 |  | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.subject` | import | 638 |  | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.subtotal` | import | 638 | 638 | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.taxtype` | import | 638 |  | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.terms_conditions` | import | 638 |  | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice.total` | import | 638 | 638 | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoice_recurring_info.end_period` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoice_recurring_info.invoice_status` | import | 13 |  | 13 | 13 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoice_recurring_info.payment_duration` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoice_recurring_info.recurring_frequency` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoice_recurring_info.salesorderid` | import | 13 | 13 | 13 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_invoice_recurring_info.start_period` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoicebillads.bill_city` | import | 615 |  | 613 | 613 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoicebillads.bill_code` | import | 578 |  | 576 | 576 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoicebillads.bill_country` | import | 633 |  | 631 | 631 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoicebillads.bill_state` | import | 366 |  | 366 | 366 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoicebillads.bill_street` | import | 638 |  | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoicebillads.invoicebilladdressid` | import | 638 | 638 | 636 | 0 | 0 | 0 | 2 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_invoicecf.invoiceid` | import | 638 | 638 | 636 | 0 | 0 | 0 | 2 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_invoicecf.tax` | import | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoiceshipads.invoiceshipaddressid` | import | 638 | 638 | 636 | 0 | 0 | 0 | 2 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_invoiceshipads.ship_city` | import | 615 |  | 613 | 613 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoiceshipads.ship_code` | import | 566 |  | 564 | 564 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoiceshipads.ship_country` | import | 633 |  | 631 | 631 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoiceshipads.ship_pobox` | import | 40 |  | 40 | 40 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoiceshipads.ship_state` | import | 369 |  | 369 | 369 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_invoiceshipads.ship_street` | import | 638 |  | 636 | 636 | 0 | 0 | 2 | 0 | rule=1 |
| `vtiger7.vtiger_invoicestatus.invoicestatus` | configuration | 7 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_invoicestatus.invoicestatusid` | configuration | 7 | 7 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_invoicestatus.picklist_valueid` | configuration | 7 | 7 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_invoicestatus.presence` | configuration | 7 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_invoicestatus.sortorderid` | configuration | 7 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_invoicestatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_invoicestatushistory.historyid` | excluded | 589 | 589 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_invoicestatushistory.invoiceid` | excluded | 589 | 589 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_invoicestatushistory.invoicestatus` | excluded | 589 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_invoicestatushistory.lastmodified` | excluded | 589 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_invoicestatushistory.total` | excluded | 124 | 124 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_invoicestatushistory_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_jivosite.chatid` | import | 52 | 52 | 49 | 49 | 0 | 0 | 3 | 0 | rule=1 |
| `vtiger7.vtiger_jivosite.ipaddr` | import | 42 |  | 39 | 39 | 0 | 0 | 3 | 0 | rule=1 |
| `vtiger7.vtiger_jivosite.jivositeid` | import | 52 | 52 | 49 | 0 | 0 | 0 | 3 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_jivosite.messages` | import | 52 |  | 49 | 49 | 0 | 0 | 3 | 0 | rule=1 |
| `vtiger7.vtiger_jivosite.relatedleads` | import | 52 |  | 49 | 49 | 0 | 0 | 3 | 0 | rule=1 |
| `vtiger7.vtiger_jivosite.widgetid` | import | 52 |  | 49 | 49 | 0 | 0 | 3 | 0 | rule=1 |
| `vtiger7.vtiger_jivositecf.jivositeid` | import | 52 | 52 | 49 | 0 | 0 | 0 | 3 | 0 | excluded=1, вне границ: key |
| `vtiger7.vtiger_jvmes.agentid` | import | 272 |  | 267 | 267 | 0 | 0 | 5 | 0 | rule=1 |
| `vtiger7.vtiger_jvmes.datemes` | import | 272 |  | 267 | 267 | 0 | 0 | 5 | 0 | rule=1 |
| `vtiger7.vtiger_jvmes.jvmesid` | import | 272 | 272 | 267 | 0 | 0 | 0 | 5 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_jvmes.message` | import | 272 |  | 267 | 267 | 0 | 0 | 5 | 0 | rule=1 |
| `vtiger7.vtiger_jvmes.relatedjivo` | import | 272 |  | 267 | 267 | 0 | 0 | 5 | 0 | rule=1 |
| `vtiger7.vtiger_jvmes.type` | import | 272 |  | 267 | 267 | 0 | 0 | 5 | 0 | rule=1 |
| `vtiger7.vtiger_jvmescf.jvmesid` | import | 272 | 272 | 267 | 0 | 0 | 0 | 5 | 0 | excluded=1, вне границ: key |
| `vtiger7.vtiger_language.active` | excluded | 16 | 16 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_language.id` | excluded | 16 | 16 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_language.isdefault` | excluded | 16 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_language.label` | excluded | 16 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_language.lastupdated` | excluded | 16 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_language.name` | excluded | 16 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_language.prefix` | excluded | 16 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_language_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_lead_view.lead_view` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_lead_view.lead_viewid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_lead_view.presence` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_lead_view.sortorderid` | excluded | 3 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_lead_view_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_leadaddress.city` | import | 184 |  | 170 | 170 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_leadaddress.code` | import | 34 |  | 34 | 34 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leadaddress.country` | import | 130 |  | 114 | 114 | 0 | 0 | 16 | 0 | rule=1 |
| `vtiger7.vtiger_leadaddress.fax` | import | 19 |  | 19 | 19 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leadaddress.lane` | import | 122 |  | 122 | 122 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leadaddress.leadaddressid` | import | 241 | 241 | 225 | 0 | 0 | 0 | 16 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_leadaddress.leadaddresstype` | import | 241 |  | 225 | 0 | 0 | 0 | 16 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_leadaddress.mobile` | import | 87 |  | 87 | 87 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leadaddress.phone` | import | 183 |  | 178 | 178 | 0 | 0 | 5 | 0 | rule=1 |
| `vtiger7.vtiger_leadaddress.state` | import | 118 |  | 104 | 104 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.annualrevenue` | import | 241 | 1 | 225 | 1 | 0 | 0 | 16 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.assignleadchk` | import | 241 | 0 | 225 | 0 | 0 | 0 | 16 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_leaddetails.company` | import | 146 |  | 146 | 146 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.converted` | import | 241 | 5 | 225 | 5 | 0 | 0 | 16 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_leaddetails.designation` | import | 92 |  | 92 | 92 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.email` | import | 182 |  | 176 | 176 | 0 | 0 | 6 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.emailoptout` | import | 241 |  | 225 | 0 | 0 | 0 | 16 | 0 | empty=1 |
| `vtiger7.vtiger_leaddetails.firstname` | import | 149 |  | 149 | 149 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.industry` | import | 90 |  | 90 | 90 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.lastname` | import | 241 |  | 225 | 225 | 0 | 0 | 16 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.lead_no` | import | 241 |  | 225 | 225 | 0 | 0 | 16 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.leadid` | import | 241 | 241 | 225 | 0 | 0 | 0 | 16 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_leaddetails.leadsource` | import | 177 |  | 163 | 163 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.leadstatus` | import | 80 |  | 80 | 80 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.noofemployees` | import | 241 | 19 | 225 | 19 | 0 | 0 | 16 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.rating` | import | 36 |  | 36 | 36 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.salutation` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leaddetails.secondaryemail` | import | 8 |  | 8 | 8 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leadscf.cf_1107` | import | 187 |  | 187 | 187 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leadscf.cf_1165` | import | 68 | 52 | 52 | 52 | 0 | 0 | 16 | 0 | rule=1 |
| `vtiger7.vtiger_leadscf.leadid` | import | 241 | 241 | 225 | 0 | 0 | 0 | 16 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_leadscf.vk_url` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_leadsource.leadsource` | configuration | 23 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadsource.leadsourceid` | configuration | 23 | 23 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadsource.picklist_valueid` | configuration | 23 | 23 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadsource.presence` | configuration | 23 | 23 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadsource.sortorderid` | configuration | 23 | 23 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadsource_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_leadstatus.leadstatus` | configuration | 20 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadstatus.leadstatusid` | configuration | 20 | 20 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadstatus.picklist_valueid` | configuration | 20 | 20 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadstatus.presence` | configuration | 20 | 20 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadstatus.sortorderid` | configuration | 20 | 20 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_leadstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_leadsubdetails.callornot` | import | 241 | 0 | 225 | 0 | 0 | 0 | 16 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_leadsubdetails.empct` | import | 241 | 0 | 225 | 0 | 0 | 0 | 16 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_leadsubdetails.leadsubscriptionid` | import | 241 | 241 | 225 | 0 | 0 | 0 | 16 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_leadsubdetails.readornot` | import | 241 | 0 | 225 | 0 | 0 | 0 | 16 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_leadsubdetails.website` | import | 63 |  | 63 | 63 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_links.handler` | excluded | 18 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.handler_class` | excluded | 18 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.handler_path` | excluded | 18 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.linkicon` | excluded | 12 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.linkid` | excluded | 121 | 121 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.linklabel` | excluded | 121 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.linktype` | excluded | 121 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.linkurl` | excluded | 119 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.parent_link` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.sequence` | excluded | 120 | 44 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links.tabid` | excluded | 121 | 115 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_links_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_loginhistory.login_id` | excluded | 1739 | 1739 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_loginhistory.login_time` | excluded | 1739 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_loginhistory.logout_time` | excluded | 1739 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_loginhistory.status` | excluded | 1739 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_loginhistory.user_ip` | excluded | 1739 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_loginhistory.user_name` | excluded | 1739 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.account_id` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.account_name` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.box_refresh` | excluded | 3 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.display_name` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.int_mailer` | excluded | 3 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.mail_password` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.mail_protocol` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.mail_servername` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.mail_username` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.mails_per_page` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.sent_folder` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.set_default` | excluded | 3 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.sslmeth` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.ssltype` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.status` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mail_accounts.user_id` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailattachments.aname` | excluded | 34 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailattachments.attachid` | excluded | 34 | 34 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailattachments.cid` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailattachments.lastsavedtime` | excluded | 34 | 34 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailattachments.muid` | excluded | 34 | 34 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailattachments.path` | excluded | 34 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailattachments.userid` | excluded | 34 | 34 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.lastsavedtime` | excluded | 41 | 41 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mbcc` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mbody` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mbodyparsed` | excluded | 41 | 41 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mcc` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mcharset` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mdate` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mfolder` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mfrom` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mhtmlmessage` | excluded | 41 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.misbodyhtml` | excluded | 41 | 26 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mplainmessage` | excluded | 41 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.msubject` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.mto` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.muid` | excluded | 41 | 41 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.muniqueid` | excluded | 41 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrecord.userid` | excluded | 41 | 41 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrel.crmid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrel.emailid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailmanager_mailrel.mailuid` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailscanner_ids.crmid` | excluded | 23 | 23 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mailscanner_ids.messageid` | excluded | 23 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_manufacturer.manufacturer` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_manufacturer.manufacturerid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_manufacturer.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_manufacturer.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_manufacturer.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_manufacturer_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mobile_alerts.deleted` | excluded | 7 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mobile_alerts.handler_class` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mobile_alerts.handler_path` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_mobile_alerts.id` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modcomments.commentcontent` | import | 78 |  | 78 | 78 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_modcomments.customer` | import | 78 | 1 | 78 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_modcomments.filename` | import | 77 |  | 77 | 2 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_modcomments.is_private` | import | 78 | 0 | 78 | 0 | 0 | 0 | 0 | 0 | empty=1 |
| `vtiger7.vtiger_modcomments.modcommentsid` | import | 78 | 78 | 78 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_modcomments.parent_comments` | import | 78 | 0 | 78 | 0 | 0 | 0 | 0 | 0 | empty=1 |
| `vtiger7.vtiger_modcomments.related_email_id` | import | 78 | 0 | 78 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_modcomments.related_to` | import | 78 | 78 | 78 | 78 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_modcomments.userid` | import | 78 | 77 | 78 | 77 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_modcommentscf.modcommentsid` | import | 78 | 78 | 78 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_modentity_num.active` | excluded | 28 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modentity_num.cur_id` | excluded | 28 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modentity_num.num_id` | excluded | 28 | 28 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modentity_num.prefix` | excluded | 25 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modentity_num.semodule` | excluded | 28 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modentity_num.start_id` | excluded | 28 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modentity_num_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_basic.changedon` | excluded | 9724 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_basic.crmid` | excluded | 10334 | 10334 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_basic.id` | excluded | 10334 | 10334 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_basic.module` | excluded | 10334 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_basic.status` | excluded | 10334 | 8679 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_basic.whodid` | excluded | 10334 | 10334 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_basic_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_detail.fieldname` | excluded | 110678 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_detail.id` | excluded | 110678 | 110678 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_detail.postvalue` | excluded | 110562 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_detail.prevalue` | excluded | 2169 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_relations.changedon` | excluded | 3006 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_relations.id` | excluded | 3006 | 3006 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_relations.targetid` | excluded | 3006 | 3006 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_relations.targetmodule` | excluded | 3006 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_tabs.tabid` | excluded | 94 | 94 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_modtracker_tabs.visible` | excluded | 94 | 93 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_module_dashboard_widgets.dashboardtabid` | excluded | 19 | 19 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_module_dashboard_widgets.data` | excluded | 15 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_module_dashboard_widgets.filterid` | excluded | 5 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_module_dashboard_widgets.id` | excluded | 19 | 19 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_module_dashboard_widgets.linkid` | excluded | 19 | 19 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_module_dashboard_widgets.position` | excluded | 19 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_module_dashboard_widgets.title` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_module_dashboard_widgets.userid` | excluded | 19 | 19 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_msg_type.msg_type` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_msg_type.msg_typeid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_msg_type.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_msg_type.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_msg_type.sortorderid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_msg_type_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_no_of_currency_decimals.no_of_currency_decimals` | excluded | 6 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_no_of_currency_decimals.no_of_currency_decimalsid` | excluded | 6 | 6 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_no_of_currency_decimals.presence` | excluded | 6 | 6 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_no_of_currency_decimals.sortorderid` | excluded | 6 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_no_of_currency_decimals_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notes.filedownloadcount` | import | 39 | 38 | 39 | 38 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_notes.filelocationtype` | import | 227 |  | 215 | 212 | 0 | 0 | 12 | 0 | rule=1 |
| `vtiger7.vtiger_notes.filename` | import | 227 |  | 215 | 215 | 0 | 0 | 12 | 0 | rule=1 |
| `vtiger7.vtiger_notes.filesize` | import | 227 | 202 | 215 | 202 | 0 | 0 | 12 | 0 | rule=1 |
| `vtiger7.vtiger_notes.filestatus` | import | 227 | 226 | 215 | 215 | 0 | 0 | 12 | 0 | rule=1 |
| `vtiger7.vtiger_notes.filetype` | import | 202 |  | 202 | 202 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_notes.fileversion` | import | 13 |  | 3 | 3 | 0 | 0 | 10 | 0 | rule=1 |
| `vtiger7.vtiger_notes.folderid` | import | 227 | 227 | 215 | 215 | 0 | 0 | 12 | 0 | rule=1 |
| `vtiger7.vtiger_notes.note_no` | import | 227 |  | 215 | 215 | 0 | 0 | 12 | 0 | rule=1 |
| `vtiger7.vtiger_notes.notecontent` | import | 14 |  | 4 | 4 | 0 | 0 | 10 | 0 | rule=1 |
| `vtiger7.vtiger_notes.notesid` | import | 227 | 227 | 215 | 0 | 0 | 0 | 12 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_notes.title` | import | 227 |  | 215 | 215 | 0 | 0 | 12 | 0 | rule=1 |
| `vtiger7.vtiger_notescf.cf_for_field` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_notescf.notesid` | import | 227 | 227 | 215 | 0 | 0 | 0 | 12 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_notification_status.notification_status` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_notification_status.notification_statusid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_notification_status.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_notification_status.sortorderid` | configuration | 2 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_notification_status_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notifications.notification_status` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notifications.notificationid` | key | 1 | 1 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_notifications.related_to` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notificationscf.notificationid` | key | 1 | 1 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_notificationscheduler.active` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notificationscheduler.label` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notificationscheduler.notificationbody` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notificationscheduler.notificationsubject` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notificationscheduler.schedulednotificationid` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notificationscheduler.schedulednotificationname` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notificationscheduler.type` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_notificationscheduler_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_opportunity_type.opportunity_type` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_opportunity_type.opptypeid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_opportunity_type.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_opportunity_type.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_opportunity_type.sortorderid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_opportunity_type_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_org_share_action2tab.share_action_id` | excluded | 156 | 117 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_org_share_action2tab.tabid` | excluded | 156 | 156 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_org_share_action_mapping.share_action_id` | excluded | 8 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_org_share_action_mapping.share_action_name` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_organizationdetails.address` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.bankaccount` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.bankid` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.bankname` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.bookkeeper` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.city` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.code` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.company` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.corraccount` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.country` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.director` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.entrepreneur` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.entrepreneurreg` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.fax` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.inn` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.kpp` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.logoname` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.okpo` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.organization_id` | import | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_organizationdetails.organizationname` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.phone` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.state` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails.website` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_organizationdetails_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_othereventduration.othereventduration` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_othereventduration.othereventdurationid` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_othereventduration.presence` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_othereventduration.sortorderid` | excluded | 5 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_othereventduration_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_parenttab.parenttab_label` | excluded | 8 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_parenttab.parenttabid` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_parenttab.sequence` | excluded | 8 | 8 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_parenttab.visible` | excluded | 8 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_parenttabrel.parenttabid` | excluded | 95 | 95 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_parenttabrel.sequence` | excluded | 95 | 95 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_parenttabrel.tabid` | excluded | 95 | 95 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pay_type.pay_type` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_pay_type.pay_typeid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_pay_type.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_pay_type.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_pay_type.sortorderid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_pay_type_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_payment_duration.payment_duration` | configuration | 5 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_payment_duration.payment_duration_id` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_payment_duration.presence` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_payment_duration.sortorderid` | configuration | 5 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_payment_duration_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pbxmanager.billduration` | import | 1116 | 774 | 1116 | 907 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.callstatus` | import | 1116 |  | 1116 | 907 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.customer` | import | 36 |  | 36 | 13 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.customernumber` | import | 1116 |  | 1116 | 907 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.customertype` | import | 36 |  | 36 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_pbxmanager.direction` | import | 1116 |  | 1116 | 907 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.endtime` | import | 1113 |  | 1113 | 907 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.gateway` | import | 1116 |  | 1116 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_pbxmanager.incominglinename` | import | 921 |  | 921 | 725 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.pbxmanagerid` | import | 1116 | 1116 | 1116 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_pbxmanager.recordingurl` | import | 1033 |  | 1033 | 902 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.sourceuuid` | import | 1116 |  | 1116 | 907 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.sp_is_local_cached` | import | 1116 | 0 | 1116 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_pbxmanager.starttime` | import | 1116 |  | 1116 | 907 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.totalduration` | import | 1116 | 1072 | 1116 | 907 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager.user` | import | 1116 |  | 1116 | 907 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_pbxmanager_gateway.gateway` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pbxmanager_gateway.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pbxmanager_gateway.parameters` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pbxmanager_phonelookup.crmid` | excluded | 304 | 304 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pbxmanager_phonelookup.fieldname` | excluded | 304 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pbxmanager_phonelookup.fnumber` | excluded | 304 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pbxmanager_phonelookup.rnumber` | excluded | 304 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pbxmanager_phonelookup.setype` | excluded | 304 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_pbxmanagercf.pbxmanagerid` | key | 1116 | 1116 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_picklist.name` | excluded | 60 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_picklist.picklistid` | excluded | 60 | 60 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_picklist_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_picklistvalues_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_portal.createdtime` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_portal.portalid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_portal.portalname` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_portal.portalurl` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_portal.sequence` | excluded | 2 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_portal.setdefault` | excluded | 2 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_portal_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_postatus.picklist_valueid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_postatus.postatus` | configuration | 5 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_postatus.postatusid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_postatus.presence` | configuration | 5 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_postatus.sortorderid` | configuration | 5 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_postatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_potential.amount` | import | 156 | 153 | 156 | 156 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.campaignid` | import | 156 | 0 | 156 | 0 | 0 | 0 | 0 | 0 | empty=1 |
| `vtiger7.vtiger_potential.closingdate` | import | 156 |  | 156 | 156 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.contact_id` | import | 156 | 47 | 156 | 47 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.converted` | import | 156 | 5 | 156 | 156 | 0 | 0 | 0 | 0 | rule=1, вне границ: archive |
| `vtiger7.vtiger_potential.forecast_amount` | import | 156 | 12 | 156 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_potential.forecastcategory` | import | 156 | 0 | 156 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_potential.isconvertedfromlead` | import | 156 |  | 156 | 156 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.leadsource` | import | 77 |  | 77 | 77 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.nextstep` | import | 4 |  | 4 | 4 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.outcomeanalysis` | import | 156 | 0 | 156 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_potential.potential_no` | import | 156 |  | 156 | 156 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.potentialid` | import | 156 | 156 | 156 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_potential.potentialname` | import | 156 |  | 156 | 156 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.potentialtype` | import | 59 |  | 59 | 59 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.private` | import | 156 | 0 | 156 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_potential.probability` | import | 156 | 13 | 156 | 156 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.related_to` | import | 156 | 146 | 156 | 146 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.runtimefee` | import | 156 | 0 | 156 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_potential.sales_stage` | import | 156 |  | 156 | 156 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potential.spcompany` | import | 153 |  | 153 | 153 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_potentialscf.potentialid` | key | 156 | 156 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_potstagehistory.amount` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_potstagehistory.closedate` | excluded | 9 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_potstagehistory.expectedrevenue` | excluded | 9 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_potstagehistory.historyid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_potstagehistory.lastmodified` | excluded | 9 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_potstagehistory.potentialid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_potstagehistory.probability` | excluded | 9 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_potstagehistory.stage` | excluded | 9 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_productcategory.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_productcategory.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_productcategory.productcategory` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_productcategory.productcategoryid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_productcategory.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_productcategory_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_productcf.productid` | import | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: key |
| `vtiger7.vtiger_productcurrencyrel.actual_price` | excluded | 27 | 25 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_productcurrencyrel.converted_price` | excluded | 27 | 25 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_productcurrencyrel.currencyid` | excluded | 27 | 27 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_productcurrencyrel.productid` | excluded | 27 | 27 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_products.commissionrate` | import | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_products.currency_id` | import | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_products.discontinued` | import | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_products.is_subproducts_viewable` | import | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_products.product_no` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_products.productcode` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_products.productid` | import | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_products.productname` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_products.purchase_cost` | import | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | empty=1 |
| `vtiger7.vtiger_products.qty_per_unit` | import | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_products.qtyindemand` | import | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | empty=1 |
| `vtiger7.vtiger_products.qtyinstock` | import | 3 | 1 | 3 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_products.reorderlevel` | import | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | empty=1 |
| `vtiger7.vtiger_products.unit_price` | import | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_products.usageunit` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_products.vendor_id` | import | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | empty=1 |
| `vtiger7.vtiger_profile.description` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile.directly_related_to_role` | excluded | 11 | 4 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile.profileid` | excluded | 11 | 11 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile.profilename` | excluded | 11 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2field.fieldid` | excluded | 12279 | 12279 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2field.profileid` | excluded | 12279 | 12279 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2field.readonly` | excluded | 12279 | 1009 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2field.tabid` | excluded | 12279 | 12279 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2field.visible` | excluded | 12279 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2globalpermissions.globalactionid` | excluded | 22 | 22 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2globalpermissions.globalactionpermission` | excluded | 22 | 20 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2globalpermissions.profileid` | excluded | 22 | 22 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2standardpermissions.operation` | excluded | 2091 | 1708 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2standardpermissions.permissions` | excluded | 2091 | 474 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2standardpermissions.profileid` | excluded | 2091 | 2091 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2standardpermissions.tabid` | excluded | 2091 | 2091 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2tab.permissions` | excluded | 800 | 123 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2tab.profileid` | excluded | 800 | 800 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2tab.tabid` | excluded | 800 | 800 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2utility.activityid` | excluded | 968 | 968 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2utility.permission` | excluded | 968 | 105 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2utility.profileid` | excluded | 968 | 968 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile2utility.tabid` | excluded | 968 | 968 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_profile_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_progress.picklist_valueid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_progress.presence` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_progress.progress` | configuration | 10 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_progress.progressid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_progress.sortorderid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_progress_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_project.actualenddate` | import | 33 |  | 33 | 33 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.isconvertedfrompotential` | import | 54 | 5 | 54 | 54 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.linktoaccountscontacts` | import | 53 |  | 53 | 53 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.potentialid` | import | 54 |  | 54 | 36 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.progress` | import | 47 |  | 47 | 47 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.project_no` | import | 54 |  | 54 | 54 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.projectid` | import | 54 | 54 | 54 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_project.projectname` | import | 54 |  | 54 | 54 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.projectpriority` | import | 47 |  | 47 | 47 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.projectstatus` | import | 50 |  | 50 | 50 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.projecttype` | import | 45 |  | 45 | 45 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.projecturl` | import | 2 |  | 2 | 2 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.startdate` | import | 54 |  | 54 | 54 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.targetbudget` | import | 51 |  | 51 | 51 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_project.targetenddate` | import | 49 |  | 49 | 49 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projectcf.projectid` | key | 54 | 54 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_projectmilestonetype.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectmilestonetype.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectmilestonetype.projectmilestonetype` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectmilestonetype.projectmilestonetypeid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectmilestonetype.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectmilestonetype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_projectpriority.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectpriority.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectpriority.projectpriority` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectpriority.projectpriorityid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectpriority.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectpriority_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_projectstatus.picklist_valueid` | configuration | 8 | 8 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectstatus.presence` | configuration | 8 | 8 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectstatus.projectstatus` | configuration | 8 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectstatus.projectstatusid` | configuration | 8 | 8 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectstatus.sortorderid` | configuration | 8 | 8 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projectstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_projecttask.enddate` | import | 468 |  | 468 | 468 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.projectid` | import | 493 |  | 493 | 493 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.projecttask_no` | import | 493 |  | 493 | 493 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.projecttaskhours` | import | 493 | 476 | 493 | 493 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.projecttaskid` | import | 493 | 493 | 493 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_projecttask.projecttaskname` | import | 493 |  | 493 | 493 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.projecttasknumber` | import | 493 | 2 | 493 | 493 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.projecttaskpriority` | import | 480 |  | 480 | 480 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.projecttaskprogress` | import | 488 |  | 488 | 488 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.projecttaskstatus` | import | 492 |  | 492 | 492 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.projecttasktype` | import | 489 |  | 489 | 489 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask.startdate` | import | 490 |  | 490 | 490 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttask_status_color.defaultcolor` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_projecttask_status_color.status` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_projecttaskcf.cf_1320` | import | 257 |  | 257 | 257 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttaskcf.cf_1354` | import | 493 |  | 493 | 493 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_projecttaskcf.projecttaskid` | import | 493 | 493 | 493 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_projecttaskpriority.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskpriority.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskpriority.projecttaskpriority` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskpriority.projecttaskpriorityid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskpriority.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskpriority_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_projecttaskprogress.picklist_valueid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskprogress.presence` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskprogress.projecttaskprogress` | configuration | 10 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskprogress.projecttaskprogressid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskprogress.sortorderid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskprogress_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_projecttaskstatus.picklist_valueid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskstatus.presence` | configuration | 5 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskstatus.projecttaskstatus` | configuration | 5 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskstatus.projecttaskstatusid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskstatus.sortorderid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttaskstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_projecttasktype.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttasktype.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttasktype.projecttasktype` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttasktype.projecttasktypeid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttasktype.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttasktype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_projecttype.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttype.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttype.projecttype` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttype.projecttypeid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttype.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_projecttype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotes.accountid` | import | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.adjustment` | import | 24 | 0 | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.compound_taxes_info` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1, вне границ: archive |
| `vtiger7.vtiger_quotes.contactid` | import | 6 | 6 | 6 | 6 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.conversion_rate` | import | 24 | 24 | 24 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_quotes.currency_id` | import | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.inventorymanager` | import | 24 | 23 | 24 | 23 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.potentialid` | import | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.pre_tax_total` | import | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.quote_no` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.quoteid` | import | 24 | 24 | 24 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_quotes.quotestage` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.region_id` | import | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.s_h_amount` | import | 24 | 0 | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.s_h_percent` | import | 24 | 0 | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.spcompany` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.subject` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.subtotal` | import | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.taxtype` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.terms_conditions` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.total` | import | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotes.validtill` | import | 15 |  | 15 | 15 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesbillads.bill_city` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesbillads.bill_code` | import | 21 |  | 21 | 21 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesbillads.bill_country` | import | 20 |  | 20 | 20 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesbillads.bill_state` | import | 19 |  | 19 | 19 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesbillads.bill_street` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesbillads.quotebilladdressid` | import | 24 | 24 | 24 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_quotescf.quoteid` | import | 24 | 24 | 24 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_quotesshipads.quoteshipaddressid` | import | 24 | 24 | 24 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_quotesshipads.ship_city` | import | 23 |  | 23 | 23 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesshipads.ship_code` | import | 21 |  | 21 | 21 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesshipads.ship_country` | import | 20 |  | 20 | 20 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesshipads.ship_state` | import | 18 |  | 18 | 18 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotesshipads.ship_street` | import | 24 |  | 24 | 24 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_quotestage.picklist_valueid` | configuration | 9 | 9 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_quotestage.presence` | configuration | 9 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_quotestage.quotestage` | configuration | 9 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_quotestage.quotestageid` | configuration | 9 | 9 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_quotestage.sortorderid` | configuration | 9 | 8 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_quotestage_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.anwidget` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.body` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.content` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.created` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.createnewrecords` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.deleted` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.filename` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.is_active` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.module` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool.updated` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_histories.body` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_histories.created` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_histories.deleted` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_histories.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_histories.template_id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_histories.updated` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_settings.background` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_settings.created` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_settings.expire_in_days` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_settings.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_settings.label_accept` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_settings.label_decline` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_settings.template_id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_quotingtool_settings.updated` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_rating.picklist_valueid` | configuration | 9 | 9 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_rating.presence` | configuration | 9 | 9 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_rating.rating` | configuration | 9 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_rating.rating_id` | configuration | 9 | 9 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_rating.sortorderid` | configuration | 9 | 9 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_rating_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_recurring_frequency.presence` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_recurring_frequency.recurring_frequency` | configuration | 6 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_recurring_frequency.recurring_frequency_id` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_recurring_frequency.sortorderid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_recurring_frequency_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_recurringtype.presence` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_recurringtype.recurringeventid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_recurringtype.recurringtype` | configuration | 4 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_recurringtype.sortorderid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_recurringtype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.actions` | excluded | 159 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.label` | excluded | 249 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.name` | excluded | 249 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.presence` | excluded | 249 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.related_tabid` | excluded | 249 | 240 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.relation_id` | excluded | 249 | 249 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.relationfieldid` | excluded | 148 | 102 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.relationtype` | excluded | 181 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.sequence` | excluded | 249 | 248 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists.tabid` | excluded | 249 | 249 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists_rb.action` | excluded | 28 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists_rb.entityid` | excluded | 28 | 28 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists_rb.ref_column` | excluded | 28 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists_rb.rel_column` | excluded | 28 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists_rb.rel_table` | excluded | 28 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists_rb.related_crm_ids` | excluded | 20 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relatedlists_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_relcriteria.column_condition` | module_code | 13 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria.columnindex` | module_code | 15 | 3 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria.columnname` | module_code | 15 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria.comparator` | module_code | 15 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria.groupid` | module_code | 15 | 15 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria.queryid` | module_code | 15 | 15 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria.value` | module_code | 8 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria_grouping.condition_expression` | module_code | 13 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria_grouping.group_condition` | module_code | 3 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria_grouping.groupid` | module_code | 13 | 13 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_relcriteria_grouping.queryid` | module_code | 13 | 13 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reminder_interval.presence` | excluded | 15 | 15 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_reminder_interval.reminder_interval` | excluded | 15 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_reminder_interval.reminder_intervalid` | excluded | 15 | 15 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_reminder_interval.sortorderid` | excluded | 15 | 15 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_reminder_interval_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_report.category` | module_code | 28 | 28 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.customizable` | module_code | 28 | 28 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.description` | module_code | 27 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.folderid` | module_code | 28 | 28 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.owner` | module_code | 28 | 28 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.queryid` | module_code | 28 | 28 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.reportid` | module_code | 28 | 28 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.reportname` | module_code | 28 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.reporttype` | module_code | 28 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.sharingtype` | module_code | 28 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_report.state` | module_code | 28 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportdatefilter.datecolumnname` | module_code | 2 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportdatefilter.datefilter` | module_code | 2 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportdatefilter.datefilterid` | module_code | 2 | 2 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportdatefilter.enddate` | module_code | 2 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportdatefilter.startdate` | module_code | 2 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportfilters.filterid` | module_code | 3 | 3 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportfilters.name` | module_code | 3 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportfolder.description` | module_code | 13 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportfolder.folderid` | module_code | 13 | 13 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportfolder.foldername` | module_code | 13 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportfolder.state` | module_code | 13 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportmodules.primarymodule` | module_code | 28 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportmodules.reportmodulesid` | module_code | 28 | 28 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportmodules.secondarymodules` | module_code | 10 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportsortcol.columnname` | module_code | 13 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportsortcol.reportid` | module_code | 13 | 13 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportsortcol.sortcolid` | module_code | 13 | 10 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportsortcol.sortorder` | module_code | 4 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportsummary.columnname` | module_code | 8 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportsummary.reportsummaryid` | module_code | 8 | 8 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_reportsummary.summarytype` | module_code | 8 | 6 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_role.allowassignedrecordsto` | excluded | 11 | 11 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role.depth` | excluded | 11 | 10 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role.parentrole` | excluded | 11 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role.roleid` | excluded | 11 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role.rolename` | excluded | 11 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role2picklist.picklistid` | excluded | 4407 | 4407 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role2picklist.picklistvalueid` | excluded | 4407 | 4407 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role2picklist.roleid` | excluded | 4407 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role2picklist.sortid` | excluded | 4407 | 4088 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role2profile.profileid` | excluded | 11 | 11 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role2profile.roleid` | excluded | 11 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_role_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_room_type.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_room_type.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_room_type.room_type` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_room_type.room_typeid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_room_type.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_room_type_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_rowheight.presence` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_rowheight.rowheight` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_rowheight.rowheightid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_rowheight.sortorderid` | excluded | 3 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_rowheight_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sales_stage.picklist_valueid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sales_stage.presence` | configuration | 10 | 8 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sales_stage.sales_stage` | configuration | 10 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sales_stage.sales_stage_id` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sales_stage.sortorderid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sales_stage_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_salesmanactivityrel.activityid` | import | 186 | 186 | 86 | 0 | 0 | 0 | 0 | 100 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_salesmanactivityrel.smid` | import | 186 | 186 | 86 | 0 | 0 | 0 | 0 | 100 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_salesmanattachmentsrel.attachmentsid` | import | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_salesmanattachmentsrel.smid` | import | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_salesorder.accountid` | import | 14 | 14 | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.adjustment` | import | 14 | 0 | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.carrier` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.compound_taxes_info` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1, вне границ: archive |
| `vtiger7.vtiger_salesorder.contactid` | import | 14 | 8 | 14 | 8 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.conversion_rate` | import | 14 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_salesorder.currency_id` | import | 14 | 14 | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.duedate` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.enable_recurring` | import | 14 | 3 | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.exciseduty` | import | 14 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.fromsite` | import | 14 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.pending` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.potentialid` | import | 14 | 12 | 14 | 12 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.pre_tax_total` | import | 14 | 14 | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.quoteid` | import | 14 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.region_id` | import | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.s_h_amount` | import | 14 | 0 | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.s_h_percent` | import | 14 | 0 | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.salescommission` | import | 14 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.salesorder_no` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.salesorderid` | import | 14 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_salesorder.sostatus` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.spcompany` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.subject` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.subtotal` | import | 14 | 14 | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.taxtype` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.terms_conditions` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesorder.total` | import | 14 | 14 | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_salesordercf.salesorderid` | import | 14 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_salutationtype.picklist_valueid` | configuration | 13 | 13 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_salutationtype.presence` | configuration | 13 | 13 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_salutationtype.salutationid` | configuration | 13 | 13 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_salutationtype.salutationtype` | configuration | 13 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_salutationtype.sortorderid` | configuration | 13 | 13 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_salutationtype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_seactivityrel.activityid` | import | 260 | 260 | 109 | 0 | 0 | 0 | 0 | 151 | relation=1, вне границ: key |
| `vtiger7.vtiger_seactivityrel.crmid` | import | 260 | 260 | 109 | 0 | 0 | 0 | 0 | 151 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_seactivityrel_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_seattachmentsrel.attachmentsid` | import | 203 | 203 | 203 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_seattachmentsrel.crmid` | import | 203 | 203 | 203 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_selectcolumn.columnindex` | module_code | 172 | 144 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_selectcolumn.columnname` | module_code | 172 |  |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_selectcolumn.queryid` | module_code | 172 | 172 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_selectquery.numofobjects` | module_code | 28 | 0 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_selectquery.queryid` | module_code | 28 | 28 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_selectquery.startindex` | module_code | 28 | 0 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_selectquery_seq.id` | module_code | 1 | 1 |  |  |  |  |  |  | module_code |
| `vtiger7.vtiger_senotesrel.crmid` | import | 233 | 233 | 221 | 0 | 0 | 0 | 0 | 12 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_senotesrel.notesid` | import | 233 | 233 | 221 | 0 | 0 | 0 | 0 | 12 | relation=1, вне границ: transfer |
| `vtiger7.vtiger_service.commissionrate` | import | 25 | 4 | 25 | 4 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.currency_id` | import | 25 | 25 | 25 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_service.discontinued` | import | 25 | 25 | 25 | 25 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.purchase_cost` | import | 25 | 0 | 25 | 0 | 0 | 0 | 0 | 0 | empty=1 |
| `vtiger7.vtiger_service.qty_per_unit` | import | 25 | 15 | 25 | 25 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.sales_end_date` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.sales_start_date` | import | 11 |  | 11 | 11 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.service_no` | import | 25 |  | 25 | 25 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.service_usageunit` | import | 19 |  | 19 | 19 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.servicecategory` | import | 15 |  | 15 | 15 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.serviceid` | import | 25 | 25 | 25 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_service.servicename` | import | 25 |  | 25 | 25 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.start_date` | import | 5 |  | 5 | 5 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.unit_price` | import | 25 | 22 | 25 | 25 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service.website` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_service_usageunit.picklist_valueid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_service_usageunit.presence` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_service_usageunit.service_usageunit` | configuration | 6 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_service_usageunit.service_usageunitid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_service_usageunit.sortorderid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_service_usageunit_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_servicecategory.picklist_valueid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_servicecategory.presence` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_servicecategory.servicecategory` | configuration | 10 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_servicecategory.servicecategoryid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_servicecategory.sortorderid` | configuration | 10 | 10 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_servicecategory_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_servicecf.cf_billable_time_tracker` | import | 25 |  | 25 | 25 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecf.serviceid` | import | 25 | 25 | 25 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_servicecontracts.contract_no` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.contract_status` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.contract_type` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.due_date` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.planned_duration` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.priority` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.sc_related_to` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.servicecontractsid` | import | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_servicecontracts.start_date` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.subject` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.total_units` | import | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.tracking_unit` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontracts.used_units` | import | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_servicecontractscf.servicecontractsid` | import | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: key |
| `vtiger7.vtiger_settings_blocks.blockid` | excluded | 10 | 10 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_blocks.label` | excluded | 10 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_blocks.sequence` | excluded | 10 | 10 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_blocks_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field.active` | excluded | 46 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field.blockid` | excluded | 46 | 46 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field.description` | excluded | 43 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field.fieldid` | excluded | 46 | 46 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field.iconpath` | excluded | 33 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field.linkto` | excluded | 46 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field.name` | excluded | 46 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field.pinned` | excluded | 46 | 11 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field.sequence` | excluded | 46 | 46 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_settings_field_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_shippingtaxinfo.compoundon` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_shippingtaxinfo.deleted` | configuration | 1 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_shippingtaxinfo.method` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_shippingtaxinfo.percentage` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_shippingtaxinfo.regions` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_shippingtaxinfo.taxid` | configuration | 1 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_shippingtaxinfo.taxlabel` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_shippingtaxinfo.taxname` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_shippingtaxinfo.type` | configuration | 1 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_shippingtaxinfo_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_signedrecord_status.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_signedrecord_status.signedrecord_status` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_signedrecord_status.signedrecord_statusid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_signedrecord_status.sortorderid` | configuration | 2 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_signedrecord_status_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_signedrecord_type.color` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_signedrecord_type.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_signedrecord_type.signedrecord_type` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_signedrecord_type.signedrecord_typeid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_signedrecord_type.sortorderid` | configuration | 2 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_signedrecord_type_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sobillads.bill_city` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sobillads.bill_code` | import | 12 |  | 12 | 12 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sobillads.bill_country` | import | 11 |  | 11 | 11 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sobillads.bill_state` | import | 10 |  | 10 | 10 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sobillads.bill_street` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sobillads.sobilladdressid` | import | 14 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_soshipads.ship_city` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_soshipads.ship_code` | import | 12 |  | 12 | 12 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_soshipads.ship_country` | import | 11 |  | 11 | 11 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_soshipads.ship_state` | import | 10 |  | 10 | 10 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_soshipads.ship_street` | import | 14 |  | 14 | 14 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_soshipads.soshipaddressid` | import | 14 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_sostatus.picklist_valueid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sostatus.presence` | configuration | 6 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sostatus.sortorderid` | configuration | 6 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sostatus.sostatus` | configuration | 6 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sostatus.sostatusid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sostatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_act.accountid` | import | 405 | 405 | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.act_no` | import | 404 |  | 403 | 403 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.actdate` | import | 403 |  | 403 | 403 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.actid` | import | 405 | 405 | 404 | 0 | 0 | 0 | 1 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_sp_act.adjustment` | import | 405 | 0 | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.compound_taxes_info` | import | 405 |  | 404 | 404 | 0 | 0 | 1 | 0 | rule=1, вне границ: archive |
| `vtiger7.vtiger_sp_act.contactid` | import | 405 | 6 | 404 | 6 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.conversion_rate` | import | 405 | 405 | 404 | 0 | 0 | 0 | 1 | 0 | excluded=1 |
| `vtiger7.vtiger_sp_act.currency_id` | import | 405 | 405 | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.pre_tax_total` | import | 405 | 404 | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.region_id` | import | 405 | 0 | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.s_h_amount` | import | 405 | 0 | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.s_h_percent` | import | 405 | 0 | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.sp_actstatus` | import | 390 |  | 390 | 390 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.spcompany` | import | 405 |  | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.subject` | import | 405 |  | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.subtotal` | import | 405 | 404 | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.taxtype` | import | 405 |  | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_act.total` | import | 405 | 404 | 404 | 404 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actbillads.actbilladdressid` | import | 405 | 405 | 404 | 0 | 0 | 0 | 1 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_sp_actbillads.bill_city` | import | 404 |  | 404 | 404 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actbillads.bill_code` | import | 401 |  | 401 | 401 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actbillads.bill_country` | import | 403 |  | 403 | 403 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actbillads.bill_state` | import | 202 |  | 202 | 202 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actbillads.bill_street` | import | 404 |  | 404 | 404 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actcf.actid` | import | 405 | 405 | 404 | 0 | 0 | 0 | 1 | 0 | excluded=1, вне границ: key |
| `vtiger7.vtiger_sp_actshipads.actshipaddressid` | import | 405 | 405 | 404 | 0 | 0 | 0 | 1 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_sp_actshipads.ship_city` | import | 404 |  | 404 | 404 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actshipads.ship_code` | import | 401 |  | 401 | 401 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actshipads.ship_country` | import | 403 |  | 403 | 403 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actshipads.ship_pobox` | import | 40 |  | 40 | 40 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actshipads.ship_state` | import | 206 |  | 206 | 206 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actshipads.ship_street` | import | 404 |  | 404 | 404 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_actstatus.picklist_valueid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_actstatus.presence` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_actstatus.sortorderid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_actstatus.sp_actstatus` | configuration | 4 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_actstatus.sp_actstatusid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_actstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_actstatushistory.actid` | excluded | 51 | 51 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_actstatushistory.historyid` | excluded | 51 | 51 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_actstatushistory.lastmodified` | excluded | 51 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_actstatushistory.sp_actstatus` | excluded | 51 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_actstatushistory.total` | excluded | 16 | 16 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_actstatushistory_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_blocks_configuration_seq.id` | excluded | 1 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_callpopup.callid` | import | 210 | 210 | 210 | 204 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_callpopup.client_type` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_callpopup.comment` | import | 2 |  | 2 | 2 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_callpopup.firstname` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_callpopup.lastname` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_callpopup.popupid` | import | 210 | 210 | 210 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_sp_callpopup.status` | import | 210 | 210 | 210 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_sp_callpopup_last_call.last_call_id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_callpopupcf.popupid` | key | 210 | 210 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_sp_consignment.accountid` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.adjustment` | import | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.compound_taxes_info` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_sp_consignment.consignment_no` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.consignmentdate` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.consignmentid` | import | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_sp_consignment.contactid` | import | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.conversion_rate` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.currency_id` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.goods_consignment_no` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.has_goods_consignment` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.invoiceid` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.pre_tax_total` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.region_id` | import | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.s_h_amount` | import | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.s_h_percent` | import | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.spcompany` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.subject` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.subtotal` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.taxtype` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignment.total` | import | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentbillads.bill_city` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentbillads.bill_code` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentbillads.bill_country` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentbillads.bill_state` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentbillads.bill_street` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentbillads.consignmentbilladdressid` | import | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_sp_consignmentcf.consignmentid` | import | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: key |
| `vtiger7.vtiger_sp_consignmentshipads.consignmentshipaddressid` | import | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_sp_consignmentshipads.ship_city` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentshipads.ship_code` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentshipads.ship_country` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentshipads.ship_state` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentshipads.ship_street` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_sp_consignmentstatus.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_consignmentstatus.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_consignmentstatus.sortorderid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_consignmentstatus.sp_consignmentstatus` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_consignmentstatus.sp_consignmentstatusid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_sp_consignmentstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_convert_popup_mapping.accountfid` | excluded | 3 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_convert_popup_mapping.contactfid` | excluded | 3 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_convert_popup_mapping.editable` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_convert_popup_mapping.id` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_convert_popup_mapping.leadfid` | excluded | 3 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_convert_popup_mapping.popupfid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_socialconnector_providers.id` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_socialconnector_providers.provider_domen` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_socialconnector_providers.provider_name` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_socialconnector_settings.key` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_voip_default_provider.default_provider` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_voipintegration_options.name` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_voipintegration_options.value` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_voipintegration_settings.field_label` | excluded | 42 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_voipintegration_settings.field_name` | excluded | 42 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_voipintegration_settings.field_value` | excluded | 9 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_voipintegration_settings.id` | excluded | 42 | 42 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_sp_voipintegration_settings.provider_name` | excluded | 42 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_spcompany.picklist_valueid` | excluded | 2 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_spcompany.presence` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_spcompany.sortorderid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_spcompany.spcompany` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_spcompany.spcompanyid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_spcompany_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_spstatus.picklist_valueid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_spstatus.presence` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_spstatus.sortorderid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_spstatus.spstatus` | configuration | 4 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_spstatus.spstatusid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_spstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_start_hour.presence` | excluded | 24 | 24 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_start_hour.sortorderid` | excluded | 24 | 23 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_start_hour.start_hour` | excluded | 24 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_start_hour.start_hourid` | excluded | 24 | 24 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_start_hour_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_status.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_status.presence` | configuration | 2 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_status.status` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_status.statusid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_status_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.from_email_field` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.from_name` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.server` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.server_password` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.server_port` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.server_tls` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.server_type` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.server_username` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.smtp_auth` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems.use_mail_account` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_systems_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.allowduplicates` | excluded | 106 | 105 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.customized` | excluded | 106 | 62 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.isentitytype` | excluded | 106 | 44 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.issyncable` | excluded | 106 | 57 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.name` | excluded | 106 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.ownedby` | excluded | 106 | 11 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.parent` | excluded | 47 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.presence` | excluded | 106 | 46 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.source` | excluded | 47 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.sync_action_for_duplicates` | excluded | 106 | 106 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.tabid` | excluded | 106 | 106 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.tablabel` | excluded | 106 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.tabsequence` | excluded | 106 | 106 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.trial` | excluded | 106 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab.version` | excluded | 80 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab_info.prefname` | excluded | 146 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab_info.prefvalue` | excluded | 146 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tab_info.tabid` | excluded | 146 | 146 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_taskpriority.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskpriority.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskpriority.sortorderid` | configuration | 3 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskpriority.taskpriority` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskpriority.taskpriorityid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskpriority_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_taskstatus.picklist_valueid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskstatus.presence` | configuration | 6 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskstatus.sortorderid` | configuration | 6 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskstatus.taskstatus` | configuration | 6 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskstatus.taskstatusid` | configuration | 6 | 6 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taskstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_taxclass.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taxclass.sortorderid` | configuration | 2 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taxclass.taxclass` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taxclass.taxclassid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_taxclass_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ticketcategories.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketcategories.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketcategories.sortorderid` | configuration | 3 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketcategories.ticketcategories` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketcategories.ticketcategories_id` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketcategories_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ticketcf.from_portal` | import | 59 |  | 45 | 0 | 0 | 0 | 14 | 0 | excluded=1 |
| `vtiger7.vtiger_ticketcf.ticketid` | import | 59 | 59 | 45 | 0 | 0 | 0 | 14 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_ticketpriorities.picklist_valueid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketpriorities.presence` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketpriorities.sortorderid` | configuration | 4 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketpriorities.ticketpriorities` | configuration | 4 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketpriorities.ticketpriorities_id` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketpriorities_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ticketseverities.picklist_valueid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketseverities.presence` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketseverities.sortorderid` | configuration | 5 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketseverities.ticketseverities` | configuration | 5 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketseverities.ticketseverities_id` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketseverities_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ticketstatus.picklist_valueid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketstatus.presence` | configuration | 4 | 0 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketstatus.sortorderid` | configuration | 4 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketstatus.ticketstatus` | configuration | 4 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketstatus.ticketstatus_id` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_ticketstatus_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_time_zone.presence` | excluded | 97 | 97 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_time_zone.sortorderid` | excluded | 97 | 96 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_time_zone.time_zone` | excluded | 97 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_time_zone.time_zoneid` | excluded | 97 | 97 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_time_zone_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tmp_read_user_sharing_per.shareduserid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tmp_read_user_sharing_per.tabid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tmp_read_user_sharing_per.userid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tmp_write_user_sharing_per.shareduserid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tmp_write_user_sharing_per.tabid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tmp_write_user_sharing_per.userid` | excluded | 9 | 9 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_tracking_unit.picklist_valueid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tracking_unit.presence` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tracking_unit.sortorderid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tracking_unit.tracking_unit` | configuration | 3 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tracking_unit.tracking_unitid` | configuration | 3 | 3 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tracking_unit_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_troubletickets.category` | import | 40 |  | 28 | 28 | 0 | 0 | 12 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.contact_id` | import | 59 | 19 | 45 | 7 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.days` | import | 59 | 1 | 45 | 1 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.hours` | import | 59 | 20 | 45 | 18 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.parent_id` | import | 59 |  | 45 | 42 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.priority` | import | 59 |  | 45 | 45 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.product_id` | import | 59 |  | 45 | 45 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.severity` | import | 40 |  | 28 | 28 | 0 | 0 | 12 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.solution` | import | 23 |  | 22 | 22 | 0 | 0 | 1 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.status` | import | 59 |  | 45 | 45 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.ticket_no` | import | 59 |  | 45 | 45 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_troubletickets.ticketid` | import | 59 | 59 | 45 | 0 | 0 | 0 | 14 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_troubletickets.title` | import | 59 |  | 45 | 45 | 0 | 0 | 14 | 0 | rule=1 |
| `vtiger7.vtiger_tw_status.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tw_status.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tw_status.sortorderid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tw_status.tw_status` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tw_status.tw_statusid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_tw_status_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_type.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type.sortorderid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type.type` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type.typeid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type_payment.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type_payment.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type_payment.sortorderid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type_payment.type_payment` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type_payment.type_paymentid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_type_payment_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_type_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_usageunit.picklist_valueid` | configuration | 16 | 16 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_usageunit.presence` | configuration | 16 | 16 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_usageunit.sortorderid` | configuration | 16 | 15 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_usageunit.usageunit` | configuration | 16 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_usageunit.usageunitid` | configuration | 16 | 16 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_usageunit_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_user2role.roleid` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | relation=1, rule=1, вне границ: transfer |
| `vtiger7.vtiger_user2role.userid` | import | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 0 | key=1, relation=1, вне границ: key |
| `vtiger7.vtiger_user_module_preferences.default_cvid` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_user_module_preferences.tabid` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_user_module_preferences.userid` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_users.accesskey` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.activity_view` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.address_city` | import | 4 |  | 4 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.address_country` | import | 4 |  | 4 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.address_postalcode` | import | 4 |  | 4 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.address_state` | import | 4 |  | 4 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.address_street` | import | 4 |  | 4 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.cal_color` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_users.calendarsharedtype` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.callduration` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.confirm_password` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.crypt_type` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_users.currency_decimal_separator` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.currency_grouping_pattern` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.currency_grouping_separator` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.currency_id` | import | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.currency_symbol_placement` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.date_entered` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1, вне границ: transfer |
| `vtiger7.vtiger_users.date_format` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.dayoftheweek` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.default_record_view` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.defaultactivitytype` | import | 2 |  | 2 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.defaultcalendarview` | import | 2 |  | 2 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.defaulteventstatus` | import | 2 |  | 2 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.deleted` | import | 7 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_users.department` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.email1` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.end_hour` | import | 1 |  | 1 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.first_name` | import | 6 |  | 6 | 6 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.hidecompletedevents` | import | 7 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.hour_format` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.id` | import | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_users.imagename` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.internal_mailer` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.is_admin` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.is_owner` | import | 1 |  | 1 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.language` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.last_name` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.lead_view` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.leftpanelhide` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.no_of_currency_decimals` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.othereventduration` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.phone_crm_extension` | import | 5 |  | 5 | 5 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.phone_home` | import | 3 |  | 3 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.phone_mobile` | import | 5 |  | 5 | 5 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.phone_work` | import | 5 |  | 5 | 5 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.reminder_interval` | import | 2 |  | 2 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.rowheight` | import | 6 |  | 6 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.signature` | import | 2 |  | 2 | 2 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.start_hour` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.status` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.theme` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.time_zone` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.title` | import | 5 |  | 5 | 5 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.truncate_trailing_zeros` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users.user_hash` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1, вне границ: excluded |
| `vtiger7.vtiger_users.user_name` | import | 7 |  | 7 | 7 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_users.user_password` | import | 7 |  | 7 | 0 | 0 | 0 | 0 | 0 | excluded=1 |
| `vtiger7.vtiger_users2group.groupid` | import | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: excluded |
| `vtiger7.vtiger_users2group.userid` | import | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | relation=1, вне границ: excluded |
| `vtiger7.vtiger_users_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vendor.email` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_vendor.phone` | import | 1 |  | 1 | 1 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_vendor.vendor_no` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_vendor.vendorid` | import | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_vendor.vendorname` | import | 3 |  | 3 | 3 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_vendor.website` | import | 2 |  | 2 | 2 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_vendorcf.cf_1206` | import | 2 |  | 2 | 2 | 0 | 0 | 0 | 0 | rule=1 |
| `vtiger7.vtiger_vendorcf.vendorid` | import | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | key=1, вне границ: key |
| `vtiger7.vtiger_version.current_version` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_version.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_version.old_version` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_version_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_visibility.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_visibility.sortorderid` | configuration | 2 | 1 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_visibility.visibility` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_visibility.visibilityid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_visibility_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vk_status.picklist_valueid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vk_status.presence` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vk_status.sortorderid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vk_status.vk_status` | configuration | 2 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vk_status.vk_statusid` | configuration | 2 | 2 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vk_status_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteemailmarketing_status.presence` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vteemailmarketing_status.sortorderid` | configuration | 5 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vteemailmarketing_status.vteemailmarketing_status` | configuration | 5 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vteemailmarketing_status.vteemailmarketing_statusid` | configuration | 5 | 5 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vteemailmarketing_status_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.comment` | excluded | 271 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.discount_amount` | excluded | 286 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.discount_percent` | excluded | 286 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.image` | excluded | 286 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.level` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.listprice` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.margin` | excluded | 286 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.net_price` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.productid` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.purchase_cost` | excluded | 286 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.quantity` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.related_to` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.sequence` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.tax1` | excluded | 286 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.tax2` | excluded | 286 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.tax3` | excluded | 286 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.tax_total` | excluded | 286 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.total` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_vteitems.vteitemid` | key | 286 | 286 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_vteitemscf.vteitemid` | key | 286 | 286 |  |  |  |  |  |  | key |
| `vtiger7.vtiger_vtemailconverter_status.picklist_valueid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vtemailconverter_status.presence` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vtemailconverter_status.sortorderid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vtemailconverter_status.vtemailconverter_status` | configuration | 4 |  |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vtemailconverter_status.vtemailconverter_statusid` | configuration | 4 | 4 |  |  |  |  |  |  | configuration |
| `vtiger7.vtiger_vtemailconverter_status_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity.handler_class` | excluded | 55 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity.handler_path` | excluded | 55 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity.id` | excluded | 55 | 55 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity.ismodule` | excluded | 55 | 48 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity.name` | excluded | 55 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_fieldtype.field_name` | excluded | 10 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_fieldtype.fieldtype` | excluded | 10 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_fieldtype.fieldtypeid` | excluded | 10 | 10 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_fieldtype.table_name` | excluded | 10 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_fieldtype_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_name.entity_id` | excluded | 5 | 5 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_name.index_field` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_name.name_fields` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_name.table_name` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_referencetype.fieldtypeid` | excluded | 10 | 10 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_referencetype.type` | excluded | 10 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_tables.table_name` | excluded | 7 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_entity_tables.webservice_entity_id` | excluded | 7 | 7 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_fieldinfo.id` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_fieldinfo.property_name` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_fieldinfo.property_value` | excluded | 1 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_fieldtype.fieldtype` | excluded | 43 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_fieldtype.fieldtypeid` | excluded | 43 | 43 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_fieldtype.uitype` | excluded | 43 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation.handler_method` | excluded | 38 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation.handler_path` | excluded | 38 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation.name` | excluded | 38 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation.operationid` | excluded | 38 | 38 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation.prelogin` | excluded | 38 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation.type` | excluded | 38 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation_parameters.name` | excluded | 67 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation_parameters.operationid` | excluded | 67 | 67 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation_parameters.sequence` | excluded | 67 | 67 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation_parameters.type` | excluded | 67 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_operation_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_referencetype.fieldtypeid` | excluded | 35 | 35 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_referencetype.type` | excluded | 35 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_userauthtoken.expiretime` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_userauthtoken.token` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_ws_userauthtoken.userid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp.appid` | excluded | 3 | 3 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp.appkey` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp.name` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp.type` | excluded | 3 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_handlerdetails.handlerclass` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_handlerdetails.handlerpath` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_handlerdetails.type` | excluded | 5 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.app_create_count` | excluded | 2 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.app_delete_count` | excluded | 2 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.app_skip_count` | excluded | 2 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.app_update_count` | excluded | 2 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.extensiontabid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.id` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.module` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.sync_datetime` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.userid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.vt_create_count` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.vt_delete_count` | excluded | 2 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.vt_skip_count` | excluded | 2 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic.vt_update_count` | excluded | 2 | 0 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_basic_seq.id` | excluded | 1 | 1 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_details.app_create_ids` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_details.app_delete_ids` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_details.app_skip_info` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_details.app_update_ids` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_details.id` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_details.vt_create_ids` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_details.vt_delete_ids` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_details.vt_skip_info` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_logs_details.vt_update_ids` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_recordmapping.appid` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_recordmapping.clientid` | excluded | 286 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_recordmapping.clientmodifiedtime` | excluded | 286 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_recordmapping.id` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_recordmapping.serverappid` | excluded | 286 | 286 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_recordmapping.serverid` | excluded | 286 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_recordmapping.servermodifiedtime` | excluded | 286 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_sync_state.id` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_sync_state.name` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_sync_state.stateencodedvalues` | excluded | 2 |  |  |  |  |  |  |  | excluded |
| `vtiger7.vtiger_wsapp_sync_state.userid` | excluded | 2 | 2 |  |  |  |  |  |  | excluded |
