# Печатные формы и шаблоны (факты аудита 2026-09-29)

Тексты шаблонов не выгружались: на сервере извлекались только имя, модуль, размер, sha256 (12 знаков), список плейсхолдеров и счётчики «похожих на реквизиты» числовых последовательностей (`scripts/audit/remote/template_tokens.py`). Во всех шаблонах таких последовательностей (20/9/10–12 цифр) — **0**: реквизиты подставляются из настроек организации, а не зашиты в текст.

## 1. SPPDFTemplates (SalesPlatform, таблица `sp_templates`)

Движок SalesPlatform: секции `{header}`, `{table_head}`, `{table_row}`/`{services_row}`/`{goods_row}`, `{summary}`, `{ending}`, `{content}`; переменные `{$name}`. Все шаблоны — `spcompany='All'`.

| id | Название | Модуль | Ориентация | Header/Footer | Размер | sha256 | Судьба |
|---|---|---|---|---|---|---|---|
| 1 | Счет | Invoice | P | 110/50 | 3426 | 2b65fd2b31ad | реализовать (этап 05), если используется — Q-21 |
| 10 | Новый счёт | Invoice | P | 85/50 | 3371 | d29ae01663a1 | **реализовать** (этап 05) — основная форма счёта (кандидат) |
| 8 | Акт | Act | P | 50/50 | 2676 | c064f3fb48b9 | реализовать (этап 05), если используется — Q-21 |
| 9 | Акт с НДС | Act | P | 50/50 | 2689 | eca24c3a3c91 | по решению Q-03/Q-04 (НДС) |
| 11 | Новый акт | Act | P | 50/50 | 2843 | 994b6520061e | **реализовать** (этап 05) — основная форма акта (кандидат) |
| 5 | Приходный кассовый ордер | SPPayments | P | 0/50 | 10913 | cece42ccbfb4 | решить (Q-21): наличных платежей 174, но поля ПКО `debit`, `coracc_subacc`, `target_code` пусты |
| 3 | Предложение | Quotes | P | 100/0 | 1796 | b712974ddc12 | не реализовывать сейчас (предложений с 2018 г. нет) |
| 2 | Накладная | SalesOrder | P | 50/0 | 2387 | 09b5ca510754 | не реализовывать (заказы практически не используются) |
| 4 | Заказ на закупку | PurchaseOrder | P | 50/0 | 1644 | 05b6adbca01c | исключить (модуль пуст) |
| 6 | Счет-фактура | Consignment | L | 85/50 | 7865 | 9f4fa44db6ca | исключить (1 накладная 2019 г., архив) |
| 7 | ТОРГ-12 | Consignment | L | 90/20 | 14589 | af4486eebfce | исключить (архив) |

«Кандидат» — по названию и дате появления; журналов генерации PDF нет, в access-логах Apache за 2 недели (2026-09-15…29) запросов экспорта PDF не найдено (параметры POST не логируются). Какие формы реально печатаются — подтвердить у пользователя (Q-21).

### Плейсхолдеры, которые нужны формам счёта и акта

| Группа | Плейсхолдеры | Источник в EspoCRM (предложено) |
|---|---|---|
| Документ | `invoice_no`, `invoice_invoicedate`, `act_no`, `act_actdate` | `Invoice.number/dateInvoiced`, `Act.number/dateAct` |
| Покупатель | `account_accountname`, `account_inn`, `account_kpp`, `account_phone`, `account_bill_street/city/state/code`, `billingAddress` | `Account.name/cInn/cKpp/phoneNumber/billingAddress*` (формы 10/11 берут адрес **контрагента**, не документа) |
| Продавец | `orgName`, `orgAddress`, `orgBillingAddress`, `orgCity`, `orgState`, `orgCode`, `orgPhone`, `orgInn`, `orgKpp`, `orgBankAccount`, `orgBankName`, `orgBankId`, `orgCorrAccount`, `orgDirector`, `orgBookkeeper` (+ в других формах `orgFax`, `orgWebsite`, `orgLogo`, `orgOKPO`, `orgEntrepreneur`, `orgEntrepreneurreg`) | `LegalEntity.*` (значения — вне Git) |
| Строки | `productNumber`/`serviceNumber` (№ п/п), `productName`, `productComment`, `productQuantity`, `productQuantityInt`, `productUnits`, `productPrice`, `productPriceWithTax`, `productNetTotal`, `productTotal` | `InvoiceItem`/`ActItem` + `Product.name/unit` |
| Итоги | `summaryTotalItems`, `summaryNetTotal`, `summaryTax`, `summaryGrandTotal`, `summaryGrandTotalLiteral`; для актов `summary*Services*` (итоги только по услугам) | расчёт в коде формы; **сумма прописью** на русском — собственная реализация |

Остальные формы дополнительно используют: коды ОКЕИ единиц (`productUnitsCode`, модуль SPUnits пуст), страну и ГТД (`manufCountry`, `manufCountryCode`, `customsId`, `internatonalCode`), разбиение товары/услуги (`summary*Goods*`), поля платежа (`payment_amount_literal`, `payment_pay_date`, `payment_doc_no`, `payment_pay_details`, `payment_payer`, `payment_debit`, `payment_coracc_subacc`, `payment_analytics_code`, `payment_target_code`).

Требования для этапа 05: кириллица, A4 портрет, отступы колонтитулов как в источнике (header/footer — значения выше, единицы SalesPlatform — предположительно мм, **не проверено**), номер/дата/реквизиты/строки/итоги/сумма прописью; сверка визуально и по числам на синтетических примерах; реальные реквизиты в Git не коммитить.

## 2. Прочие шаблоны

| Тип | Кол-во | Факт | Судьба |
|---|---|---|---|
| Email-шаблоны `vtiger_emailtemplates` | 15 (3 системных) | 9 демонстрационных англоязычных шаблонов Vtiger; «Регистрационная информация клиента» (Contacts, ~12 КБ); «Support end notification before a week/month» (~6.9 КБ); системные Activity Reminder, ToDo Reminder, Invite Users | перенести вручную только используемые (Q-14); демо не переносить |
| QuotingTool | 1 | «Invoice Light Blue», `deleted=1` | исключить |
| Условия `vtiger_inventory_tandc` | 6 | один и тот же текст для Invoice, Quotes, PurchaseOrder, SalesOrder, Act, Consignment (одинаковый хеш) | перенести в настройку `termsAndConditions` по умолчанию |
| `vtiger_notificationscheduler` | 8 | стандартные уведомления Vtiger (`LBL_*`), `active=1`, отдельной cron-задачи нет | не переносить |
| `vtiger_inventorynotification` | 3 | стандартные тексты Invoice/Quote/SalesOrder | не переносить |
| Логотипы `test/logo` | 11 файлов | файл логотипа организации указан в `vtiger_organizationdetails.logoname` | перенести логотип в `LegalEntity` (файл — вне Git) |
| Webforms | 0 | — | — |
