# Покрытие финансовых полей и связей аудита (этап 04.6)

<!-- Сгенерировано scripts/model/build_finance_coverage.py — не править вручную; проверка: task model:check. -->

Источник — `field-map.csv` и `relations.csv` (счётчики аудита: проверено SQL 2026-10-03) и модель EspoCRM (метаданные ядра и модуля `Itvolga`). Каждая строка области получает один итог; реализованная строка заново проверяется `model_check` (стадия и текст проверки должны совпасть с картой). Покрытие строки — модель и путь записи; сверка значений живых записей после импорта — этап 06.4.

## Область

- Модули: `Quotes`, `SalesOrder`, `Invoice`, `Act`, `SPPayments`, `PurchaseOrder`, `Consignment`, `VTEItems`.
- Ссылки других модулей на финансовые документы: колонки `invoiceid`, `purchaseorderid`, `quote_id`, `quoteid`, `salesorder_id`, `salesorderid`, `sp_act_id`.
- Таблицы без модуля: Таблицы документов (ключи, адреса, пользовательские поля) (`^vtiger_(quotes|salesorder|invoice|sp_act|sp_consignment|purchaseorder|vteitems)(cf|billads|shipads)?$|^vtiger_(sobillads|soshipads|pobillads|poshipads|invoice_recurring_info)$`); Строки документов (`^vtiger_inventory(productrel|chargesrel)(_seq)?$`); Таблицы платежей (`^sp_payments`); Юрлицо (`^vtiger_(organizationdetails|spcompany)(_seq)?$`); Налоги, валюта, доп. расходы (`^vtiger_(inventorytaxinfo|shippingtaxinfo|inventorycharges|taxclass|currency_info|currencies|productcurrencyrel)(_seq)?$`); Справочники статусов и значений (`^vtiger_(quotestage|sostatus|invoicestatus|sp_actstatus|postatus|sp_consignmentstatus|spstatus|pay_type|type_payment|carrier|recurring_frequency|payment_duration)(_seq)?$`); История статусов (`^vtiger_(invoicestatushistory|sp_actstatushistory)(_seq)?$`); Нумерация (`^vtiger_modentity_num(_seq)?$`); Печатные формы, условия, уведомления (`^(sp_templates|vtiger_quotingtool\w*|vtiger_inventory_tandc|vtiger_inventorynotification)(_seq)?$`); Настройки платного расширения Quoter (`^quoter_`).
- Общие колонки записей: `vtiger_crmentity.crmid`, `vtiger_crmentity.setype`.
- Вне области (похожи на финансовые): `^vtiger_(currency_decimal_separator|currency_grouping_pattern|currency_grouping_separator|currency_symbol_placement|no_of_currency_decimals)(_seq)?$` — формат чисел пользователя (Preferences, этап 03); `^vtiger_emailtemplates(_seq)?$` — шаблоны писем, не финансовые печатные формы; `^vtiger_glacct(_seq)?$` — счёт учёта товара (Products, этап 03); `^vtiger_recurringtype(_seq)?$` — повторение событий календаря (Events, этап 03), не периодичность заказов.

## Итоги

| Раздел | перенос | рабочее поле, в источнике пусто | справочник | архив | ключ | настройка | печатная форма | исключено | пусто | открыто | всего |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Предложения (Quotes → Quote) | 37 | 16 |  |  |  |  |  | 5 |  |  | 58 |
| Заказы (SalesOrder) | 36 | 18 |  | 8 |  |  |  | 5 | 3 |  | 70 |
| Счета (Invoice) | 43 | 13 |  | 3 |  |  |  | 5 |  |  | 64 |
| Акты (Act) | 36 | 11 |  | 1 |  |  |  | 6 |  |  | 54 |
| Платежи (SPPayments → Payment) | 23 | 3 |  | 1 |  |  |  | 3 |  |  | 30 |
| Заказы поставщикам (PurchaseOrder): записей нет, сущность не создаётся |  |  |  |  |  |  |  | 5 | 54 |  | 59 |
| Накладные (Consignment → VtigerArchive, только чтение) | 1 |  |  | 36 |  |  |  |  | 20 |  | 57 |
| Строки VTEItems: дубль строк документов, исключены (D-09) |  |  |  |  |  |  |  | 19 |  |  | 19 |
| Ссылки других модулей на финансовые документы |  |  |  |  |  |  |  |  | 3 |  | 3 |
| Таблицы документов (ключи, адреса, пользовательские поля) | 1 |  |  | 4 | 23 |  |  | 2 | 13 |  | 43 |
| Строки документов | 3 |  |  |  |  |  |  | 5 |  |  | 8 |
| Таблицы платежей | 2 |  |  |  |  |  |  |  |  |  | 2 |
| Юрлицо | 22 |  |  |  |  |  |  | 9 | 2 |  | 33 |
| Налоги, валюта, доп. расходы |  |  |  |  |  | 43 |  | 9 |  |  | 52 |
| Справочники статусов и значений |  |  | 42 | 22 |  |  |  | 18 |  |  | 82 |
| История статусов |  |  |  |  |  |  |  | 14 |  |  | 14 |
| Нумерация |  |  |  |  |  |  |  | 8 |  |  | 8 |
| Печатные формы, условия, уведомления |  |  |  |  |  | 3 | 8 | 43 |  |  | 54 |
| Настройки платного расширения Quoter |  |  |  |  |  |  |  | 48 |  |  | 48 |
| Общие колонки записей (vtiger_crmentity) | 1 |  |  |  | 1 |  |  |  |  |  | 2 |
| Связи (relations.csv) | 57 | 1 |  | 7 |  |  |  | 16 | 6 |  | 87 |
| **всего** | **262** | **62** | **42** | **82** | **24** | **46** | **8** | **220** | **101** | **0** | **847** |

Итоги:

- **перенос** — значения переносятся в рабочее поле EspoCRM (поле или связь есть в модели, проверено `model_check`).
- **рабочее поле, в источнике пусто** — в источнике значений нет; поле нужно новым документам (D-47) и есть в модели.
- **справочник** — значения — опции enum и словарь `vtigerValueMap` (D-38).
- **архив** — исходные значения хранятся только для чтения (`vtigerData`, `VtigerArchive.data`).
- **ключ** — ключ записи или соединения таблиц: исходный id → `vtigerId`, тип записи → целевая сущность.
- **настройка** — воспроизводится настройкой EspoCRM (валюта RUB, без НДС — D-21, D-37; условия документов по умолчанию — D-83).
- **печатная форма** — шаблон источника воспроизведён печатной формой модуля (этап 05, D-79; реестр и файлы форм проверены `model_check`).
- **исключено** — не переносится по решению (причина — в строке).
- **пусто** — в источнике значений нет, рабочее поле не создаётся.
- **открыто** — нет окончательного решения — должно быть 0.

## Открытые расхождения

Нет: у каждой строки области есть окончательный итог.

## Цепочка документов (реестр `app.itvolgaFinance`)

| Переход | Связь | Копируемые поля | Модель |
|---|---|---|---|
| Quote → позиции | Quote.items ↔ QuoteItem.quote | — | ok |
| SalesOrder → позиции | SalesOrder.items ↔ SalesOrderItem.salesOrder | — | ok |
| Invoice → позиции | Invoice.items ↔ InvoiceItem.invoice | — | ok |
| Act → позиции | Act.items ↔ ActItem.act | — | ok |
| Quote → SalesOrder | SalesOrder.quote (ссылка у нового документа) | name, account, contact, opportunity, assignedUser, teams, taxMode, discountAmount, discountPercent, shippingAmount, adjustment, billingAddress, shippingAddress, termsAndConditions, description | ok |
| Quote → Invoice | Invoice.quote (ссылка у нового документа) | name, account, contact, opportunity, assignedUser, teams, taxMode, discountAmount, discountPercent, shippingAmount, adjustment, billingAddress, shippingAddress, termsAndConditions, description | ok |
| SalesOrder → Invoice | Invoice.salesOrder (ссылка у нового документа) | name, account, contact, opportunity, assignedUser, teams, taxMode, discountAmount, discountPercent, shippingAmount, adjustment, billingAddress, shippingAddress, termsAndConditions, description, quote | ok |
| Invoice → Act | Act.invoices (ключ у источника) | name, account, contact, assignedUser, teams, taxMode, discountAmount, discountPercent, shippingAmount, adjustment, billingAddress, shippingAddress, description | ok |
| Payment → Invoice | PaymentAllocation.invoice ↔ Invoice.paymentAllocations | «Добавить платёж»: плательщик, сумма, строка распределения | ok |
| Payment → SalesOrder | PaymentAllocation.salesOrder ↔ SalesOrder.paymentAllocations | «Добавить платёж»: плательщик, сумма, строка распределения | ok |

Статус, номер, даты, итоги и пометки источника не копируются: у нового документа — свои умолчания, номер из счётчика и расчёт ядра; юрлицо подставляет сервер; платёж назначается текущему пользователю (D-67).

## Тесты по сущностям

| Сущность | Тесты |
|---|---|
| Quote, QuoteItem | `tests/stage04/test_stage04_2.py`, `tests/stage04/test_stage04_6.py` |
| SalesOrder, SalesOrderItem | `tests/stage04/test_stage04_2.py`, `tests/stage04/test_stage04_6.py` |
| Invoice, InvoiceItem | `tests/stage04/test_stage04_3.py`, `tests/stage04/test_stage04_6.py` |
| Payment, PaymentAllocation | `tests/stage04/test_stage04_4.py`, `tests/stage04/test_stage04_6.py` |
| Act, ActItem | `tests/stage04/test_stage04_5.py`, `tests/stage04/test_stage04_6.py` |
| LegalEntity | `tests/stage04/test_stage04_2.py`, `tests/stage04/test_stage04_3.py` |
| расчётное ядро (итоги, налоги, оплата, юрлицо) | `tests/finance/run.php` |
| печатные формы (этап 05) | `tests/stage05/test_stage05.py`, `tests/finance/run.php` |

## Поля: Предложения (Quotes → Quote)

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_quotes.subject` | subject (Subject) | 24 из 24 | Quote.name | перенос | реализовано (этап 04.2) | ok: Quote.name varchar(255) |
| `vtiger_quotes.potentialid` | potential_id (Potential Name) | 24 из 24 | Quote.opportunity | перенос | реализовано (этап 04.2) | ok: Quote.opportunity link |
| `vtiger_quotes.quote_no` | quote_no (Quote No) | 24 из 24 | Quote.number | перенос | реализовано (этап 04.2) | ok: Quote.number varchar(100) |
| `vtiger_quotes.quotestage` | quotestage (Quote Stage) | 24 из 24 | Quote.status | перенос | реализовано (этап 04.2) | ok: Quote.status enum |
| `vtiger_quotes.validtill` | validtill (Valid Till) | 15 из 24 | Quote.dateValidUntil | перенос | реализовано (этап 04.2) | ok: Quote.dateValidUntil date |
| `vtiger_quotes.contactid` | contact_id (Contact Name) | 6 из 24 | Quote.contact | перенос | реализовано (этап 04.2) | ok: Quote.contact link |
| `vtiger_quotes.carrier` | carrier (Carrier) | 0 из 24 | vtigerData.carrier | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.vtigerData jsonObject |
| `vtiger_quotes.subtotal` | hdnSubTotal (Sub Total) | 24 из 24 | Quote.subtotal | перенос | реализовано (этап 04.2) | ok: Quote.subtotal currency decimal(25,8) |
| `vtiger_quotes.shipping` | shipping (Shipping) | 0 из 24 | vtigerData.shipping | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.vtigerData jsonObject |
| `vtiger_quotes.inventorymanager` | assigned_user_id1 (Inventory Manager) | 23 из 24 | Quote.inventoryManager | перенос | реализовано (этап 04.2) | ok: Quote.inventoryManager link |
| `vtiger_quotes.total` | hdnGrandTotal (Total) | 24 из 24 | Quote.grandTotal | перенос | реализовано (этап 04.2) | ok: Quote.grandTotal currency decimal(25,8) |
| `vtiger_quotes.taxtype` | hdnTaxType (Tax Type) | 24 из 24 | Quote.taxMode | перенос | реализовано (этап 04.2) | ok: Quote.taxMode enum |
| `vtiger_quotes.s_h_amount` | hdnS_H_Amount (S&H Amount) | 0 из 24 | Quote.shippingAmount | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.shippingAmount currency decimal(25,8) |
| `vtiger_quotes.accountid` | account_id (Account Name) | 24 из 24 | Quote.account | перенос | реализовано (этап 04.2) | ok: Quote.account link |
| `vtiger_crmentity.smownerid` | assigned_user_id (Assigned To) | 24 из 24 | Quote.assignedUser / teams | перенос | реализовано (этап 04.2) | ok: Quote.assignedUser link; Quote.teams linkMultiple |
| `vtiger_crmentity.createdtime` | createdtime (Created Time) | 24 из 24 | Quote.createdAt | перенос | реализовано (этап 04.2) | ok: Quote.createdAt datetime |
| `vtiger_crmentity.modifiedtime` | modifiedtime (Modified Time) | 24 из 24 | Quote.modifiedAt | перенос | реализовано (этап 04.2) | ok: Quote.modifiedAt datetime |
| `vtiger_quotes.adjustment` | txtAdjustment (Adjustment) | 0 из 24 | Quote.adjustment | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.adjustment currency decimal(25,8) |
| `vtiger_quotes.currency_id` | currency_id (Currency) | 24 из 24 | Quote.currency | перенос | реализовано (этап 04.2) | ok: Quote: валюта RUB (12 денежных полей decimal, onlyDefaultCurrency) |
| `vtiger_quotes.conversion_rate` | conversion_rate (Conversion Rate) | 24 из 24 | — | исключено | решено | всегда 1.000 (одна валюта) |
| `vtiger_crmentity.modifiedby` | modifiedby (Last Modified By) | 24 из 24 | Quote.modifiedBy | перенос | реализовано (этап 04.2) | ok: Quote.modifiedBy link |
| `vtiger_quotes.pre_tax_total` | pre_tax_total (Pre Tax Total) | 24 из 24 | Quote.preTaxTotal | перенос | реализовано (этап 04.2) | ok: Quote.preTaxTotal currency decimal(25,8) |
| `vtiger_quotes.spcompany` | spcompany (Self Company) | 24 из 24 | legalEntity + vtigerData.spcompany | перенос | реализовано (этап 04.2) | ok: Quote.legalEntity link; Quote.vtigerData jsonObject |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 24 из 24 | Quote.createdBy | перенос | реализовано (этап 04.2) | ok: Quote.createdBy link |
| `vtiger_crmentity.source` | source (Source) | 24 из 24 | — | исключено | решено | технический канал создания записи Vtiger (CRM/WEBSERVICE) |
| `vtiger_crmentity_user_field.starred` | starred (starred) | 0 из 24 | — | исключено | решено | персональная «звёздочка» пользователя (истинных значений — единицы) |
| `vtiger_quotes.tags` | tags (tags) | 0 из 24 | — | исключено | решено | пусто в источнике (теги — vtiger_freetagged_objects) |
| `vtiger_quotesbillads.bill_street` | bill_street (Billing Address) | 24 из 24 | Quote.billingAddressStreet | перенос | реализовано (этап 04.2) | ok: Quote.billingAddressStreet text |
| `vtiger_quotesshipads.ship_street` | ship_street (Shipping Address) | 24 из 24 | Quote.shippingAddressStreet | перенос | реализовано (этап 04.2) | ok: Quote.shippingAddressStreet text |
| `vtiger_quotesbillads.bill_pobox` | bill_pobox (Billing Po Box) | 0 из 24 | vtigerData.bill_pobox | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.vtigerData jsonObject |
| `vtiger_quotesshipads.ship_pobox` | ship_pobox (Shipping Po Box) | 0 из 24 | vtigerData.ship_pobox | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.vtigerData jsonObject |
| `vtiger_quotesbillads.bill_city` | bill_city (Billing City) | 24 из 24 | Quote.billingAddressCity | перенос | реализовано (этап 04.2) | ok: Quote.billingAddressCity varchar(100) |
| `vtiger_quotesshipads.ship_city` | ship_city (Shipping City) | 23 из 24 | Quote.shippingAddressCity | перенос | реализовано (этап 04.2) | ok: Quote.shippingAddressCity varchar(100) |
| `vtiger_quotesbillads.bill_state` | bill_state (Billing State) | 19 из 24 | Quote.billingAddressState | перенос | реализовано (этап 04.2) | ok: Quote.billingAddressState varchar(100) |
| `vtiger_quotesshipads.ship_state` | ship_state (Shipping State) | 18 из 24 | Quote.shippingAddressState | перенос | реализовано (этап 04.2) | ok: Quote.shippingAddressState varchar(100) |
| `vtiger_quotesbillads.bill_code` | bill_code (Billing Code) | 21 из 24 | Quote.billingAddressPostalCode | перенос | реализовано (этап 04.2) | ok: Quote.billingAddressPostalCode varchar(40) |
| `vtiger_quotesshipads.ship_code` | ship_code (Shipping Code) | 21 из 24 | Quote.shippingAddressPostalCode | перенос | реализовано (этап 04.2) | ok: Quote.shippingAddressPostalCode varchar(40) |
| `vtiger_quotesbillads.bill_country` | bill_country (Billing Country) | 20 из 24 | Quote.billingAddressCountry | перенос | реализовано (этап 04.2) | ok: Quote.billingAddressCountry varchar(100) |
| `vtiger_quotesshipads.ship_country` | ship_country (Shipping Country) | 20 из 24 | Quote.shippingAddressCountry | перенос | реализовано (этап 04.2) | ok: Quote.shippingAddressCountry varchar(100) |
| `vtiger_quotes.terms_conditions` | terms_conditions (Terms & Conditions) | 24 из 24 | Quote.termsAndConditions | перенос | реализовано (этап 04.2) | ok: Quote.termsAndConditions text |
| `vtiger_crmentity.description` | description (Description) | 0 из 24 | Quote.description | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.description text |
| `vtiger_inventoryproductrel.productid` | productid (Item Name) | 27 из 27 | QuoteItem.product | перенос | реализовано (этап 04.2) | ok: QuoteItem.product link |
| `vtiger_inventoryproductrel.quantity` | quantity (Quantity) | 27 из 27 | QuoteItem.quantity | перенос | реализовано (этап 04.2) | ok: QuoteItem.quantity decimal decimal(25,3) |
| `vtiger_inventoryproductrel.listprice` | listprice (List Price) | 27 из 27 | QuoteItem.unitPrice | перенос | реализовано (этап 04.2) | ok: QuoteItem.unitPrice currency decimal(27,8) |
| `vtiger_inventoryproductrel.comment` | comment (Item Comment) | 22 из 27 | QuoteItem.description | перенос | реализовано (этап 04.2) | ok: QuoteItem.description text |
| `vtiger_inventoryproductrel.discount_amount` | discount_amount (Item Discount Amount) | 0 из 27 | QuoteItem.discountAmount | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: QuoteItem.discountAmount currency decimal(27,8) |
| `vtiger_inventoryproductrel.discount_percent` | discount_percent (Item Discount Percent) | 0 из 27 | QuoteItem.discountPercent | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: QuoteItem.discountPercent decimal decimal(7,3) |
| `vtiger_inventoryproductrel.tax1` | tax1 (НДС) | 26 из 27 | QuoteItem.taxRate | перенос | реализовано (этап 04.2) | ok: QuoteItem.taxRate decimal decimal(7,3) |
| `vtiger_inventoryproductrel.tax2` | tax2 (Tax2) | 0 из 27 | QuoteItem.vtigerData.tax2 | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: QuoteItem.vtigerData jsonObject |
| `vtiger_inventoryproductrel.tax3` | tax3 (Tax3) | 0 из 27 | QuoteItem.vtigerData.tax3 | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: QuoteItem.vtigerData jsonObject |
| `vtiger_quotes.s_h_percent` | hdnS_H_Percent (S&H Percent) | 0 из 24 | Quote.shippingTaxPercent | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.shippingTaxPercent decimal |
| `vtiger_quotes.discount_percent` | hdnDiscountPercent (Discount Percent) | 0 из 24 | Quote.discountPercent | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.discountPercent decimal decimal(25,3) |
| `vtiger_quotes.discount_amount` | hdnDiscountAmount (Discount Amount) | 0 из 24 | Quote.discountAmount | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.discountAmount currency decimal(25,8) |
| `vtiger_inventoryproductrel.image` | image (Image) | 0 из 27 | — | исключено | решено | пустое служебное поле |
| `vtiger_inventoryproductrel.purchase_cost` | purchase_cost (Purchase Cost) | 0 из 27 | QuoteItem.purchaseCost | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: QuoteItem.purchaseCost currency decimal(27,8) |
| `vtiger_inventoryproductrel.margin` | margin (Margin) | 1 из 27 | QuoteItem.margin | перенос | реализовано (этап 04.2) | ok: QuoteItem.margin currency decimal(27,8) |
| `vtiger_quotes.region_id` | region_id (Tax Region) | 0 из 24 | sourceFormula + vtigerData.region_id | перенос | реализовано (этап 04.2) | ok: Quote.sourceFormula enum; Quote.vtigerData jsonObject |
| `vtiger_quotescf.tax` | tax (tax) | 0 из 24 | vtigerData.tax | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: Quote.vtigerData jsonObject |

## Поля: Заказы (SalesOrder)

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_salesorder.subject` | subject (Subject) | 14 из 14 | SalesOrder.name | перенос | реализовано (этап 04.2) | ok: SalesOrder.name varchar(255) |
| `vtiger_salesorder.potentialid` | potential_id (Potential Name) | 12 из 14 | SalesOrder.opportunity | перенос | реализовано (этап 04.2) | ok: SalesOrder.opportunity link |
| `vtiger_salesorder.customerno` | customerno (Customer No) | 0 из 14 | — | пусто | решено | пусто — данных нет |
| `vtiger_salesorder.salesorder_no` | salesorder_no (SalesOrder No) | 14 из 14 | SalesOrder.number | перенос | реализовано (этап 04.2) | ok: SalesOrder.number varchar(100) |
| `vtiger_salesorder.quoteid` | quote_id (Quote Name) | 0 из 14 | SalesOrder.quote | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.quote link |
| `vtiger_salesorder.purchaseorder` | vtiger_purchaseorder (Purchase Order) | 0 из 14 | — | пусто | решено | пусто — данных нет |
| `vtiger_salesorder.contactid` | contact_id (Contact Name) | 8 из 14 | SalesOrder.contact | перенос | реализовано (этап 04.2) | ok: SalesOrder.contact link |
| `vtiger_salesorder.duedate` | duedate (Due Date) | 7 из 14 | SalesOrder.dateDue | перенос | реализовано (этап 04.2) | ok: SalesOrder.dateDue date |
| `vtiger_salesorder.carrier` | carrier (Carrier) | 1 из 14 | vtigerData.carrier | архив | реализовано (этап 04.2) | ok: SalesOrder.vtigerData jsonObject |
| `vtiger_salesorder.pending` | pending (Pending) | 1 из 14 | vtigerData.pending | архив | реализовано (этап 04.2) | ok: SalesOrder.vtigerData jsonObject |
| `vtiger_salesorder.sostatus` | sostatus (Status) | 14 из 14 | SalesOrder.status | перенос | реализовано (этап 04.2) | ok: SalesOrder.status enum |
| `vtiger_salesorder.adjustment` | txtAdjustment (Adjustment) | 0 из 14 | SalesOrder.adjustment | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.adjustment currency decimal(25,8) |
| `vtiger_salesorder.salescommission` | salescommission (Sales Commission) | 0 из 14 | vtigerData.salescommission | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.vtigerData jsonObject |
| `vtiger_salesorder.exciseduty` | exciseduty (Excise Duty) | 0 из 14 | vtigerData.exciseduty | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.vtigerData jsonObject |
| `vtiger_salesorder.total` | hdnGrandTotal (Total) | 14 из 14 | SalesOrder.grandTotal | перенос | реализовано (этап 04.2) | ok: SalesOrder.grandTotal currency decimal(25,8) |
| `vtiger_salesorder.subtotal` | hdnSubTotal (Sub Total) | 14 из 14 | SalesOrder.subtotal | перенос | реализовано (этап 04.2) | ok: SalesOrder.subtotal currency decimal(25,8) |
| `vtiger_salesorder.taxtype` | hdnTaxType (Tax Type) | 14 из 14 | SalesOrder.taxMode | перенос | реализовано (этап 04.2) | ok: SalesOrder.taxMode enum |
| `vtiger_salesorder.s_h_amount` | hdnS_H_Amount (S&H Amount) | 0 из 14 | SalesOrder.shippingAmount | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.shippingAmount currency decimal(25,8) |
| `vtiger_salesorder.accountid` | account_id (Account Name) | 14 из 14 | SalesOrder.account | перенос | реализовано (этап 04.2) | ok: SalesOrder.account link |
| `vtiger_crmentity.smownerid` | assigned_user_id (Assigned To) | 14 из 14 | SalesOrder.assignedUser / teams | перенос | реализовано (этап 04.2) | ok: SalesOrder.assignedUser link; SalesOrder.teams linkMultiple |
| `vtiger_crmentity.createdtime` | createdtime (Created Time) | 14 из 14 | SalesOrder.createdAt | перенос | реализовано (этап 04.2) | ok: SalesOrder.createdAt datetime |
| `vtiger_crmentity.modifiedtime` | modifiedtime (Modified Time) | 14 из 14 | SalesOrder.modifiedAt | перенос | реализовано (этап 04.2) | ok: SalesOrder.modifiedAt datetime |
| `vtiger_salesorder.currency_id` | currency_id (Currency) | 14 из 14 | SalesOrder.currency | перенос | реализовано (этап 04.2) | ok: SalesOrder: валюта RUB (14 денежных полей decimal, onlyDefaultCurrency) |
| `vtiger_salesorder.conversion_rate` | conversion_rate (Conversion Rate) | 14 из 14 | — | исключено | решено | всегда 1.000 (одна валюта) |
| `vtiger_crmentity.modifiedby` | modifiedby (Last Modified By) | 14 из 14 | SalesOrder.modifiedBy | перенос | реализовано (этап 04.2) | ok: SalesOrder.modifiedBy link |
| `vtiger_salesorder.one_s_id` | one_s_id (1C ID) | 0 из 14 | — | пусто | решено | пусто — данных нет |
| `vtiger_salesorder.fromsite` | fromsite (fromsite) | 0 из 14 | vtigerData.fromsite | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.vtigerData jsonObject |
| `vtiger_salesorder.pre_tax_total` | pre_tax_total (Pre Tax Total) | 14 из 14 | SalesOrder.preTaxTotal | перенос | реализовано (этап 04.2) | ok: SalesOrder.preTaxTotal currency decimal(25,8) |
| `vtiger_salesorder.spcompany` | spcompany (Self Company) | 14 из 14 | legalEntity + vtigerData.spcompany | перенос | реализовано (этап 04.2) | ok: SalesOrder.legalEntity link; SalesOrder.vtigerData jsonObject |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 14 из 14 | SalesOrder.createdBy | перенос | реализовано (этап 04.2) | ok: SalesOrder.createdBy link |
| `vtiger_crmentity.source` | source (Source) | 14 из 14 | — | исключено | решено | технический канал создания записи Vtiger (CRM/WEBSERVICE) |
| `vtiger_crmentity_user_field.starred` | starred (starred) | 0 из 14 | — | исключено | решено | персональная «звёздочка» пользователя (истинных значений — единицы) |
| `vtiger_salesorder.tags` | tags (tags) | 0 из 14 | — | исключено | решено | пусто в источнике (теги — vtiger_freetagged_objects) |
| `vtiger_sobillads.bill_street` | bill_street (Billing Address) | 14 из 14 | SalesOrder.billingAddressStreet | перенос | реализовано (этап 04.2) | ok: SalesOrder.billingAddressStreet text |
| `vtiger_soshipads.ship_street` | ship_street (Shipping Address) | 14 из 14 | SalesOrder.shippingAddressStreet | перенос | реализовано (этап 04.2) | ok: SalesOrder.shippingAddressStreet text |
| `vtiger_sobillads.bill_pobox` | bill_pobox (Billing Po Box) | 0 из 14 | vtigerData.bill_pobox | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.vtigerData jsonObject |
| `vtiger_soshipads.ship_pobox` | ship_pobox (Shipping Po Box) | 0 из 14 | vtigerData.ship_pobox | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.vtigerData jsonObject |
| `vtiger_sobillads.bill_city` | bill_city (Billing City) | 14 из 14 | SalesOrder.billingAddressCity | перенос | реализовано (этап 04.2) | ok: SalesOrder.billingAddressCity varchar(100) |
| `vtiger_soshipads.ship_city` | ship_city (Shipping City) | 14 из 14 | SalesOrder.shippingAddressCity | перенос | реализовано (этап 04.2) | ok: SalesOrder.shippingAddressCity varchar(100) |
| `vtiger_sobillads.bill_state` | bill_state (Billing State) | 10 из 14 | SalesOrder.billingAddressState | перенос | реализовано (этап 04.2) | ok: SalesOrder.billingAddressState varchar(100) |
| `vtiger_soshipads.ship_state` | ship_state (Shipping State) | 10 из 14 | SalesOrder.shippingAddressState | перенос | реализовано (этап 04.2) | ok: SalesOrder.shippingAddressState varchar(100) |
| `vtiger_sobillads.bill_code` | bill_code (Billing Code) | 12 из 14 | SalesOrder.billingAddressPostalCode | перенос | реализовано (этап 04.2) | ok: SalesOrder.billingAddressPostalCode varchar(40) |
| `vtiger_soshipads.ship_code` | ship_code (Shipping Code) | 12 из 14 | SalesOrder.shippingAddressPostalCode | перенос | реализовано (этап 04.2) | ok: SalesOrder.shippingAddressPostalCode varchar(40) |
| `vtiger_sobillads.bill_country` | bill_country (Billing Country) | 11 из 14 | SalesOrder.billingAddressCountry | перенос | реализовано (этап 04.2) | ok: SalesOrder.billingAddressCountry varchar(100) |
| `vtiger_soshipads.ship_country` | ship_country (Shipping Country) | 11 из 14 | SalesOrder.shippingAddressCountry | перенос | реализовано (этап 04.2) | ok: SalesOrder.shippingAddressCountry varchar(100) |
| `vtiger_salesorder.terms_conditions` | terms_conditions (Terms & Conditions) | 14 из 14 | SalesOrder.termsAndConditions | перенос | реализовано (этап 04.2) | ok: SalesOrder.termsAndConditions text |
| `vtiger_crmentity.description` | description (Description) | 0 из 14 | SalesOrder.description | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.description text |
| `vtiger_salesorder.enable_recurring` | enable_recurring (Enable Recurring) | 3 из 14 | vtigerData.enable_recurring | архив | реализовано (этап 04.2) | ok: SalesOrder.vtigerData jsonObject |
| `vtiger_invoice_recurring_info.recurring_frequency` | recurring_frequency (Frequency) | 3 из 13 | vtigerData.recurring_frequency | архив | реализовано (этап 04.2) | ok: SalesOrder.vtigerData jsonObject |
| `vtiger_invoice_recurring_info.start_period` | start_period (Start Period) | 3 из 13 | vtigerData.start_period | архив | реализовано (этап 04.2) | ok: SalesOrder.vtigerData jsonObject |
| `vtiger_invoice_recurring_info.end_period` | end_period (End Period) | 3 из 13 | vtigerData.end_period | архив | реализовано (этап 04.2) | ok: SalesOrder.vtigerData jsonObject |
| `vtiger_invoice_recurring_info.payment_duration` | payment_duration (Payment Duration) | 3 из 13 | vtigerData.payment_duration | архив | реализовано (этап 04.2) | ok: SalesOrder.vtigerData jsonObject |
| `vtiger_invoice_recurring_info.invoice_status` | invoicestatus (Invoice Status) | 13 из 13 | vtigerData.recurring_invoice_status | архив | реализовано (этап 04.2) | ok: SalesOrder.vtigerData jsonObject |
| `vtiger_inventoryproductrel.productid` | productid (Item Name) | 14 из 14 | SalesOrderItem.product | перенос | реализовано (этап 04.2) | ok: SalesOrderItem.product link |
| `vtiger_inventoryproductrel.quantity` | quantity (Quantity) | 14 из 14 | SalesOrderItem.quantity | перенос | реализовано (этап 04.2) | ok: SalesOrderItem.quantity decimal decimal(25,3) |
| `vtiger_inventoryproductrel.listprice` | listprice (List Price) | 14 из 14 | SalesOrderItem.unitPrice | перенос | реализовано (этап 04.2) | ok: SalesOrderItem.unitPrice currency decimal(27,8) |
| `vtiger_inventoryproductrel.comment` | comment (Item Comment) | 12 из 14 | SalesOrderItem.description | перенос | реализовано (этап 04.2) | ok: SalesOrderItem.description text |
| `vtiger_inventoryproductrel.discount_amount` | discount_amount (Item Discount Amount) | 0 из 14 | SalesOrderItem.discountAmount | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrderItem.discountAmount currency decimal(27,8) |
| `vtiger_inventoryproductrel.discount_percent` | discount_percent (Item Discount Percent) | 0 из 14 | SalesOrderItem.discountPercent | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrderItem.discountPercent decimal decimal(7,3) |
| `vtiger_inventoryproductrel.tax1` | tax1 (НДС) | 13 из 14 | SalesOrderItem.taxRate | перенос | реализовано (этап 04.2) | ok: SalesOrderItem.taxRate decimal decimal(7,3) |
| `vtiger_inventoryproductrel.tax2` | tax2 (Tax2) | 0 из 14 | SalesOrderItem.vtigerData.tax2 | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrderItem.vtigerData jsonObject |
| `vtiger_inventoryproductrel.tax3` | tax3 (Tax3) | 0 из 14 | SalesOrderItem.vtigerData.tax3 | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrderItem.vtigerData jsonObject |
| `vtiger_salesorder.s_h_percent` | hdnS_H_Percent (S&H Percent) | 0 из 14 | SalesOrder.shippingTaxPercent | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.shippingTaxPercent decimal |
| `vtiger_salesorder.discount_percent` | hdnDiscountPercent (Discount Percent) | 0 из 14 | SalesOrder.discountPercent | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.discountPercent decimal decimal(25,3) |
| `vtiger_salesorder.discount_amount` | hdnDiscountAmount (Discount Amount) | 0 из 14 | SalesOrder.discountAmount | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.discountAmount currency decimal(25,8) |
| `vtiger_inventoryproductrel.image` | image (Image) | 0 из 14 | — | исключено | решено | пустое служебное поле |
| `vtiger_inventoryproductrel.purchase_cost` | purchase_cost (Purchase Cost) | 0 из 14 | SalesOrderItem.purchaseCost | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrderItem.purchaseCost currency decimal(27,8) |
| `vtiger_inventoryproductrel.margin` | margin (Margin) | 1 из 14 | SalesOrderItem.margin | перенос | реализовано (этап 04.2) | ok: SalesOrderItem.margin currency decimal(27,8) |
| `vtiger_salesorder.region_id` | region_id (Tax Region) | 0 из 14 | sourceFormula + vtigerData.region_id | перенос | реализовано (этап 04.2) | ok: SalesOrder.sourceFormula enum; SalesOrder.vtigerData jsonObject |
| `vtiger_salesordercf.tax` | tax (tax) | 0 из 14 | vtigerData.tax | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.vtigerData jsonObject |

## Поля: Счета (Invoice)

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_invoice.subject` | subject (Subject) | 636 из 636 | Invoice.name | перенос | реализовано (этап 04.3) | ok: Invoice.name varchar(255) |
| `vtiger_invoice.salesorderid` | salesorder_id (Sales Order) | 27 из 636 | Invoice.salesOrder | перенос | реализовано (этап 04.3) | ok: Invoice.salesOrder link |
| `vtiger_invoice.customerno` | customerno (Customer No) | 1 из 636 | vtigerData.customerno | архив | реализовано (этап 04.3) | ok: Invoice.vtigerData jsonObject |
| `vtiger_invoice.invoice_no` | invoice_no (Invoice No) | 636 из 636 | Invoice.number | перенос | реализовано (этап 04.3) | ok: Invoice.number varchar(100) |
| `vtiger_invoice.contactid` | contact_id (Contact Name) | 23 из 636 | Invoice.contact | перенос | реализовано (этап 04.3) | ok: Invoice.contact link |
| `vtiger_invoice.invoicedate` | invoicedate (Invoice Date) | 635 из 636 | Invoice.dateInvoiced | перенос | реализовано (этап 04.3) | ok: Invoice.dateInvoiced date |
| `vtiger_invoice.duedate` | duedate (Due Date) | 536 из 636 | Invoice.dateDue | перенос | реализовано (этап 04.3) | ok: Invoice.dateDue date |
| `vtiger_invoice.purchaseorder` | vtiger_purchaseorder (Purchase Order) | 0 из 636 | vtigerData.purchaseorder | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: Invoice.vtigerData jsonObject |
| `vtiger_invoice.adjustment` | txtAdjustment (Adjustment) | 0 из 636 | Invoice.adjustment | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: Invoice.adjustment currency decimal(25,8) |
| `vtiger_invoice.exciseduty` | exciseduty (Excise Duty) | 0 из 636 | vtigerData.exciseduty | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: Invoice.vtigerData jsonObject |
| `vtiger_invoice.subtotal` | hdnSubTotal (Sub Total) | 636 из 636 | Invoice.subtotal | перенос | реализовано (этап 04.3) | ok: Invoice.subtotal currency decimal(25,8) |
| `vtiger_invoice.salescommission` | salescommission (Sales Commission) | 0 из 636 | vtigerData.salescommission | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: Invoice.vtigerData jsonObject |
| `vtiger_invoice.total` | hdnGrandTotal (Total) | 636 из 636 | Invoice.grandTotal | перенос | реализовано (этап 04.3) | ok: Invoice.grandTotal currency decimal(25,8) |
| `vtiger_invoice.taxtype` | hdnTaxType (Tax Type) | 636 из 636 | Invoice.taxMode | перенос | реализовано (этап 04.3) | ok: Invoice.taxMode enum |
| `vtiger_invoice.accountid` | account_id (Account Name) | 636 из 636 | Invoice.account | перенос | реализовано (этап 04.3) | ok: Invoice.account link |
| `vtiger_invoice.invoicestatus` | invoicestatus (Status) | 632 из 636 | Invoice.status | перенос | реализовано (этап 04.3) | ok: Invoice.status enum |
| `vtiger_crmentity.smownerid` | assigned_user_id (Assigned To) | 636 из 636 | Invoice.assignedUser / teams | перенос | реализовано (этап 04.3) | ok: Invoice.assignedUser link; Invoice.teams linkMultiple |
| `vtiger_crmentity.createdtime` | createdtime (Created Time) | 636 из 636 | Invoice.createdAt | перенос | реализовано (этап 04.3) | ok: Invoice.createdAt datetime |
| `vtiger_crmentity.modifiedtime` | modifiedtime (Modified Time) | 636 из 636 | Invoice.modifiedAt | перенос | реализовано (этап 04.3) | ok: Invoice.modifiedAt datetime |
| `vtiger_invoice.currency_id` | currency_id (Currency) | 636 из 636 | Invoice.currency | перенос | реализовано (этап 04.3) | ok: Invoice: валюта RUB (15 денежных полей decimal, onlyDefaultCurrency) |
| `vtiger_invoice.conversion_rate` | conversion_rate (Conversion Rate) | 636 из 636 | — | исключено | решено | всегда 1.000 (одна валюта) |
| `vtiger_crmentity.modifiedby` | modifiedby (Last Modified By) | 636 из 636 | Invoice.modifiedBy | перенос | реализовано (этап 04.3) | ok: Invoice.modifiedBy link |
| `vtiger_invoice.sp_act_id` | sp_act_id (Act) | 392 из 636 | Invoice.act | перенос | реализовано (этап 04.5) | ok: Invoice.act link |
| `vtiger_invoice.pre_tax_total` | pre_tax_total (Pre Tax Total) | 636 из 636 | Invoice.preTaxTotal | перенос | реализовано (этап 04.3) | ok: Invoice.preTaxTotal currency decimal(25,8) |
| `vtiger_invoice.received` | received (Received) | 0 из 636 | vtigerData.received | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: Invoice.vtigerData jsonObject |
| `vtiger_invoice.balance` | balance (Balance) | 636 из 636 | Invoice.balanceSource | перенос | реализовано (этап 04.3) | ok: Invoice.balanceSource currency decimal(25,8) |
| `vtiger_invoice.spcompany` | spcompany (Self Company) | 636 из 636 | legalEntity + vtigerData.spcompany | перенос | реализовано (этап 04.3) | ok: Invoice.legalEntity link; Invoice.vtigerData jsonObject |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 636 из 636 | Invoice.createdBy | перенос | реализовано (этап 04.3) | ok: Invoice.createdBy link |
| `vtiger_invoice.potential_id` | potential_id (Potential Name) | 636 из 636 | Invoice.opportunity | перенос | реализовано (этап 04.3) | ok: Invoice.opportunity link |
| `vtiger_crmentity.source` | source (Source) | 636 из 636 | — | исключено | решено | технический канал создания записи Vtiger (CRM/WEBSERVICE) |
| `vtiger_crmentity_user_field.starred` | starred (starred) | 0 из 636 | — | исключено | решено | персональная «звёздочка» пользователя (истинных значений — единицы) |
| `vtiger_invoice.tags` | tags (tags) | 0 из 636 | — | исключено | решено | пусто в источнике (теги — vtiger_freetagged_objects) |
| `vtiger_invoicebillads.bill_street` | bill_street (Billing Address) | 636 из 636 | Invoice.billingAddressStreet | перенос | реализовано (этап 04.3) | ok: Invoice.billingAddressStreet text |
| `vtiger_invoiceshipads.ship_street` | ship_street (Shipping Address) | 636 из 636 | Invoice.shippingAddressStreet | перенос | реализовано (этап 04.3) | ok: Invoice.shippingAddressStreet text |
| `vtiger_invoicebillads.bill_pobox` | bill_pobox (Billing Po Box) | 0 из 636 | vtigerData.bill_pobox | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: Invoice.vtigerData jsonObject |
| `vtiger_invoiceshipads.ship_pobox` | ship_pobox (Shipping Po Box) | 40 из 636 | vtigerData.ship_pobox | архив | реализовано (этап 04.3) | ok: Invoice.vtigerData jsonObject |
| `vtiger_invoicebillads.bill_city` | bill_city (Billing City) | 613 из 636 | Invoice.billingAddressCity | перенос | реализовано (этап 04.3) | ok: Invoice.billingAddressCity varchar(100) |
| `vtiger_invoiceshipads.ship_city` | ship_city (Shipping City) | 613 из 636 | Invoice.shippingAddressCity | перенос | реализовано (этап 04.3) | ok: Invoice.shippingAddressCity varchar(100) |
| `vtiger_invoicebillads.bill_state` | bill_state (Billing State) | 366 из 636 | Invoice.billingAddressState | перенос | реализовано (этап 04.3) | ok: Invoice.billingAddressState varchar(100) |
| `vtiger_invoiceshipads.ship_state` | ship_state (Shipping State) | 369 из 636 | Invoice.shippingAddressState | перенос | реализовано (этап 04.3) | ok: Invoice.shippingAddressState varchar(100) |
| `vtiger_invoicebillads.bill_code` | bill_code (Billing Code) | 576 из 636 | Invoice.billingAddressPostalCode | перенос | реализовано (этап 04.3) | ok: Invoice.billingAddressPostalCode varchar(40) |
| `vtiger_invoiceshipads.ship_code` | ship_code (Shipping Code) | 564 из 636 | Invoice.shippingAddressPostalCode | перенос | реализовано (этап 04.3) | ok: Invoice.shippingAddressPostalCode varchar(40) |
| `vtiger_invoicebillads.bill_country` | bill_country (Billing Country) | 631 из 636 | Invoice.billingAddressCountry | перенос | реализовано (этап 04.3) | ok: Invoice.billingAddressCountry varchar(100) |
| `vtiger_invoiceshipads.ship_country` | ship_country (Shipping Country) | 631 из 636 | Invoice.shippingAddressCountry | перенос | реализовано (этап 04.3) | ok: Invoice.shippingAddressCountry varchar(100) |
| `vtiger_invoice.s_h_amount` | hdnS_H_Amount (S&H Amount) | 0 из 636 | Invoice.shippingAmount | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: Invoice.shippingAmount currency decimal(25,8) |
| `vtiger_invoice.terms_conditions` | terms_conditions (Terms & Conditions) | 636 из 636 | Invoice.termsAndConditions | перенос | реализовано (этап 04.3) | ok: Invoice.termsAndConditions text |
| `vtiger_crmentity.description` | description (Description) | 6 из 636 | Invoice.description | перенос | реализовано (этап 04.3) | ok: Invoice.description text |
| `vtiger_inventoryproductrel.productid` | productid (Item Name) | 712 из 712 | InvoiceItem.product | перенос | реализовано (этап 04.3) | ok: InvoiceItem.product link |
| `vtiger_inventoryproductrel.quantity` | quantity (Quantity) | 712 из 712 | InvoiceItem.quantity | перенос | реализовано (этап 04.3) | ok: InvoiceItem.quantity decimal decimal(25,3) |
| `vtiger_inventoryproductrel.listprice` | listprice (List Price) | 712 из 712 | InvoiceItem.unitPrice | перенос | реализовано (этап 04.3) | ok: InvoiceItem.unitPrice currency decimal(27,8) |
| `vtiger_inventoryproductrel.comment` | comment (Item Comment) | 685 из 712 | InvoiceItem.description | перенос | реализовано (этап 04.3) | ok: InvoiceItem.description text |
| `vtiger_inventoryproductrel.discount_amount` | discount_amount (Item Discount Amount) | 2 из 712 | InvoiceItem.discountAmount | перенос | реализовано (этап 04.3) | ok: InvoiceItem.discountAmount currency decimal(27,8) |
| `vtiger_inventoryproductrel.discount_percent` | discount_percent (Item Discount Percent) | 0 из 712 | InvoiceItem.discountPercent | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: InvoiceItem.discountPercent decimal decimal(7,3) |
| `vtiger_inventoryproductrel.tax1` | tax1 (НДС) | 211 из 712 | InvoiceItem.taxRate | перенос | реализовано (этап 04.3) | ok: InvoiceItem.taxRate decimal decimal(7,3) |
| `vtiger_inventoryproductrel.tax2` | tax2 (Tax2) | 0 из 712 | InvoiceItem.vtigerData.tax2 | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: InvoiceItem.vtigerData jsonObject |
| `vtiger_inventoryproductrel.tax3` | tax3 (Tax3) | 0 из 712 | InvoiceItem.vtigerData.tax3 | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: InvoiceItem.vtigerData jsonObject |
| `vtiger_invoice.s_h_percent` | hdnS_H_Percent (S&H Percent) | 0 из 636 | Invoice.shippingTaxPercent | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: Invoice.shippingTaxPercent decimal decimal(25,3) |
| `vtiger_invoice.discount_percent` | hdnDiscountPercent (Discount Percent) | 0 из 636 | Invoice.discountPercent | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: Invoice.discountPercent decimal decimal(25,3) |
| `vtiger_invoice.discount_amount` | hdnDiscountAmount (Discount Amount) | 1 из 636 | Invoice.discountAmount | перенос | реализовано (этап 04.3) | ok: Invoice.discountAmount currency decimal(25,8) |
| `vtiger_inventoryproductrel.image` | image (Image) | 0 из 712 | — | исключено | решено | пустое служебное поле |
| `vtiger_inventoryproductrel.purchase_cost` | purchase_cost (Purchase Cost) | 0 из 712 | InvoiceItem.purchaseCost | рабочее поле, в источнике пусто | реализовано (этап 04.3) | пусто в источнике; ok: InvoiceItem.purchaseCost currency decimal(27,8) |
| `vtiger_inventoryproductrel.margin` | margin (Margin) | 486 из 712 | InvoiceItem.margin | перенос | реализовано (этап 04.3) | ok: InvoiceItem.margin currency decimal(27,8) |
| `vtiger_invoice.region_id` | region_id (Tax Region) | 0 из 636 | sourceFormula + vtigerData.region_id | перенос | реализовано (этап 04.3) | ok: Invoice.sourceFormula enum; Invoice.vtigerData jsonObject |
| `vtiger_invoicecf.tax` | tax (tax) | 2 из 636 | vtigerData.tax | архив | реализовано (этап 04.3) | ok: Invoice.vtigerData jsonObject |

## Поля: Акты (Act)

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_sp_act.act_no` | act_no (Act No) | 403 из 404 | Act.number | перенос | реализовано (этап 04.5) | ok: Act.number varchar(100) |
| `vtiger_sp_act.subject` | subject (Subject) | 404 из 404 | Act.name | перенос | реализовано (этап 04.5) | ok: Act.name varchar(255) |
| `vtiger_sp_act.salesorderid` | salesorder_id (Sales Order) | 0 из 404 | — | исключено | решено | у актов пусто — поле не создаётся (finance-contract.md §11, Act) |
| `vtiger_sp_act.actdate` | actdate (Act Date) | 403 из 404 | Act.dateAct | перенос | реализовано (этап 04.5) | ok: Act.dateAct date |
| `vtiger_crmentity.smownerid` | assigned_user_id (Assigned To) | 404 из 404 | Act.assignedUser / teams | перенос | реализовано (этап 04.5) | ok: Act.assignedUser link; Act.teams linkMultiple |
| `vtiger_sp_act.accountid` | account_id (Account Name) | 404 из 404 | Act.account | перенос | реализовано (этап 04.5) | ok: Act.account link |
| `vtiger_crmentity.createdtime` | createdtime (Created Time) | 404 из 404 | Act.createdAt | перенос | реализовано (этап 04.5) | ok: Act.createdAt datetime |
| `vtiger_sp_act.contactid` | contact_id (Contact Name) | 6 из 404 | Act.contact | перенос | реализовано (этап 04.5) | ok: Act.contact link |
| `vtiger_crmentity.modifiedtime` | modifiedtime (Modified Time) | 404 из 404 | Act.modifiedAt | перенос | реализовано (этап 04.5) | ok: Act.modifiedAt datetime |
| `vtiger_sp_act.sp_actstatus` | sp_actstatus (Status) | 390 из 404 | Act.status | перенос | реализовано (этап 04.5) | ok: Act.status enum |
| `vtiger_sp_act.adjustment` | txtAdjustment (Adjustment) | 0 из 404 | Act.adjustment | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: Act.adjustment currency decimal(25,8) |
| `vtiger_sp_act.subtotal` | hdnSubTotal (Sub Total) | 404 из 404 | Act.subtotal | перенос | реализовано (этап 04.5) | ok: Act.subtotal currency decimal(25,8) |
| `vtiger_sp_act.total` | hdnGrandTotal (Total) | 404 из 404 | Act.grandTotal | перенос | реализовано (этап 04.5) | ok: Act.grandTotal currency decimal(25,8) |
| `vtiger_sp_act.taxtype` | hdnTaxType (Tax Type) | 404 из 404 | Act.taxMode | перенос | реализовано (этап 04.5) | ok: Act.taxMode enum |
| `vtiger_sp_act.s_h_amount` | hdnS_H_Amount (S&H Amount) | 0 из 404 | Act.shippingAmount | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: Act.shippingAmount currency decimal(25,8) |
| `vtiger_sp_act.currency_id` | currency_id (Currency) | 404 из 404 | Act.currency | перенос | реализовано (этап 04.5) | ok: Act: валюта RUB (12 денежных полей decimal, onlyDefaultCurrency) |
| `vtiger_sp_act.conversion_rate` | conversion_rate (Conversion Rate) | 404 из 404 | — | исключено | решено | всегда 1.000 (одна валюта) |
| `vtiger_crmentity.modifiedby` | modifiedby (Last Modified By) | 404 из 404 | Act.modifiedBy | перенос | реализовано (этап 04.5) | ok: Act.modifiedBy link |
| `vtiger_crmentity.source` | source (Source) | 404 из 404 | — | исключено | решено | технический канал создания записи Vtiger (CRM/WEBSERVICE) |
| `vtiger_sp_act.tags` | tags (tags) | 0 из 404 | — | исключено | решено | пусто в источнике (теги — vtiger_freetagged_objects) |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 404 из 404 | Act.createdBy | перенос | реализовано (этап 04.5) | ok: Act.createdBy link |
| `vtiger_crmentity_user_field.starred` | starred (starred) | 0 из 404 | — | исключено | решено | персональная «звёздочка» пользователя (истинных значений — единицы) |
| `vtiger_sp_act.pre_tax_total` | pre_tax_total (Pre Tax Total) | 404 из 404 | Act.preTaxTotal | перенос | реализовано (этап 04.5) | ok: Act.preTaxTotal currency decimal(25,8) |
| `vtiger_sp_act.spcompany` | spcompany (Self Company) | 404 из 404 | legalEntity + vtigerData.spcompany | перенос | реализовано (этап 04.5) | ok: Act.legalEntity link; Act.vtigerData jsonObject |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 404 из 404 | Act.createdBy | перенос | реализовано (этап 04.5) | ok: Act.createdBy link |
| `vtiger_sp_actbillads.bill_street` | bill_street (Billing Address) | 404 из 404 | Act.billingAddressStreet | перенос | реализовано (этап 04.5) | ok: Act.billingAddressStreet text |
| `vtiger_sp_actshipads.ship_street` | ship_street (Shipping Address) | 404 из 404 | Act.shippingAddressStreet | перенос | реализовано (этап 04.5) | ok: Act.shippingAddressStreet text |
| `vtiger_sp_actbillads.bill_pobox` | bill_pobox (Billing Po Box) | 0 из 404 | vtigerData.bill_pobox | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: Act.vtigerData jsonObject |
| `vtiger_sp_actshipads.ship_pobox` | ship_pobox (Shipping Po Box) | 40 из 404 | vtigerData.ship_pobox | архив | реализовано (этап 04.5) | ok: Act.vtigerData jsonObject |
| `vtiger_sp_actbillads.bill_city` | bill_city (Billing City) | 404 из 404 | Act.billingAddressCity | перенос | реализовано (этап 04.5) | ok: Act.billingAddressCity varchar(100) |
| `vtiger_sp_actshipads.ship_city` | ship_city (Shipping City) | 404 из 404 | Act.shippingAddressCity | перенос | реализовано (этап 04.5) | ok: Act.shippingAddressCity varchar(100) |
| `vtiger_sp_actbillads.bill_state` | bill_state (Billing State) | 202 из 404 | Act.billingAddressState | перенос | реализовано (этап 04.5) | ok: Act.billingAddressState varchar(100) |
| `vtiger_sp_actshipads.ship_state` | ship_state (Shipping State) | 206 из 404 | Act.shippingAddressState | перенос | реализовано (этап 04.5) | ok: Act.shippingAddressState varchar(100) |
| `vtiger_sp_actbillads.bill_code` | bill_code (Billing Code) | 401 из 404 | Act.billingAddressPostalCode | перенос | реализовано (этап 04.5) | ok: Act.billingAddressPostalCode varchar(40) |
| `vtiger_sp_actshipads.ship_code` | ship_code (Shipping Code) | 401 из 404 | Act.shippingAddressPostalCode | перенос | реализовано (этап 04.5) | ok: Act.shippingAddressPostalCode varchar(40) |
| `vtiger_sp_actbillads.bill_country` | bill_country (Billing Country) | 403 из 404 | Act.billingAddressCountry | перенос | реализовано (этап 04.5) | ok: Act.billingAddressCountry varchar(100) |
| `vtiger_sp_actshipads.ship_country` | ship_country (Shipping Country) | 403 из 404 | Act.shippingAddressCountry | перенос | реализовано (этап 04.5) | ok: Act.shippingAddressCountry varchar(100) |
| `vtiger_crmentity.description` | description (Description) | 1 из 404 | Act.description | перенос | реализовано (этап 04.5) | ok: Act.description text |
| `vtiger_inventoryproductrel.productid` | productid (Item Name) | 417 из 417 | ActItem.product | перенос | реализовано (этап 04.5) | ok: ActItem.product link |
| `vtiger_inventoryproductrel.quantity` | quantity (Quantity) | 417 из 417 | ActItem.quantity | перенос | реализовано (этап 04.5) | ok: ActItem.quantity decimal decimal(25,3) |
| `vtiger_inventoryproductrel.listprice` | listprice (List Price) | 417 из 417 | ActItem.unitPrice | перенос | реализовано (этап 04.5) | ok: ActItem.unitPrice currency decimal(27,8) |
| `vtiger_inventoryproductrel.comment` | comment (Item Comment) | 406 из 417 | ActItem.description | перенос | реализовано (этап 04.5) | ok: ActItem.description text |
| `vtiger_inventoryproductrel.discount_amount` | discount_amount (Item Discount Amount) | 1 из 417 | ActItem.discountAmount | перенос | реализовано (этап 04.5) | ok: ActItem.discountAmount currency decimal(27,8) |
| `vtiger_inventoryproductrel.discount_percent` | discount_percent (Item Discount Percent) | 0 из 417 | ActItem.discountPercent | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: ActItem.discountPercent decimal decimal(7,3) |
| `vtiger_inventoryproductrel.tax1` | tax1 (НДС) | 0 из 417 | ActItem.taxRate | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: ActItem.taxRate decimal decimal(7,3) |
| `vtiger_inventoryproductrel.tax2` | tax2 (Tax2) | 0 из 417 | ActItem.vtigerData.tax2 | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: ActItem.vtigerData jsonObject |
| `vtiger_inventoryproductrel.tax3` | tax3 (Tax3) | 0 из 417 | ActItem.vtigerData.tax3 | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: ActItem.vtigerData jsonObject |
| `vtiger_sp_act.s_h_percent` | hdnS_H_Percent (S&H Percent) | 0 из 404 | Act.shippingTaxPercent | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: Act.shippingTaxPercent decimal |
| `vtiger_sp_act.discount_percent` | hdnDiscountPercent (Discount Percent) | 0 из 404 | Act.discountPercent | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: Act.discountPercent decimal decimal(25,3) |
| `vtiger_sp_act.discount_amount` | hdnDiscountAmount (Discount Amount) | 0 из 404 | Act.discountAmount | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: Act.discountAmount currency decimal(25,8) |
| `vtiger_inventoryproductrel.image` | image (Image) | 0 из 417 | — | исключено | решено | пустое служебное поле |
| `vtiger_inventoryproductrel.purchase_cost` | purchase_cost (Purchase Cost) | 0 из 417 | ActItem.purchaseCost | рабочее поле, в источнике пусто | реализовано (этап 04.5) | пусто в источнике; ok: ActItem.purchaseCost currency decimal(27,8) |
| `vtiger_inventoryproductrel.margin` | margin (Margin) | 417 из 417 | ActItem.margin | перенос | реализовано (этап 04.5) | ok: ActItem.margin currency decimal(27,8) |
| `vtiger_sp_act.region_id` | region_id (Tax Region) | 0 из 404 | sourceFormula + vtigerData.region_id | перенос | реализовано (этап 04.5) | ok: Act.sourceFormula enum; Act.vtigerData jsonObject |

## Поля: Платежи (SPPayments → Payment)

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `sp_payments.pay_date` | pay_date (Pay date) | 799 из 799 | datePaid | перенос | реализовано (этап 04.4) | ok: Payment.datePaid date |
| `sp_payments.pay_type` | pay_type (Pay type) | 799 из 799 | direction | перенос | реализовано (этап 04.4) | ok: Payment.direction enum |
| `sp_payments.payer` | payer (Payer) | 756 из 799 | payer (Account\|Contact\|Vendor) | перенос | реализовано (этап 04.4) | ok: Payment.payer linkParent |
| `sp_payments.pay_no` | pay_no (Pay No) | 799 из 799 | number | перенос | реализовано (этап 04.4) | ok: Payment.number varchar(100) |
| `sp_payments.related_to` | related_to (Invoice To) | 623 из 799 | PaymentAllocation.invoice\|salesOrder | перенос | реализовано (этап 04.4) | ok: PaymentAllocation.invoice link; PaymentAllocation.salesOrder link |
| `sp_payments.type_payment` | type_payment (Type payment) | 797 из 799 | method | перенос | реализовано (этап 04.4) | ok: Payment.method enum |
| `sp_payments.amount` | amount (Amount) | 798 из 799 | amount | перенос | реализовано (этап 04.4) | ok: Payment.amount currency decimal(25,8) |
| `vtiger_crmentity.smownerid` | assigned_user_id (Assigned To) | 799 из 799 | assignedUser / teams | перенос | реализовано (этап 04.4) | ok: Payment.assignedUser link; Payment.teams linkMultiple |
| `sp_payments.spstatus` | spstatus (Spstatus) | 781 из 799 | status | перенос | реализовано (этап 04.4) | ok: Payment.status enum |
| `vtiger_crmentity.createdtime` | createdtime (Created Time) | 799 из 799 | createdAt | перенос | реализовано (этап 04.4) | ok: Payment.createdAt datetime |
| `vtiger_crmentity.modifiedtime` | modifiedtime (Modified Time) | 799 из 799 | modifiedAt | перенос | реализовано (этап 04.4) | ok: Payment.modifiedAt datetime |
| `vtiger_crmentity.modifiedby` | modifiedby (Last Modified By) | 799 из 799 | modifiedBy | перенос | реализовано (этап 04.4) | ok: Payment.modifiedBy link |
| `vtiger_crmentity.source` | source (Source) | 799 из 799 | — | исключено | решено | технический канал создания записи Vtiger (CRM/WEBSERVICE) |
| `sp_payments.tags` | tags (tags) | 0 из 799 | — | исключено | решено | пусто в источнике (теги — vtiger_freetagged_objects) |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 799 из 799 | createdBy | перенос | реализовано (этап 04.4) | ok: Payment.createdBy link |
| `vtiger_crmentity_user_field.starred` | starred (starred) | 0 из 799 | — | исключено | решено | персональная «звёздочка» пользователя (истинных значений — единицы) |
| `sp_payments.spcompany` | spcompany (Self Company) | 611 из 799 | legalEntity + vtigerData.spcompany | перенос | реализовано (этап 04.4) | ok: Payment.legalEntity link; Payment.vtigerData jsonObject |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 799 из 799 | createdBy | перенос | реализовано (этап 04.4) | ok: Payment.createdBy link |
| `sp_payments.doc_no` | doc_no (Document no) | 657 из 799 | documentNumber | перенос | реализовано (этап 04.4) | ok: Payment.documentNumber varchar(100) |
| `sp_payments.debit` | debit (Debit) | 0 из 799 | vtigerData.debit | рабочее поле, в источнике пусто | реализовано (этап 04.4) | пусто в источнике; ok: Payment.vtigerData jsonObject |
| `sp_payments.pay_details` | pay_details (Pay details) | 663 из 799 | purpose | перенос | реализовано (этап 04.4) | ok: Payment.purpose varchar(255) |
| `sp_payments.coracc_subacc` | coracc_subacc (Corresponding Account, Subaccount) | 0 из 799 | vtigerData.coracc_subacc | рабочее поле, в источнике пусто | реализовано (этап 04.4) | пусто в источнике; ok: Payment.vtigerData jsonObject |
| `sp_payments.analytics_code` | analytics_code (Analytics Code) | 1 из 799 | vtigerData.analytics_code | архив | реализовано (этап 04.4) | ok: Payment.vtigerData jsonObject |
| `sp_payments.target_code` | target_code (Target Code) | 0 из 799 | vtigerData.target_code | рабочее поле, в источнике пусто | реализовано (этап 04.4) | пусто в источнике; ok: Payment.vtigerData jsonObject |
| `vtiger_crmentity.description` | description (Description) | 41 из 799 | description | перенос | реализовано (этап 04.4) | ok: Payment.description text |
| `sp_paymentscf.cf_1198` | cf_1198 (Расчётный счёт) | 209 из 799 | counterpartyAccount | перенос | реализовано (этап 04.4) | ok: Payment.counterpartyAccount varchar(50) |
| `sp_paymentscf.cf_1200` | cf_1200 (БИК банка) | 190 из 799 | counterpartyBic | перенос | реализовано (этап 04.4) | ok: Payment.counterpartyBic varchar(9) |
| `sp_paymentscf.cf_1202` | cf_1202 (Название банка) | 208 из 799 | counterpartyBankName | перенос | реализовано (этап 04.4) | ok: Payment.counterpartyBankName varchar(50) |
| `sp_paymentscf.cf_1204` | cf_1204 (Номер банковской трансакции) | 188 из 799 | bankTransactionId | перенос | реализовано (этап 04.4) | ok: Payment.bankTransactionId varchar(100) |
| `sp_paymentscf.cf_1380` | cf_1380 (Валютный счет) | 1 из 799 | isForeignCurrencyAccount | перенос | реализовано (этап 04.4) | ok: Payment.isForeignCurrencyAccount bool |

## Поля: Заказы поставщикам (PurchaseOrder): записей нет, сущность не создаётся

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_purchaseorder.subject` | subject (Subject) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.purchaseorder_no` | purchaseorder_no (PurchaseOrder No) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.vendorid` | vendor_id (Vendor Name) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.requisition_no` | requisition_no (Requisition No) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.tracking_no` | tracking_no (Tracking Number) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.contactid` | contact_id (Contact Name) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.duedate` | duedate (Due Date) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.carrier` | carrier (Carrier) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.adjustment` | txtAdjustment (Adjustment) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.salescommission` | salescommission (Sales Commission) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.exciseduty` | exciseduty (Excise Duty) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.total` | hdnGrandTotal (Total) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.subtotal` | hdnSubTotal (Sub Total) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.taxtype` | hdnTaxType (Tax Type) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.s_h_amount` | hdnS_H_Amount (S&H Amount) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.postatus` | postatus (Status) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_crmentity.smownerid` | assigned_user_id (Assigned To) | 0 из 0 | assignedUser / teams | пусто | предложено | пусто — данных нет |
| `vtiger_crmentity.createdtime` | createdtime (Created Time) | 0 из 0 | createdAt | пусто | предложено | пусто — данных нет |
| `vtiger_crmentity.modifiedtime` | modifiedtime (Modified Time) | 0 из 0 | modifiedAt | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.currency_id` | currency_id (Currency) | 0 из 0 | currency | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.conversion_rate` | conversion_rate (Conversion Rate) | 0 из 0 | — | исключено | предложено | всегда 1.000 (одна валюта) |
| `vtiger_crmentity.modifiedby` | modifiedby (Last Modified By) | 0 из 0 | modifiedBy | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.pre_tax_total` | pre_tax_total (Pre Tax Total) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.paid` | paid (Paid) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.balance` | balance (Balance) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.spcompany` | spcompany (Self Company) | 0 из 0 | legalEntity + vtigerData.spcompany | пусто | предложено | пусто — данных нет |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 0 из 0 | createdBy | пусто | предложено | пусто — данных нет |
| `vtiger_crmentity.source` | source (Source) | 0 из 0 | — | исключено | предложено | технический канал создания записи Vtiger (CRM/WEBSERVICE) |
| `vtiger_crmentity_user_field.starred` | starred (starred) | 0 из 0 | — | исключено | предложено | персональная «звёздочка» пользователя (истинных значений — единицы) |
| `vtiger_purchaseorder.tags` | tags (tags) | 0 из 0 | — | исключено | предложено | пусто в источнике (теги — vtiger_freetagged_objects) |
| `vtiger_pobillads.bill_street` | bill_street (Billing Address) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_poshipads.ship_street` | ship_street (Shipping Address) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_pobillads.bill_pobox` | bill_pobox (Billing Po Box) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_poshipads.ship_pobox` | ship_pobox (Shipping Po Box) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_pobillads.bill_city` | bill_city (Billing City) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_poshipads.ship_city` | ship_city (Shipping City) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_pobillads.bill_state` | bill_state (Billing State) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_poshipads.ship_state` | ship_state (Shipping State) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_pobillads.bill_code` | bill_code (Billing Code) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_poshipads.ship_code` | ship_code (Shipping Code) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_pobillads.bill_country` | bill_country (Billing Country) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_poshipads.ship_country` | ship_country (Shipping Country) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.terms_conditions` | terms_conditions (Terms & Conditions) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_crmentity.description` | description (Description) | 0 из 0 | description | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.productid` | productid (Item Name) | 0 из 0 | PurchaseOrderItem.product | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.quantity` | quantity (Quantity) | 0 из 0 | PurchaseOrderItem.quantity | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.listprice` | listprice (List Price) | 0 из 0 | PurchaseOrderItem.unitPrice | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.comment` | comment (Item Comment) | 0 из 0 | PurchaseOrderItem.description | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.discount_amount` | discount_amount (Item Discount Amount) | 0 из 0 | PurchaseOrderItem.discountAmount | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.discount_percent` | discount_percent (Item Discount Percent) | 0 из 0 | PurchaseOrderItem.discountPercent | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.tax1` | tax1 (НДС) | 0 из 0 | PurchaseOrderItem.taxRate | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.tax2` | tax2 (Tax2) | 0 из 0 | PurchaseOrderItem.vtigerData.tax2 | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.tax3` | tax3 (Tax3) | 0 из 0 | PurchaseOrderItem.vtigerData.tax3 | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.s_h_percent` | hdnS_H_Percent (S&H Percent) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.discount_percent` | hdnDiscountPercent (Discount Percent) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseorder.discount_amount` | hdnDiscountAmount (Discount Amount) | 0 из 0 | — | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.image` | image (Image) | 0 из 0 | — | исключено | предложено | пустое служебное поле |
| `vtiger_purchaseorder.region_id` | region_id (Tax Region) | 0 из 0 | sourceFormula + vtigerData.region_id | пусто | предложено | пусто — данных нет |
| `vtiger_purchaseordercf.tax` | tax (tax) | 0 из 0 | — | пусто | предложено | пусто — данных нет |

## Поля: Накладные (Consignment → VtigerArchive, только чтение)

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_sp_consignment.consignment_no` | consignment_no (Consignment No) | 1 из 1 | VtigerArchive.data.consignment_no | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.subject` | subject (Subject) | 1 из 1 | VtigerArchive.data.subject | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.invoiceid` | invoice_id (Invoice Name) | 1 из 1 | VtigerArchive.data.invoice_id | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.consignmentdate` | consignmentdate (Consignment Date) | 1 из 1 | VtigerArchive.data.consignmentdate | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.salesorderid` | salesorder_id (Sales Order) | 0 из 1 | VtigerArchive.data.salesorder_id | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignment.accountid` | account_id (Account Name) | 1 из 1 | VtigerArchive.data.account_id | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_crmentity.smownerid` | assigned_user_id (Assigned To) | 1 из 1 | VtigerArchive.data.assigned_user_id | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.contactid` | contact_id (Contact Name) | 0 из 1 | VtigerArchive.data.contact_id | пусто | предложено | пусто — данных нет |
| `vtiger_crmentity.createdtime` | createdtime (Created Time) | 1 из 1 | VtigerArchive.data.createdtime | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.sp_consignmentstatus` | sp_consignmentstatus (Status) | 0 из 1 | VtigerArchive.data.sp_consignmentstatus | пусто | предложено | пусто — данных нет |
| `vtiger_crmentity.modifiedtime` | modifiedtime (Modified Time) | 1 из 1 | VtigerArchive.data.modifiedtime | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.adjustment` | txtAdjustment (Adjustment) | 0 из 1 | VtigerArchive.data.txtAdjustment | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignment.subtotal` | hdnSubTotal (Sub Total) | 1 из 1 | VtigerArchive.data.hdnSubTotal | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.total` | hdnGrandTotal (Total) | 1 из 1 | VtigerArchive.data.hdnGrandTotal | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.taxtype` | hdnTaxType (Tax Type) | 1 из 1 | VtigerArchive.data.hdnTaxType | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.s_h_amount` | hdnS_H_Amount (S&H Amount) | 0 из 1 | VtigerArchive.data.hdnS_H_Amount | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignment.currency_id` | currency_id (Currency) | 1 из 1 | VtigerArchive.data.currency_id | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.conversion_rate` | conversion_rate (Conversion Rate) | 1 из 1 | VtigerArchive.data.conversion_rate | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_crmentity.modifiedby` | modifiedby (Last Modified By) | 1 из 1 | VtigerArchive.data.modifiedby | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_crmentity.source` | source (Source) | 1 из 1 | VtigerArchive.data.source | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.tags` | tags (tags) | 0 из 1 | VtigerArchive.data.tags | пусто | предложено | пусто — данных нет |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 1 из 1 | VtigerArchive.data.created_user_id | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_crmentity_user_field.starred` | starred (starred) | 0 из 1 | VtigerArchive.data.starred | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignment.pre_tax_total` | pre_tax_total (Pre Tax Total) | 1 из 1 | VtigerArchive.data.pre_tax_total | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.spcompany` | spcompany (Self Company) | 1 из 1 | VtigerArchive.data.spcompany | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_crmentity.smcreatorid` | created_user_id (Created By) | 1 из 1 | VtigerArchive.data.created_user_id | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.has_goods_consignment` | has_goods_consignment (Has Goods Consignment) | 1 из 1 | VtigerArchive.data.has_goods_consignment | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.goods_consignment_no` | goods_consignment_no (Goods Consignment No) | 1 из 1 | VtigerArchive.data.goods_consignment_no | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentbillads.bill_street` | bill_street (Billing Address) | 1 из 1 | VtigerArchive.data.bill_street | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentshipads.ship_street` | ship_street (Shipping Address) | 1 из 1 | VtigerArchive.data.ship_street | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentbillads.bill_pobox` | bill_pobox (Billing Po Box) | 0 из 1 | VtigerArchive.data.bill_pobox | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignmentshipads.ship_pobox` | ship_pobox (Shipping Po Box) | 0 из 1 | VtigerArchive.data.ship_pobox | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignmentbillads.bill_city` | bill_city (Billing City) | 1 из 1 | VtigerArchive.data.bill_city | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentshipads.ship_city` | ship_city (Shipping City) | 1 из 1 | VtigerArchive.data.ship_city | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentbillads.bill_state` | bill_state (Billing State) | 1 из 1 | VtigerArchive.data.bill_state | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentshipads.ship_state` | ship_state (Shipping State) | 1 из 1 | VtigerArchive.data.ship_state | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentbillads.bill_code` | bill_code (Billing Code) | 1 из 1 | VtigerArchive.data.bill_code | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentshipads.ship_code` | ship_code (Shipping Code) | 1 из 1 | VtigerArchive.data.ship_code | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentbillads.bill_country` | bill_country (Billing Country) | 1 из 1 | VtigerArchive.data.bill_country | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentshipads.ship_country` | ship_country (Shipping Country) | 1 из 1 | VtigerArchive.data.ship_country | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_crmentity.description` | description (Description) | 0 из 1 | VtigerArchive.data.description | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.productid` | productid (Item Name) | 3 из 3 | VtigerArchive.data.productid | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_inventoryproductrel.quantity` | quantity (Quantity) | 3 из 3 | VtigerArchive.data.quantity | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_inventoryproductrel.listprice` | listprice (List Price) | 3 из 3 | VtigerArchive.data.listprice | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_inventoryproductrel.comment` | comment (Item Comment) | 3 из 3 | VtigerArchive.data.comment | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_inventoryproductrel.discount_amount` | discount_amount (Item Discount Amount) | 0 из 3 | VtigerArchive.data.discount_amount | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.discount_percent` | discount_percent (Item Discount Percent) | 0 из 3 | VtigerArchive.data.discount_percent | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.tax1` | tax1 (НДС) | 0 из 3 | VtigerArchive.data.tax1 | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.tax2` | tax2 (Tax2) | 0 из 3 | VtigerArchive.data.tax2 | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.tax3` | tax3 (Tax3) | 0 из 3 | VtigerArchive.data.tax3 | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignment.s_h_percent` | hdnS_H_Percent (S&H Percent) | 0 из 1 | VtigerArchive.data.hdnS_H_Percent | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignment.discount_percent` | hdnDiscountPercent (Discount Percent) | 0 из 1 | VtigerArchive.data.hdnDiscountPercent | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignment.discount_amount` | hdnDiscountAmount (Discount Amount) | 0 из 1 | VtigerArchive.data.hdnDiscountAmount | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.image` | image (Image) | 0 из 3 | VtigerArchive.data.image | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.purchase_cost` | purchase_cost (Purchase Cost) | 0 из 3 | VtigerArchive.data.purchase_cost | пусто | предложено | пусто — данных нет |
| `vtiger_inventoryproductrel.margin` | margin (Margin) | 3 из 3 | VtigerArchive.data.margin | архив | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignment.region_id` | region_id (Tax Region) | 0 из 1 | VtigerArchive.data.region_id | перенос | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |

## Поля: Строки VTEItems: дубль строк документов, исключены (D-09)

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_vteitems.related_to` | related_to (Related to) | 286 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.productid` | productid (Item Name) | 286 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.quantity` | quantity (Quantity) | 286 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.listprice` | listprice (List Price) | 286 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.discount_amount` | discount_amount (Item Discount Amount) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.discount_percent` | discount_percent (Item Discount Percent) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.tax1` | tax1 (VAT) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.tax2` | tax2 (Sales) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.tax3` | tax3 (Service) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.tax_total` | tax_total (Tax) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.image` | image (Image) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.purchase_cost` | purchase_cost (Purchase Cost) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.margin` | margin (Margin) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.total` | total (Total) | 286 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.net_price` | net_price (Net Price) | 286 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.comment` | comment (Item Comment) | 271 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_crmentity.source` | source (Source) | 286 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_crmentity_user_field.starred` | starred (starred) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |
| `vtiger_vteitems.tags` | tags (tags) | 0 из 286 | — | исключено | решено | модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; 1 расхождение суммы — в отчёт; решение владельца, Q-12) |

## Поля: Ссылки других модулей на финансовые документы

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_activity.invoiceid` | invoiceid (Invoice Id) | 0 из 52 | vtigerData.invoiceid | пусто | предложено | пусто — данных нет |
| `vtiger_activity.salesorder_id` | salesorder_id (Salesorder Id) | 0 из 52 | vtigerData.salesorder_id | пусто | предложено | пусто — данных нет |
| `vtiger_assets.invoiceid` | invoiceid (Invoice Name) | 0 из 3 | VtigerArchive.data.invoiceid | пусто | предложено | пусто — данных нет |

## Поля: Таблицы документов (ключи, адреса, пользовательские поля)

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_invoice.invoiceid` | — | 636 из 636 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_invoice.notes` | — | 0 из 636 | — | пусто | предложено | пусто — данных нет |
| `vtiger_invoice.invoiceterms` | — | 0 из 636 | — | пусто | предложено | пусто — данных нет |
| `vtiger_invoice.type` | — | 0 из 636 | — | пусто | предложено | пусто — данных нет |
| `vtiger_invoice.shipping` | — | 0 из 636 | — | пусто | предложено | пусто — данных нет |
| `vtiger_invoice.compound_taxes_info` | — | 636 из 636 | vtigerData.compound_taxes_info | архив | реализовано (этап 04.3) | ok: Invoice.vtigerData jsonObject |
| `vtiger_invoice_recurring_info.salesorderid` | — | 13 из 13 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_invoice_recurring_info.last_recurring_date` | — | 0 из 13 | — | пусто | предложено | пусто — данных нет |
| `vtiger_invoicebillads.invoicebilladdressid` | — | 636 из 636 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_invoicecf.invoiceid` | — | 636 из 636 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_invoiceshipads.invoiceshipaddressid` | — | 636 из 636 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_quotes.quoteid` | — | 24 из 24 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_quotes.type` | — | 0 из 24 | — | пусто | предложено | пусто — данных нет |
| `vtiger_quotes.compound_taxes_info` | — | 24 из 24 | vtigerData.compound_taxes_info | архив | реализовано (этап 04.2) | ok: Quote.vtigerData jsonObject |
| `vtiger_quotesbillads.quotebilladdressid` | — | 24 из 24 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_quotescf.quoteid` | — | 24 из 24 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_quotesshipads.quoteshipaddressid` | — | 24 из 24 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_salesorder.salesorderid` | — | 14 из 14 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_salesorder.vendorterms` | — | 0 из 14 | — | пусто | предложено | пусто — данных нет |
| `vtiger_salesorder.vendorid` | — | 0 из 14 | — | пусто | предложено | пусто — данных нет |
| `vtiger_salesorder.type` | — | 0 из 14 | — | пусто | предложено | пусто — данных нет |
| `vtiger_salesorder.compound_taxes_info` | — | 14 из 14 | vtigerData.compound_taxes_info | архив | реализовано (этап 04.2) | ok: SalesOrder.vtigerData jsonObject |
| `vtiger_salesordercf.salesorderid` | — | 14 из 14 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_sobillads.sobilladdressid` | — | 14 из 14 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_soshipads.soshipaddressid` | — | 14 из 14 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_sp_act.actid` | — | 404 из 404 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_sp_act.shipping` | — | 0 из 404 | — | пусто | предложено | пусто — данных нет |
| `vtiger_sp_act.compound_taxes_info` | — | 404 из 404 | vtigerData.compound_taxes_info | архив | реализовано (этап 04.5) | ok: Act.vtigerData jsonObject |
| `vtiger_sp_actbillads.actbilladdressid` | — | 404 из 404 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_sp_actcf.actid` | — | всего 405 | — | ключ | предложено | только ключ записи; кастомных колонок с данными нет |
| `vtiger_sp_actshipads.actshipaddressid` | — | 404 из 404 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_sp_consignment.consignmentid` | — | 1 из 1 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_sp_consignment.shipping` | — | 0 из 1 | — | пусто | предложено | пусто — данных нет |
| `vtiger_sp_consignment.compound_taxes_info` | — | 1 из 1 | VtigerArchive.data | перенос | реализовано (этап 03) | ok: VtigerArchive.data jsonObject |
| `vtiger_sp_consignmentbillads.consignmentbilladdressid` | — | 1 из 1 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_sp_consignmentcf.consignmentid` | — | всего 1 | — | ключ | предложено | только ключ записи; кастомных колонок с данными нет |
| `vtiger_sp_consignmentshipads.consignmentshipaddressid` | — | 1 из 1 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_vteitems.vteitemid` | — | 286 из 286 | (ключ записи) | ключ | предложено | ключ записи → vtigerId |
| `vtiger_vteitems.sequence` | — | 286 из 286 | — | исключено | предложено | исключено вместе с VTEItems |
| `vtiger_vteitems.level` | — | 286 из 286 | — | исключено | предложено | исключено вместе с VTEItems |
| `vtiger_vteitems.section_value` | — | 0 из 286 | — | пусто | предложено | пусто — данных нет |
| `vtiger_vteitems.running_item_value` | — | 0 из 286 | — | пусто | предложено | пусто — данных нет |
| `vtiger_vteitemscf.vteitemid` | — | всего 286 | — | ключ | предложено | только ключ записи; кастомных колонок с данными нет |

## Поля: Строки документов

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_inventorychargesrel.recordid` | — | всего 1082 | — | исключено | предложено | во всех записях значения 0 (проверено) |
| `vtiger_inventorychargesrel.charges` | — | всего 1082 | — | исключено | предложено | во всех записях значения 0 (проверено) |
| `vtiger_inventoryproductrel.id` | — | 1173 из 1173 | &lt;Doc>Item.&lt;документ> | перенос | реализовано (этап 04.5) | ok: QuoteItem.quote link; SalesOrderItem.salesOrder link; InvoiceItem.invoice link; ActItem.act link |
| `vtiger_inventoryproductrel.sequence_no` | — | 1173 из 1173 | &lt;Doc>Item.order | перенос | реализовано (этап 04.5) | ok: QuoteItem.order int; SalesOrderItem.order int; InvoiceItem.order int; ActItem.order int |
| `vtiger_inventoryproductrel.description` | — | 0 из 1173 | — | исключено | решено | пусто |
| `vtiger_inventoryproductrel.incrementondel` | — | 696 из 1173 | — | исключено | решено | складской флаг Vtiger |
| `vtiger_inventoryproductrel.lineitem_id` | — | 1173 из 1173 | &lt;Doc>Item.vtigerId | перенос | реализовано (этап 04.5) | ok: QuoteItem.vtigerId int; SalesOrderItem.vtigerId int; InvoiceItem.vtigerId int; ActItem.vtigerId int |
| `vtiger_inventoryproductrel_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |

## Поля: Таблицы платежей

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `sp_payments.payid` | — | 799 из 799 | Payment.vtigerId | перенос | реализовано (этап 04.4) | ok: Payment.vtigerId int |
| `sp_paymentscf.payid` | — | 799 из 799 | Payment.vtigerId | перенос | реализовано (этап 04.4) | ok: Payment.vtigerId int |

## Поля: Юрлицо

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_organizationdetails.organization_id` | — | всего 1 | — | исключено | решено | служебный ключ единственной строки |
| `vtiger_organizationdetails.organizationname` | — | всего 1 | LegalEntity.name | перенос | реализовано (этап 04.2) | ok: LegalEntity.name varchar(255) |
| `vtiger_organizationdetails.address` | — | всего 1 | LegalEntity.addressStreet | перенос | реализовано (этап 04.2) | ok: LegalEntity.addressStreet text |
| `vtiger_organizationdetails.city` | — | всего 1 | LegalEntity.addressCity | перенос | реализовано (этап 04.2) | ok: LegalEntity.addressCity varchar(100) |
| `vtiger_organizationdetails.state` | — | всего 1 | LegalEntity.addressState | перенос | реализовано (этап 04.2) | ok: LegalEntity.addressState varchar(100) |
| `vtiger_organizationdetails.country` | — | всего 1 | LegalEntity.addressCountry | перенос | реализовано (этап 04.2) | ok: LegalEntity.addressCountry varchar(100) |
| `vtiger_organizationdetails.code` | — | всего 1 | LegalEntity.addressPostalCode | перенос | реализовано (этап 04.2) | ok: LegalEntity.addressPostalCode varchar(40) |
| `vtiger_organizationdetails.phone` | — | всего 1 | LegalEntity.phoneNumber | перенос | реализовано (этап 04.2) | ok: LegalEntity.phoneNumber varchar(100) |
| `vtiger_organizationdetails.fax` | — | всего 1 | LegalEntity.fax | перенос | реализовано (этап 04.2) | ok: LegalEntity.fax varchar(100) |
| `vtiger_organizationdetails.website` | — | всего 1 | LegalEntity.website | перенос | реализовано (этап 04.2) | ok: LegalEntity.website url(255) |
| `vtiger_organizationdetails.logoname` | — | всего 1 | LegalEntity.logo | перенос | реализовано (этап 04.2) | ok: LegalEntity.logo image |
| `vtiger_organizationdetails.logo` | — | всего 0 | — | пусто | решено | пусто — данных нет |
| `vtiger_organizationdetails.vatid` | — | всего 0 | — | пусто | решено | пусто — данных нет |
| `vtiger_organizationdetails.inn` | — | всего 1 | LegalEntity.inn | перенос | реализовано (этап 04.2) | ok: LegalEntity.inn varchar(255) |
| `vtiger_organizationdetails.kpp` | — | всего 1 | LegalEntity.kpp | перенос | реализовано (этап 04.2) | ok: LegalEntity.kpp varchar(255) |
| `vtiger_organizationdetails.bankaccount` | — | всего 1 | LegalEntity.bankAccount | перенос | реализовано (этап 04.2) | ok: LegalEntity.bankAccount varchar(255) |
| `vtiger_organizationdetails.bankname` | — | всего 1 | LegalEntity.bankName | перенос | реализовано (этап 04.2) | ok: LegalEntity.bankName varchar(255) |
| `vtiger_organizationdetails.bankid` | — | всего 1 | LegalEntity.bic | перенос | реализовано (этап 04.2) | ok: LegalEntity.bic varchar(255) |
| `vtiger_organizationdetails.corraccount` | — | всего 1 | LegalEntity.corrAccount | перенос | реализовано (этап 04.2) | ok: LegalEntity.corrAccount varchar(255) |
| `vtiger_organizationdetails.director` | — | всего 1 | LegalEntity.director | перенос | реализовано (этап 04.2) | ok: LegalEntity.director varchar(255) |
| `vtiger_organizationdetails.bookkeeper` | — | всего 1 | LegalEntity.bookkeeper | перенос | реализовано (этап 04.2) | ok: LegalEntity.bookkeeper varchar(255) |
| `vtiger_organizationdetails.entrepreneur` | — | всего 1 | LegalEntity.entrepreneur | перенос | реализовано (этап 04.2) | ok: LegalEntity.entrepreneur varchar(255) |
| `vtiger_organizationdetails.entrepreneurreg` | — | всего 1 | LegalEntity.entrepreneurRegistration | перенос | реализовано (этап 04.2) | ok: LegalEntity.entrepreneurRegistration varchar(255) |
| `vtiger_organizationdetails.okpo` | — | всего 1 | LegalEntity.okpo | перенос | реализовано (этап 04.2) | ok: LegalEntity.okpo varchar(255) |
| `vtiger_organizationdetails.company` | — | всего 1 | LegalEntity.vtigerCompanyKey | перенос | реализовано (этап 04.2) | ok: LegalEntity.vtigerCompanyKey varchar(255) |
| `vtiger_organizationdetails_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_spcompany.spcompanyid` | — | всего 2 | LegalEntity | исключено | решено | не переносится как опции: 'Default' и 'По умолчанию' — одно юрлицо, одна запись LegalEntity (D-04) |
| `vtiger_spcompany.spcompany` | — | всего 2 | LegalEntity | исключено | решено | не переносится как опции: 'Default' и 'По умолчанию' — одно юрлицо, одна запись LegalEntity (D-04) |
| `vtiger_spcompany.presence` | — | всего 2 | LegalEntity | исключено | решено | не переносится как опции: 'Default' и 'По умолчанию' — одно юрлицо, одна запись LegalEntity (D-04) |
| `vtiger_spcompany.picklist_valueid` | — | всего 2 | LegalEntity | исключено | решено | не переносится как опции: 'Default' и 'По умолчанию' — одно юрлицо, одна запись LegalEntity (D-04) |
| `vtiger_spcompany.sortorderid` | — | всего 2 | LegalEntity | исключено | решено | не переносится как опции: 'Default' и 'По умолчанию' — одно юрлицо, одна запись LegalEntity (D-04) |
| `vtiger_spcompany.color` | — | всего 0 | LegalEntity | исключено | решено | не переносится как опции: 'Default' и 'По умолчанию' — одно юрлицо, одна запись LegalEntity (D-04) |
| `vtiger_spcompany_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |

## Поля: Налоги, валюта, доп. расходы

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_currencies.currencyid` | — | всего 138 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currencies.currency_name` | — | всего 138 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currencies.currency_code` | — | всего 138 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currencies.currency_symbol` | — | всего 138 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currencies_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_currency_info.id` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currency_info.currency_name` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currency_info.currency_code` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currency_info.currency_symbol` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currency_info.conversion_rate` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currency_info.currency_status` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currency_info.defaultid` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currency_info.deleted` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_currency_info_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_inventorycharges.chargeid` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorycharges.name` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorycharges.format` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorycharges.type` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorycharges.value` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorycharges.regions` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorycharges.istaxable` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorycharges.taxes` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorycharges.deleted` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo.taxid` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo.taxname` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo.taxlabel` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo.percentage` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo.deleted` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo.method` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo.type` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo.compoundon` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo.regions` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_inventorytaxinfo_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_productcurrencyrel.productid` | — | всего 27 | — | исключено | предложено | одна валюта, цена берётся из unit_price |
| `vtiger_productcurrencyrel.currencyid` | — | всего 27 | — | исключено | предложено | одна валюта, цена берётся из unit_price |
| `vtiger_productcurrencyrel.converted_price` | — | всего 27 | — | исключено | предложено | одна валюта, цена берётся из unit_price |
| `vtiger_productcurrencyrel.actual_price` | — | всего 27 | — | исключено | предложено | одна валюта, цена берётся из unit_price |
| `vtiger_shippingtaxinfo.taxid` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_shippingtaxinfo.taxname` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_shippingtaxinfo.taxlabel` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_shippingtaxinfo.percentage` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_shippingtaxinfo.deleted` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_shippingtaxinfo.method` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_shippingtaxinfo.type` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_shippingtaxinfo.compoundon` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_shippingtaxinfo.regions` | — | всего 1 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_shippingtaxinfo_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_taxclass.taxclassid` | — | всего 2 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_taxclass.taxclass` | — | всего 2 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_taxclass.sortorderid` | — | всего 2 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_taxclass.presence` | — | всего 2 | config | настройка | предложено | переносится как конфигурация (валюта RUB, НДС 18% исторически) |
| `vtiger_taxclass_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |

## Поля: Справочники статусов и значений

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_carrier.carrierid` | — | всего 5 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_carrier.carrier` | — | всего 5 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_carrier.presence` | — | всего 5 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_carrier.picklist_valueid` | — | всего 5 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_carrier.sortorderid` | — | всего 5 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_carrier.color` | — | всего 0 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_carrier_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_invoicestatus.invoicestatusid` | — | всего 7 | entityDefs options | справочник | реализовано (этап 04.3) | ok: опции Invoice.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_invoicestatus.invoicestatus` | — | всего 7 | entityDefs options | справочник | реализовано (этап 04.3) | ok: опции Invoice.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_invoicestatus.presence` | — | всего 7 | entityDefs options | справочник | реализовано (этап 04.3) | ok: опции Invoice.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_invoicestatus.picklist_valueid` | — | всего 7 | entityDefs options | справочник | реализовано (этап 04.3) | ok: опции Invoice.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_invoicestatus.sortorderid` | — | всего 7 | entityDefs options | справочник | реализовано (этап 04.3) | ok: опции Invoice.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_invoicestatus.color` | — | всего 0 | entityDefs options | справочник | реализовано (этап 04.3) | ok: опции Invoice.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_invoicestatus_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_pay_type.pay_typeid` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.direction (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_pay_type.pay_type` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.direction (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_pay_type.presence` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.direction (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_pay_type.picklist_valueid` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.direction (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_pay_type.sortorderid` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.direction (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_pay_type.color` | — | всего 0 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.direction (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_pay_type_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_payment_duration.payment_duration_id` | — | всего 5 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_payment_duration.payment_duration` | — | всего 5 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_payment_duration.sortorderid` | — | всего 5 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_payment_duration.presence` | — | всего 5 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_payment_duration.color` | — | всего 0 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_payment_duration_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_postatus.postatusid` | — | всего 5 | entityDefs options | исключено | предложено | не используется: модуль PurchaseOrder без записей не создаётся (finance-contract.md §1) |
| `vtiger_postatus.postatus` | — | всего 5 | entityDefs options | исключено | предложено | не используется: модуль PurchaseOrder без записей не создаётся (finance-contract.md §1) |
| `vtiger_postatus.presence` | — | всего 5 | entityDefs options | исключено | предложено | не используется: модуль PurchaseOrder без записей не создаётся (finance-contract.md §1) |
| `vtiger_postatus.picklist_valueid` | — | всего 5 | entityDefs options | исключено | предложено | не используется: модуль PurchaseOrder без записей не создаётся (finance-contract.md §1) |
| `vtiger_postatus.sortorderid` | — | всего 5 | entityDefs options | исключено | предложено | не используется: модуль PurchaseOrder без записей не создаётся (finance-contract.md §1) |
| `vtiger_postatus.color` | — | всего 0 | entityDefs options | исключено | предложено | не используется: модуль PurchaseOrder без записей не создаётся (finance-contract.md §1) |
| `vtiger_postatus_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_quotestage.quotestageid` | — | всего 9 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции Quote.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_quotestage.quotestage` | — | всего 9 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции Quote.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_quotestage.presence` | — | всего 9 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции Quote.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_quotestage.picklist_valueid` | — | всего 9 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции Quote.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_quotestage.sortorderid` | — | всего 9 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции Quote.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_quotestage.color` | — | всего 0 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции Quote.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_quotestage_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_recurring_frequency.recurring_frequency_id` | — | всего 6 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_recurring_frequency.recurring_frequency` | — | всего 6 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_recurring_frequency.sortorderid` | — | всего 6 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_recurring_frequency.presence` | — | всего 6 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_recurring_frequency.color` | — | всего 0 | entityDefs options | архив | предложено | архив: исходные значения в vtigerData (enum не создаётся; периодичность заказов закончилась в 2016, D-15) |
| `vtiger_recurring_frequency_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_sostatus.sostatusid` | — | всего 6 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции SalesOrder.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sostatus.sostatus` | — | всего 6 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции SalesOrder.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sostatus.presence` | — | всего 6 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции SalesOrder.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sostatus.picklist_valueid` | — | всего 6 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции SalesOrder.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sostatus.sortorderid` | — | всего 6 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции SalesOrder.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sostatus.color` | — | всего 0 | entityDefs options | справочник | реализовано (этап 04.2) | ok: опции SalesOrder.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sostatus_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_sp_actstatus.sp_actstatusid` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.5) | ok: опции Act.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sp_actstatus.sp_actstatus` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.5) | ok: опции Act.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sp_actstatus.presence` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.5) | ok: опции Act.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sp_actstatus.picklist_valueid` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.5) | ok: опции Act.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sp_actstatus.sortorderid` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.5) | ok: опции Act.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sp_actstatus.color` | — | всего 0 | entityDefs options | справочник | реализовано (этап 04.5) | ok: опции Act.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_sp_actstatus_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_sp_consignmentstatus.sp_consignmentstatusid` | — | всего 2 | entityDefs options | архив | предложено | архив: исходные значения в VtigerArchive.data (enum не создаётся) |
| `vtiger_sp_consignmentstatus.sp_consignmentstatus` | — | всего 2 | entityDefs options | архив | предложено | архив: исходные значения в VtigerArchive.data (enum не создаётся) |
| `vtiger_sp_consignmentstatus.presence` | — | всего 2 | entityDefs options | архив | предложено | архив: исходные значения в VtigerArchive.data (enum не создаётся) |
| `vtiger_sp_consignmentstatus.picklist_valueid` | — | всего 2 | entityDefs options | архив | предложено | архив: исходные значения в VtigerArchive.data (enum не создаётся) |
| `vtiger_sp_consignmentstatus.sortorderid` | — | всего 2 | entityDefs options | архив | предложено | архив: исходные значения в VtigerArchive.data (enum не создаётся) |
| `vtiger_sp_consignmentstatus.color` | — | всего 0 | entityDefs options | архив | предложено | архив: исходные значения в VtigerArchive.data (enum не создаётся) |
| `vtiger_sp_consignmentstatus_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_spstatus.spstatusid` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_spstatus.spstatus` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_spstatus.presence` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_spstatus.picklist_valueid` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_spstatus.sortorderid` | — | всего 4 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_spstatus.color` | — | всего 0 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.status (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_spstatus_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_type_payment.type_paymentid` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.method (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_type_payment.type_payment` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.method (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_type_payment.presence` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.method (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_type_payment.picklist_valueid` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.method (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_type_payment.sortorderid` | — | всего 2 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.method (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_type_payment.color` | — | всего 0 | entityDefs options | справочник | реализовано (этап 04.4) | ok: опции Payment.method (metadata/vtigerValueMap, D-19, Q-32) |
| `vtiger_type_payment_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |

## Поля: История статусов

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_invoicestatushistory.historyid` | — | всего 589 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_invoicestatushistory.invoiceid` | — | всего 589 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_invoicestatushistory.accountname` | — | всего 0 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_invoicestatushistory.total` | — | всего 124 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_invoicestatushistory.invoicestatus` | — | всего 589 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_invoicestatushistory.lastmodified` | — | всего 589 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_invoicestatushistory_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_sp_actstatushistory.historyid` | — | всего 51 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_sp_actstatushistory.actid` | — | всего 51 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_sp_actstatushistory.accountname` | — | всего 0 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_sp_actstatushistory.total` | — | всего 16 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_sp_actstatushistory.sp_actstatus` | — | всего 51 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_sp_actstatushistory.lastmodified` | — | всего 51 | — | исключено | решено | не переносится (решение владельца, Q-27): остаётся в защищённом снимке |
| `vtiger_sp_actstatushistory_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |

## Поля: Нумерация

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_modentity_num.num_id` | — | всего 28 | — | исключено | предложено | не переносится: используется как источник проектирования модели и настроек |
| `vtiger_modentity_num.semodule` | — | всего 28 | — | исключено | предложено | не переносится: используется как источник проектирования модели и настроек |
| `vtiger_modentity_num.prefix` | — | всего 25 | — | исключено | предложено | не переносится: используется как источник проектирования модели и настроек |
| `vtiger_modentity_num.start_id` | — | всего 28 | — | исключено | предложено | не переносится: используется как источник проектирования модели и настроек |
| `vtiger_modentity_num.cur_id` | — | всего 28 | — | исключено | предложено | не переносится: используется как источник проектирования модели и настроек |
| `vtiger_modentity_num.active` | — | всего 28 | — | исключено | предложено | не переносится: используется как источник проектирования модели и настроек |
| `vtiger_modentity_num.spcompany` | — | всего 0 | — | исключено | предложено | не переносится: используется как источник проектирования модели и настроек |
| `vtiger_modentity_num_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |

## Поля: Печатные формы, условия, уведомления

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `sp_templates.templateid` | — | всего 11 | печатные формы (этап 05) | печатная форма | реализовано (этап 05) | ok: печатные формы 5 (шаблоны SalesPlatform 10, 11, 5) |
| `sp_templates.name` | — | всего 11 | печатные формы (этап 05) | печатная форма | реализовано (этап 05) | ok: печатные формы 5 (шаблоны SalesPlatform 10, 11, 5) |
| `sp_templates.module` | — | всего 11 | печатные формы (этап 05) | печатная форма | реализовано (этап 05) | ok: печатные формы 5 (шаблоны SalesPlatform 10, 11, 5) |
| `sp_templates.template` | — | всего 11 | печатные формы (этап 05) | печатная форма | реализовано (этап 05) | ok: печатные формы 5 (шаблоны SalesPlatform 10, 11, 5) |
| `sp_templates.header_size` | — | всего 11 | печатные формы (этап 05) | печатная форма | реализовано (этап 05) | ok: печатные формы 5 (шаблоны SalesPlatform 10, 11, 5) |
| `sp_templates.footer_size` | — | всего 11 | печатные формы (этап 05) | печатная форма | реализовано (этап 05) | ok: печатные формы 5 (шаблоны SalesPlatform 10, 11, 5) |
| `sp_templates.page_orientation` | — | всего 11 | печатные формы (этап 05) | печатная форма | реализовано (этап 05) | ok: печатные формы 5 (шаблоны SalesPlatform 10, 11, 5) |
| `sp_templates.spcompany` | — | всего 11 | печатные формы (этап 05) | печатная форма | реализовано (этап 05) | ok: печатные формы 5 (шаблоны SalesPlatform 10, 11, 5) |
| `sp_templates_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_inventory_tandc.id` | — | всего 6 | termsAndConditions (умолчание) | настройка | реализовано (этап 05) | ok: умолчание termsAndConditions (Quote, SalesOrder, Invoice) |
| `vtiger_inventory_tandc.type` | — | всего 6 | termsAndConditions (умолчание) | настройка | реализовано (этап 05) | ok: умолчание termsAndConditions (Quote, SalesOrder, Invoice) |
| `vtiger_inventory_tandc.tandc` | — | всего 6 | termsAndConditions (умолчание) | настройка | реализовано (этап 05) | ok: умолчание termsAndConditions (Quote, SalesOrder, Invoice) |
| `vtiger_inventory_tandc_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_inventorynotification.notificationid` | — | всего 3 | — | исключено | решено | не переносится: стандартные уведомления Vtiger, в EspoCRM — штатные (решение владельца, Q-14) |
| `vtiger_inventorynotification.notificationname` | — | всего 3 | — | исключено | решено | не переносится: стандартные уведомления Vtiger, в EspoCRM — штатные (решение владельца, Q-14) |
| `vtiger_inventorynotification.notificationsubject` | — | всего 3 | — | исключено | решено | не переносится: стандартные уведомления Vtiger, в EspoCRM — штатные (решение владельца, Q-14) |
| `vtiger_inventorynotification.notificationbody` | — | всего 3 | — | исключено | решено | не переносится: стандартные уведомления Vtiger, в EspoCRM — штатные (решение владельца, Q-14) |
| `vtiger_inventorynotification.label` | — | всего 3 | — | исключено | решено | не переносится: стандартные уведомления Vtiger, в EspoCRM — штатные (решение владельца, Q-14) |
| `vtiger_inventorynotification.status` | — | всего 0 | — | исключено | решено | не переносится: стандартные уведомления Vtiger, в EspoCRM — штатные (решение владельца, Q-14) |
| `vtiger_inventorynotification_seq.id` | — | всего 1 | — | исключено | предложено | не переносится: счётчики EspoCRM свои; следующий номер документов задаётся настройкой нумерации |
| `vtiger_quotingtool.id` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.filename` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.module` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.body` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.header` | — | всего 0 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.content` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.footer` | — | всего 0 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.anwidget` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.description` | — | всего 0 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.deleted` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.created` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.updated` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.email_subject` | — | всего 0 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.email_content` | — | всего 0 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.mapping_fields` | — | всего 0 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.attachments` | — | всего 0 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.is_active` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.createnewrecords` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool.linkproposal` | — | всего 0 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_histories.id` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_histories.created` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_histories.updated` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_histories.deleted` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_histories.template_id` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_histories.body` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_settings.id` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_settings.template_id` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_settings.created` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_settings.updated` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_settings.description` | — | всего 0 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_settings.label_decline` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_settings.label_accept` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_settings.background` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |
| `vtiger_quotingtool_settings.expire_in_days` | — | всего 1 | — | исключено | решено | шаблон закрытого расширения VTE удалён в источнике (deleted=1); платные расширения не переносятся (решение владельца, Q-30) |

## Поля: Настройки платного расширения Quoter

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `quoter_invoice_settings.module` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.item_name` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.quantity` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.listprice` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.total` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.net_price` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.comment` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.discount_amount` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.discount_percent` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.total_fields` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.section_setting` | — | всего 0 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_invoice_settings.tax_total` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.module` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.item_name` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.quantity` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.listprice` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.total` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.net_price` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.comment` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.discount_amount` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.discount_percent` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.total_fields` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.section_setting` | — | всего 0 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_purchaseorder_settings.tax_total` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.module` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.item_name` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.quantity` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.listprice` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.total` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.net_price` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.comment` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.discount_amount` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.discount_percent` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.total_fields` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.section_setting` | — | всего 0 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_quotes_settings.tax_total` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.module` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.item_name` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.quantity` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.listprice` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.total` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.net_price` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.comment` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.discount_amount` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.discount_percent` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.total_fields` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.section_setting` | — | всего 0 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |
| `quoter_salesorder_settings.tax_total` | — | всего 1 | — | исключено | предложено | не переносится: закрытые/платные расширения VTE/ITS4You/SalesPlatform; функции оцениваются в module-decisions.md |

## Поля: Общие колонки записей (vtiger_crmentity)

| Колонка | Поле Vtiger | Непустых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---:|---|---|---|---|
| `vtiger_crmentity.crmid` | — | 6045 из 6045 | vtigerId | перенос | реализовано (этап 03) | ok: vtigerId (int, unique) у 30 сущностей |
| `vtiger_crmentity.setype` | — | 6045 из 6045 | (тип сущности) | ключ | предложено | определяет целевую сущность |

## Связи: Предложения (Quotes → Quote)

| Связь | Вид | Откуда → куда | Живых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---|---:|---|---|---|---|
| `Quotes.modifiedby` | owner | Quotes → User | 24 | modifiedBy | перенос | реализовано (этап 04.2) | ok: Quote.modifiedBy |
| `Quotes.smcreatorid` | owner | Quotes → User | 24 | createdBy | перенос | реализовано (этап 04.2) | ok: Quote.createdBy |
| `Quotes.smownerid` | owner | Quotes → User | 24 | assignedUser/teams | перенос | реализовано (этап 04.2) | ok: Quote.assignedUser; Quote.teams |
| `Quotes.productid` | field | Quotes → Services | 27 | QuoteItem.product | перенос | реализовано (этап 04.2) | ok: QuoteItem.product |
| `Quotes.accountid` | field | Quotes → Accounts | 24 | Quote.account | перенос | реализовано (этап 04.2) | ok: Quote.account |
| `Quotes.contactid` | field | Quotes → Contacts | 6 | Quote.contact | перенос | реализовано (этап 04.2) | ok: Quote.contact |
| `Quotes.inventorymanager` | owner | Quotes → User | 23 | Quote.inventoryManager (User) | перенос | реализовано (этап 04.2) | ok: Quote.inventoryManager |
| `Quotes.potentialid` | field | Quotes → Potentials | 24 | Quote.opportunity | перенос | реализовано (этап 04.2) | ok: Quote.opportunity |
| `crmentityrel:Potentials->Quotes` | m2m | Potentials → Quotes | 1 | Quote.opportunity | перенос | реализовано (этап 04.2) | ok: Quote.opportunity |
| `lines:Quotes` | lines | Quotes → lines | 27 | QuoteItem.quote | перенос | реализовано (этап 04.2) | ok: QuoteItem.quote |
| `history-link:Potentials->Quotes` | history | Potentials → Quotes | 1 | — | исключено | решено | история не переносится (Q-27) |

## Связи: Заказы (SalesOrder)

| Связь | Вид | Откуда → куда | Живых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---|---:|---|---|---|---|
| `SalesOrder.modifiedby` | owner | SalesOrder → User | 14 | modifiedBy | перенос | реализовано (этап 04.2) | ok: SalesOrder.modifiedBy |
| `SalesOrder.smcreatorid` | owner | SalesOrder → User | 14 | createdBy | перенос | реализовано (этап 04.2) | ok: SalesOrder.createdBy |
| `SalesOrder.smownerid` | owner | SalesOrder → User | 14 | assignedUser/teams | перенос | реализовано (этап 04.2) | ok: SalesOrder.assignedUser; SalesOrder.teams |
| `SalesOrder.productid` | field | SalesOrder → Services | 14 | SalesOrderItem.product | перенос | реализовано (этап 04.2) | ok: SalesOrderItem.product |
| `SalesOrder.accountid` | field | SalesOrder → Accounts | 14 | SalesOrder.account | перенос | реализовано (этап 04.2) | ok: SalesOrder.account |
| `SalesOrder.contactid` | field | SalesOrder → Contacts | 8 | SalesOrder.contact | перенос | реализовано (этап 04.2) | ok: SalesOrder.contact |
| `SalesOrder.potentialid` | field | SalesOrder → Potentials | 12 | SalesOrder.opportunity | перенос | реализовано (этап 04.2) | ok: SalesOrder.opportunity |
| `SalesOrder.quoteid` | field | SalesOrder → — | 0 | SalesOrder.quote | рабочее поле, в источнике пусто | реализовано (этап 04.2) | пусто в источнике; ok: SalesOrder.quote |
| `lines:SalesOrder` | lines | SalesOrder → lines | 14 | SalesOrderItem.salesOrder | перенос | реализовано (этап 04.2) | ok: SalesOrderItem.salesOrder |

## Связи: Счета (Invoice)

| Связь | Вид | Откуда → куда | Живых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---|---:|---|---|---|---|
| `Events.crmid` | field | Events → Accounts\|Invoice\|Leads\|Potentials | 48 | Call\|Meeting\|Task.parent | перенос | реализовано (этап 03) | ok: Call.parent; Meeting.parent; Task.parent |
| `Invoice.modifiedby` | owner | Invoice → User | 636 | modifiedBy | перенос | реализовано (этап 04.3) | ok: Invoice.modifiedBy |
| `Invoice.smcreatorid` | owner | Invoice → User | 636 | createdBy | перенос | реализовано (этап 04.3) | ok: Invoice.createdBy |
| `Invoice.smownerid` | owner | Invoice → User | 636 | assignedUser/teams | перенос | реализовано (этап 04.3) | ok: Invoice.assignedUser; Invoice.teams |
| `Invoice.productid` | field | Invoice → Products\|Services | 712 | InvoiceItem.product | перенос | реализовано (этап 04.3) | ok: InvoiceItem.product |
| `Invoice.accountid` | field | Invoice → Accounts | 636 | Invoice.account | перенос | реализовано (этап 04.3) | ok: Invoice.account |
| `Invoice.contactid` | field | Invoice → Contacts | 23 | Invoice.contact | перенос | реализовано (этап 04.3) | ok: Invoice.contact |
| `Invoice.potential_id` | field | Invoice → Potentials | 429 | Invoice.opportunity | перенос | реализовано (этап 04.3) | ok: Invoice.opportunity |
| `Invoice.salesorderid` | field | Invoice → SalesOrder | 27 | Invoice.salesOrder | перенос | реализовано (этап 04.3) | ok: Invoice.salesOrder |
| `Invoice.sp_act_id` | field | Invoice → Act | 392 | Invoice.act (belongsTo; обратная Act.invoices hasMany без ограничения 1:1) | перенос | реализовано (этап 04.5) | ok: Invoice.act |
| `crmentityrel:Accounts->Invoice` | m2m | Accounts → Invoice | 443 | Invoice.account (дублирует поле accountid) | перенос | реализовано (этап 04.3) | ok: Invoice.account |
| `crmentityrel:Contacts->Invoice` | m2m | Contacts → Invoice | 2 | Invoice.contact | перенос | реализовано (этап 04.3) | ok: Invoice.contact |
| `crmentityrel:Invoice->Calendar` | m2m | Invoice → Calendar | 1 | Task\|Call\|Meeting.parent (родитель Invoice) | перенос | реализовано (этап 04.3) | ok: Task.parent; Call.parent; Meeting.parent |
| `crmentityrel:Invoice->Consignment` | m2m | Invoice → Consignment | 1 | VtigerArchive.invoice (дублирует поле invoiceid) | перенос | реализовано (этап 04.3) | ok: VtigerArchive.invoice |
| `crmentityrel:Invoice->SPPayments` | m2m | Invoice → SPPayments | 520 | PaymentAllocation.invoice (объединение с related_to) | перенос | реализовано (этап 04.4) | ok: PaymentAllocation.invoice |
| `crmentityrel:Potentials->Invoice` | m2m | Potentials → Invoice | 20 | Invoice.opportunity | перенос | реализовано (этап 04.3) | ok: Invoice.opportunity |
| `seactivityrel:Invoice->Письмо` | m2m | Invoice → activity:Письмо | 1 | Task.parent (вид «Письмо») | перенос | реализовано (этап 04.3) | ok: Task.parent |
| `senotesrel:Invoice->Documents` | m2m | Invoice → Documents | 72 | Invoice.documents (M:N с Document) | перенос | реализовано (этап 04.3) | ok: Invoice.documents |
| `lines:Invoice` | lines | Invoice → lines | 712 | InvoiceItem.invoice | перенос | реализовано (этап 04.3) | ok: InvoiceItem.invoice |
| `invoice_act:Invoice->Act` | field | Invoice → Act | 392 | Invoice.act / Act.invoices (hasMany, без ограничения 1:1) | перенос | реализовано (этап 04.5) | ok: Invoice.act; Act.invoices |
| `history-link:Accounts->Invoice` | history | Accounts → Invoice | 443 | — | исключено | решено | история не переносится (Q-27) |
| `history-link:Contacts->Invoice` | history | Contacts → Invoice | 2 | — | исключено | решено | история не переносится (Q-27) |
| `history-link:Invoice->Calendar` | history | Invoice → Calendar | 1 | — | исключено | решено | история не переносится (Q-27) |
| `history-link:Invoice->Consignment` | history | Invoice → Consignment | 1 | — | исключено | решено | история не переносится (Q-27) |
| `history-link:Invoice->Documents` | history | Invoice → Documents | 74 | — | исключено | решено | история не переносится (Q-27) |
| `history-link:Invoice->SPPayments` | history | Invoice → SPPayments | 657 | — | исключено | решено | история не переносится (Q-27) |
| `history-link:Potentials->Invoice` | history | Potentials → Invoice | 22 | — | исключено | решено | история не переносится (Q-27) |

## Связи: Акты (Act)

| Связь | Вид | Откуда → куда | Живых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---|---:|---|---|---|---|
| `Act.modifiedby` | owner | Act → User | 404 | modifiedBy | перенос | реализовано (этап 04.5) | ok: Act.modifiedBy |
| `Act.smcreatorid` | owner | Act → User | 404 | createdBy | перенос | реализовано (этап 04.5) | ok: Act.createdBy |
| `Act.smownerid` | owner | Act → User | 404 | assignedUser/teams | перенос | реализовано (этап 04.5) | ok: Act.assignedUser; Act.teams |
| `Act.productid` | field | Act → Services | 417 | ActItem.product | перенос | реализовано (этап 04.5) | ok: ActItem.product |
| `Act.accountid` | field | Act → Accounts | 404 | Act.account | перенос | реализовано (этап 04.5) | ok: Act.account |
| `Act.contactid` | field | Act → Contacts | 6 | Act.contact | перенос | реализовано (этап 04.5) | ok: Act.contact |
| `Act.salesorderid` | field | Act → — | 0 | — (у актов пусто: поле не создаётся, finance-contract.md §11 Act) | пусто | решено | пусто — данных нет |
| `senotesrel:Act->Documents` | m2m | Act → Documents | 42 | Act.documents (M:N с Document) | перенос | реализовано (этап 04.5) | ok: Act.documents |
| `lines:Act` | lines | Act → lines | 417 | ActItem.act | перенос | реализовано (этап 04.5) | ok: ActItem.act |
| `history-link:Act->Documents` | history | Act → Documents | 42 | — | исключено | решено | история не переносится (Q-27) |

## Связи: Платежи (SPPayments → Payment)

| Связь | Вид | Откуда → куда | Живых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---|---:|---|---|---|---|
| `SPPayments.payer` | field | SPPayments → Accounts\|Contacts\|Vendors | 756 | Payment.payer (Account\|Contact\|Vendor) | перенос | реализовано (этап 04.4) | ok: Payment.payer |
| `SPPayments.related_to` | field | SPPayments → Invoice\|SalesOrder | 623 | PaymentAllocation.invoice \| PaymentAllocation.salesOrder | перенос | реализовано (этап 04.4) | ok: PaymentAllocation.invoice; PaymentAllocation.salesOrder |
| `SPPayments.modifiedby` | owner | SPPayments → User | 799 | modifiedBy | перенос | реализовано (этап 04.4) | ok: Payment.modifiedBy |
| `SPPayments.smcreatorid` | owner | SPPayments → User | 799 | createdBy | перенос | реализовано (этап 04.4) | ok: Payment.createdBy |
| `SPPayments.smownerid` | owner | SPPayments → User | 799 | assignedUser/teams | перенос | реализовано (этап 04.4) | ok: Payment.assignedUser; Payment.teams |
| `crmentityrel:Accounts->SPPayments` | m2m | Accounts → SPPayments | 180 | Payment.payer (дублирует поле payer) | перенос | реализовано (этап 04.4) | ok: Payment.payer |
| `crmentityrel:Contacts->SPPayments` | m2m | Contacts → SPPayments | 5 | Payment.payer | перенос | реализовано (этап 04.4) | ok: Payment.payer |
| `crmentityrel:Vendors->SPPayments` | m2m | Vendors → SPPayments | 23 | Payment.payer (Vendor) | перенос | реализовано (этап 04.4) | ok: Payment.payer |
| `senotesrel:SPPayments->Documents` | m2m | SPPayments → Documents | 1 | Payment.documents (M:N с Document) | перенос | реализовано (этап 04.4) | ok: Payment.documents |
| `allocation:SPPayments->Invoice` | derived | SPPayments → Invoice\|SalesOrder | 679 | PaymentAllocation.payment / PaymentAllocation.invoice / PaymentAllocation.salesOrder (сумма = сумма платежа) | перенос | реализовано (этап 04.4) | ok: PaymentAllocation.payment; PaymentAllocation.invoice; PaymentAllocation.salesOrder |
| `history-link:Accounts->SPPayments` | history | Accounts → SPPayments | 180 | — | исключено | решено | история не переносится (Q-27) |
| `history-link:Contacts->SPPayments` | history | Contacts → SPPayments | 5 | — | исключено | решено | история не переносится (Q-27) |
| `history-link:SPPayments->Documents` | history | SPPayments → Documents | 1 | — | исключено | решено | история не переносится (Q-27) |
| `history-link:Vendors->SPPayments` | history | Vendors → SPPayments | 44 | — | исключено | решено | история не переносится (Q-27) |

## Связи: Накладные (Consignment → VtigerArchive, только чтение)

| Связь | Вид | Откуда → куда | Живых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---|---:|---|---|---|---|
| `Consignment.modifiedby` | owner | Consignment → User | 1 | modifiedBy | архив | реализовано (этап 03) | ok: VtigerArchive.modifiedBy |
| `Consignment.smcreatorid` | owner | Consignment → User | 1 | createdBy | архив | реализовано (этап 03) | ok: VtigerArchive.createdBy |
| `Consignment.smownerid` | owner | Consignment → User | 1 | assignedUser/teams | архив | реализовано (этап 03) | ok: VtigerArchive.assignedUser; VtigerArchive.teams |
| `Consignment.productid` | field | Consignment → Products | 3 | VtigerArchive.data (строки) | архив | реализовано (этап 03) | ok: VtigerArchive.data |
| `Consignment.accountid` | field | Consignment → Accounts | 1 | VtigerArchive.account | архив | реализовано (этап 03) | ok: VtigerArchive.account |
| `Consignment.contactid` | field | Consignment → — | 0 | VtigerArchive.contact | пусто | предложено | пусто — данных нет |
| `Consignment.invoiceid` | field | Consignment → Invoice | 1 | VtigerArchive.invoice (+ vtigerId счёта в VtigerArchive.data) | архив | реализовано (этап 04.3) | ok: VtigerArchive.invoice |
| `Consignment.salesorderid` | field | Consignment → — | 0 | VtigerArchive.data | пусто | предложено | пусто — данных нет |
| `senotesrel:Consignment->Documents` | m2m | Consignment → Documents | 2 | VtigerArchive.documents (M:N с Document) | перенос | реализовано (этап 03) | ok: VtigerArchive.documents |
| `lines:Consignment` | lines | Consignment → lines | 3 | VtigerArchive.data (строки) | архив | реализовано (этап 03) | ok: VtigerArchive.data |
| `history-link:Consignment->Documents` | history | Consignment → Documents | 2 | — | исключено | решено | история не переносится (Q-27) |

## Связи: Строки VTEItems: дубль строк документов, исключены (D-09)

| Связь | Вид | Откуда → куда | Живых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---|---:|---|---|---|---|
| `VTEItems.productid` | field | VTEItems → Services | 286 | — (исключено вместе с VTEItems) | исключено | предложено | исключено вместе с модулем |
| `VTEItems.related_to` | field | VTEItems → Invoice\|Quotes\|SalesOrder | 286 | — (исключено вместе с VTEItems) | исключено | предложено | исключено вместе с модулем |

## Связи: Ссылки других модулей на финансовые документы

| Связь | Вид | Откуда → куда | Живых | Цель | Итог | Статус карты | Причина / проверка |
|---|---|---|---:|---|---|---|---|
| `Assets.invoiceid` | field | Assets → — | 0 | VtigerArchive.data | пусто | предложено | пусто — данных нет |
| `Events.invoiceid` | field | Events → — | 0 | — | пусто | предложено | пусто — данных нет |
| `Events.salesorder_id` | field | Events → — | 0 | — | пусто | предложено | пусто — данных нет |
