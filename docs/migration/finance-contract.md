# Финансовый контракт (аудит 2026-09-29, перепроверка и контракт этапа 04.1 — 2026-09-30)

Документ фиксирует **фактическое** поведение данных Vtiger/SalesPlatform (§1–§10), контракт собственных сущностей EspoCRM (§11), расчётное ядро (§12) и правила, которых в данных нет (§13). Всё, что не подтверждено данными, помечено «не проверено» или вынесено в `open-questions.md`. Денежные агрегаты — **только в приватных отчётах** (`/data/itvolga/espo-private/audit/<срез>/35_control_sums_private.tsv`, `47_finance_snapshot_private.tsv`); в Git — счётчики, правила и HMAC-дайджесты контрольных сумм (`tests/finance/fixtures/source-profile.php`).

Реализация этапа 04.3 (Invoice, InvoiceItem, контроль итогов) — §15, факты перепроверены 2026-10-02 (срез `20261002T162427`); этапа 04.4 (Payment, PaymentAllocation, оплата документов) — §16, срез `20261002T185652`; этапа 04.5 (Act, ActItem, связь счёта и акта) — §17, срез `20261003T094220`; этапа 04.6 (сквозной сценарий, покрытие полей и связей) — §18, срез `20261003T135407`; этапа 05 (печатные формы) — §19.

Перепроверка этапа 04.1: срез `20260930T220947` (`run-audit.sh`, шаги `46_finance_contract.sql`, `47_finance_snapshot_private.sql`); код SalesPlatform — по локальной копии `/data/itvolga/espo-private/vtiger-src/vtiger7/` (7.1.0 SP01). Счётчики с 2026-09-29 выросли на 1 счёт и 1 акт; найдено одно расхождение с прежней версией документа — расходные платежи связаны со счетами (§8). Решения владельца по правилам, которых нет в данных (Q-36…Q-38, 2026-09-30), — D-47, D-49.

## 1. Документы и объёмы (живые записи, 2026-09-30)

| Документ | Таблицы | Записей | Строк | Макс. строк | Период | Цель |
|---|---|---|---|---|---|---|
| Quote | `vtiger_quotes`, `*billads/shipads`, `vtiger_quotescf` | 24 | 27 | 2 | 2016-01 … 2018-10 | `Quote`/`QuoteItem` |
| SalesOrder | `vtiger_salesorder`, `vtiger_invoice_recurring_info` | 14 | 14 | 1 | 2016-01 … 2023-06 | `SalesOrder`/`SalesOrderItem` |
| Invoice | `vtiger_invoice`, `*billads/shipads`, `vtiger_invoicecf` | 636 | 712 | 6 | 2016-01 … 2026-09 | `Invoice`/`InvoiceItem` |
| Act | `vtiger_sp_act`, `*billads/shipads`, `vtiger_sp_actcf` | 404 | 417 | 2 | 2018-07 … 2026-09 | `Act`/`ActItem` |
| Consignment | `vtiger_sp_consignment` | 1 | 3 | 3 | 2019-12 | `VtigerArchive` |
| Payment | `sp_payments`, `sp_paymentscf` | 798 | — | — | 2015-10 … 2026-09 | `Payment`/`PaymentAllocation` |
| PurchaseOrder | `vtiger_purchaseorder` | 0 | — | — | — | не создаётся |

Строки всех документов — одна таблица `vtiger_inventoryproductrel` (`id` = crmid документа, `sequence_no`, `lineitem_id` — уникален у всех 1176 строк). У каждого документа строки пронумерованы `1…n` без пропусков. Товар строки: Services 1167, Products 6 (счёт 3, накладная 3), удалённых и пустых ссылок нет. Удалённые документы: Invoice 2 (2 строки), Act 1 (1 строка) — не переносятся. `vtiger_vteitems` — устаревшая копия строк (исключается, D-09).

## 2. Поля заголовка (общие для Quote/SalesOrder/Invoice/Act)

| Поле Vtiger (колонка) | Смысл | Факт (2026-09-30) | Цель |
|---|---|---|---|
| `*_no` | номер | см. §6 | `number` (строка как есть) |
| `subject` | название | заполнено везде | `name` |
| `invoicedate` / `actdate` / `validtill` / `duedate` | даты | Invoice: дата 635/636, срок 536; Act: дата 403/404; Quote: срок 15/24; SO: срок 7/14 | `dateInvoiced`, `dateAct`, `dateValidUntil`, `dateDue` |
| `*status` | статус | §5 | `status` (enum, значения источника) |
| `accountid` | покупатель | у всех живых документов | `account` |
| `contactid` | контакт | Invoice 23, Act 6, Quote 6, SO 8 | `contact` |
| `potential_id`/`potentialid` | сделка | Invoice 429, Quote 24, SO 12 | `opportunity` |
| `salesorderid` | заказ | Invoice 27, Act 0 | `salesOrder` |
| `sp_act_id` (Invoice) | акт | 392 | `act` |
| `currency_id`, `conversion_rate` | валюта | всегда `1` (RUB), курс 1.000 | валюта полей = RUB |
| `taxtype` (`hdnTaxType`) | режим налога | individual / group / group_tax_inc | `taxMode` |
| `region_id` | налоговый регион | `NULL` — документы до обновления 2018-07 (Invoice 151, Quote 23, SO 13; последний — 2018-05-28), `0` — после (Invoice 485, все акты) | класс формулы `sourceFormula` + `vtigerData.region_id` |
| `subtotal` (`hdnSubTotal`) | сумма строк | §4 | `subtotal` (эталон) |
| `discount_percent`/`discount_amount` | скидка на документ | 1 счёт — суммой; процентом — нигде | `discountAmount`/`discountPercent` |
| `s_h_amount`, `s_h_percent` | доставка и её налог | всегда 0 | `shippingAmount`, `shippingTaxPercent` |
| `pre_tax_total` | сумма до налога | §4 | `preTaxTotal` (эталон) |
| `adjustment` (`txtAdjustment`) | корректировка | всегда 0 во всех 4 модулях | `adjustment` |
| `total` (`hdnGrandTotal`) | итог | §4; у всех > 0; ≤ 2 знаков после запятой | `grandTotal` (эталон) |
| `received`, `balance` (Invoice) | оплачено/остаток | `received` всегда 0; `balance = total` у 616 из 636 | `vtigerData.received`, `balanceSource` (контроль, не бизнес-логика) |
| `spcompany` | юрлицо-продавец | §3 | `legalEntity` |
| `compound_taxes_info` | составные налоги | служебный JSON | `vtigerData` |
| `terms_conditions` | условия | один общий текст (`vtiger_inventory_tandc`); у Act колонки нет | `termsAndConditions` |
| `bill_*`, `ship_*` | адреса | копия адреса контрагента на момент документа | `billingAddress*`, `shippingAddress*` |
| `vtiger_inventorychargesrel.charges` | доп. расходы (JSON) | у всех документов значение 0 | не переносится |

## 3. Юридическое лицо (`spcompany`)

- `vtiger_organizationdetails` содержит **одну** строку, `company='Default'`; заполнены наименование, адрес, телефоны, сайт, ИНН, КПП, р/с, банк, БИК, к/с, директор, бухгалтер, ИП-поля, ОКПО, имя файла логотипа; `vatid` и колонка `logo` пусты (значения не выгружались и в Git не хранятся).
- Справочник `vtiger_spcompany` — два значения: `Default` (id 1, создан миграцией SalesPlatform 6.2→6.3 вместе с `organizationdetails.company='Default'`) и `По умолчанию` (id 2).
- **Семантика (проверено 2026-09-30):** `По умолчанию` — это русская подпись английского ключа `Default` (`languages/ru_ru/Vtiger.php`: `'Default' => 'По умолчанию'`, так же в `Settings/Vtiger.php`), сохранённая как второе значение списка. Своей строки реквизитов (`organizationdetails.company='По умолчанию'`) и своего счётчика нумерации (`vtiger_modentity_num.spcompany`: у всех финансовых модулей только пустое значение = `Default`) у него нет. Следствия в коде SalesPlatform: печать ищет реквизиты `WHERE company=<spcompany>` (`includes/SalesPlatform/PDF/SPPDFController.php`; пустое значение → `Default`), нумерация ищет счётчик по `spcompany` (`data/CRMEntity.php`, `Default` → пусто) — поэтому единственный живой акт без номера — акт с `По умолчанию`.
- Использование (все живые записи):

| Модуль | `Default` | `По умолчанию` | пусто |
|---|---|---|---|
| Invoice | 548 (2016-01 … 2026-09) | 88 (созданы 2016-02 … 2018-07; 86 из них — с `region_id NULL`) | 0 |
| Act | 402 | 2 (2018-07 … 2019-10) | 0 |
| Quote / SalesOrder | 22 / 13 | 2 / 1 (2016) | 0 |
| Payment | 473 | 137 (2015-10 … 2018-07) | 188 (187 — банковский импорт 2018–2020, 1 — 2023) |

  История поля: 3 счёта и 1 акт вручную переведены `По умолчанию → Default` (2018); обратных переводов нет. Оба значения выбирались пользователями как одно и то же юрлицо.
- **Вывод (принято, D-04; уточнено D-48):** `Default`, `По умолчанию` и пустое значение — одно юрлицо; второго юрлица в данных нет. В EspoCRM — одна запись `LegalEntity`; импорт сопоставляет значения только точным совпадением (`LegalEntityResolver`, при каждом сохранении с `SaveOption::IMPORT`, исходное значение — в `vtigerData.spcompany`, D-60), любое другое значение останавливает импорт и не превращается во второе юрлицо. Печатные шаблоны имеют `spcompany='All'` (11 шаблонов).
- **Ограничение вывода:** Vtiger хранит только текущие реквизиты (одна строка без истории); реквизиты, напечатанные в исторических документах, по БД подтвердить нельзя (владелец: не менялись, Q-31).

## 4. Расчёт сумм (проверено пересчётом по строкам, 2026-09-30)

Обозначения: `gross = quantity × listprice`, `net = gross − discount_amount − gross × discount_percent / 100`, `tax% = tax1 + tax2 + tax3`, `hdisc` — скидка документа.

| Проверка | Invoice | Act | Quote | SalesOrder |
|---|---|---|---|---|
| `pre_tax_total = Σ net − hdisc + s_h_amount` | 636/636 | 404/404 | 24/24 | 14/14 |
| `subtotal = Σ net` | 636/636 | 404/404 | 24/24 | 14/14 |
| `total = subtotal − hdisc + s_h + adjustment` | 634/636 (2 group-счёта: `+ налог 18%`) | 404/404 | 24/24 | 14/14 |
| итоги кратны 0.01 | 636 | 404 | 24 | 14 |

Классы документов (класс формулы ядра, §12; счётчики совпадают с независимым SQL `34_finance_config.sql: formula_class`):

| Класс | Invoice | Act | Quote | SO | Период |
|---|---|---|---|---|---|
| `noLineTax` — налога в строках нет | individual 454, group_tax_inc 31 | individual 383, group_tax_inc 21 | 1 | group_tax_inc 1 | 2016–2026 (region_id=0) |
| `lineTaxNotApplied` — `tax1=18%` в строках, в итоги не входит | individual 148 | — | 23 | 13 | 2016–2018 (region_id NULL) |
| `taxIncludedInPrice` — group_tax_inc, 18% внутри цены | 1 | — | — | — | 2017 (region_id NULL) |
| `groupTaxAdded` — group, одна ставка во всех строках, `total = pre_tax + 18%` | 2 | — | — | — | 2016–2017 (region_id NULL) |

Правила контракта:
1. **Исходные `subtotal`, `pre_tax_total`, `total`, строки — эталон** (D-05). Импорт сохраняет их как есть; ядро пересчитывает только для контроля и показывает расхождение отдельно (`totalsCheck`), без исправления.
2. Для `region_id IS NULL` значение `tax1` на строках — историческое и не влияет на итоги (кроме 2 group-счетов). После обновления 2018-07 ни у одного живого документа налога в строках нет.
3. `group_tax_inc` — цена включает налог; сумма налога нигде не хранится. Компания работает **без НДС (УСН)** — выделение НДС не требуется, форма «Акт с НДС» не реализуется (Q-04, D-21).
4. Групповой налог (Vtiger 7, `Inventory/resources/Edit.js: calculateGroupTax`): ставка хранится в каждой строке, база = `subtotal − hdisc`, база и налог округляются до копеек; в данных подтверждено только при `hdisc = 0` (2 счёта, ставка одинакова во всех строках, `total − pre_tax_total = ROUND(base × 18/100, 2)` у обоих).
5. Настройка налога `vtiger_inventorytaxinfo`: одна ставка `tax1` «НДС» 18%, Simple/Fixed; налог доставки 18%; доп. расход «Shipping & Handling» 0. Новые документы — без налога, ставки 20%/22% не заводятся; исторические `tax1=18%` переносятся как исходные значения строк (Q-04, D-21).
6. Количество: `DECIMAL(25,3)`, дробное у 111 строк счетов и 97 строк актов (часы), фактически ≤ 2 знаков; > 0 у всех строк. Цена: `DECIMAL(27,8)`, фактически ≤ 2 знаков, > 0 у всех строк (нулевых нет).
7. Скидки: на строке — суммой в 2 строках счетов и 1 строке акта, процентом — нигде; скидка документа — суммой в 1 счёте, процентом — нигде. Отрицательных и нулевых сумм строк нет.
8. Округление: все хранимые итоги кратны 0.01, ни одна строка живых документов не даёт долей копейки (`36_rounding.sql`) — исходные суммы от правила не зависят. Для новых документов: сумма строки округляется до копеек (0,5 — от нуля), итог = сумма округлённых строк (Q-03, D-29). Vtiger округлял в браузере через `Number.toFixed` (двоичная плавающая точка) — на исторических данных различие не проявляется, воспроизводить его не нужно.
9. Маржа строки (Vtiger 7 `calculateTotalAfterDiscount`): `margin = net − purchase_cost`, где `purchase_cost` — себестоимость всей строки; `purchase_cost` во всех строках 0. Проверено: равенство у 486 строк счетов, 417 актов, 1 предложения, 1 заказа; у остальных (226 строк счетов, из них 211 в документах до 2018-07; 26 предложения; 13 заказа) маржа 0 — не вычислялась. Других значений нет.

## 5. Статусы (живые записи, 2026-09-30)

- Invoice: Paid 561, Created 34, Cancel 17, Sent 9, Credit Invoice 6, Approved 5, пусто 4. Статус **выставляется вручную**: банковский импорт пытался ставить Paid, но сохранение закомментировано в коде. Итоги `Credit Invoice` положительны, как у остальных.
- Act: Created 291, Sent 55, Received 39, Done 5, пусто 14; история статусов `vtiger_sp_actstatushistory` 51.
- Quote: Принято 11, Доставка 8, Создано 3, Delivered 1, Просмотрено 1. SalesOrder: Одобрено 9, Создано 4, Created 1; `invoicestatus` (периодичность) Cancel 10, AutoCreated 3.
- Payment (`spstatus`, список: Executed, Запланирован, Canceled, Delayed): Executed 776, Запланирован 3, Canceled 1, пусто 18 (приходы 2015–2021; при расчёте оплаты считаются как Executed — Q-37, D-49).
- История статусов счетов — 588 записей (`vtiger_invoicestatushistory`, 2018-07…2026-09) — не переносится (Q-27, D-08).

## 6. Нумерация

| Документ | Форматы (цифры → 9) | Уникальность | Счётчик `vtiger_modentity_num` (`cur_id` — следующий номер) |
|---|---|---|---|
| Invoice | `С-999` 471 (`С-166`…`С-636`); `СЧЕТ_9…999` 165 (живые) | уникальны; 2 пустых номера — только у удалённых счетов | активный `С-`, 637 (прежний `СЧЕТ_` — 166, неактивен) |
| Act | `9` 8, `99` 92, `999` 303 (только цифры); пусто 1 (акт с `По умолчанию`, §3) | **2 номера повторяются у 4 живых актов** (двузначные) | без префикса, 403 |
| Quote | `ПРЕД_9` 9, `ПРЕД_99` 15 | уникальны | `ПРЕД_`, 25 |
| SalesOrder | `ЗАКАЗ_9` 9, `ЗАКАЗ_99` 5 | уникальны | `ЗАКАЗ_`, 15 |
| Payment | `9` 8, `99` 90, `999` 700 | уникальны (798 живых) | без префикса, 991 |
| Consignment | `9` | — | 2 |

Номера переносятся строкой без изменений (D-17); уникальность проверяется только у документов, созданных в EspoCRM; первый номер новых документов — значение `cur_id` (на дату среза: `С-637`, акт 403, `ПРЕД_25`, `ЗАКАЗ_15`, платёж 991; при переключении — перечитать). Счётчик один: юрлицо одно (§3).

## 7. Связь счёт → акт

- `Invoice.sp_act_id` → Act: 392 живых счёта ссылаются на 392 **разных** живых акта; ни один акт не связан с двумя счетами; **12** живых актов без живого счёта (один связан только с удалённым счётом); 244 живых счёта без акта.
- Совпадение: контрагент 392/392, юрлицо 391/392, режим налога 389/392, итог 387/392 (у 5 пар итог акта больше итога счёта; переносятся как есть + отчёт — Q-18, D-26).
- Модель: `Invoice.act` (belongsTo) + `Act.invoices` (hasMany) — **без** ограничения 1:1; импорт проверяет фактическую кардинальность.
- Как связь возникала (код SalesPlatform, перепроверено 2026-10-03): «Создать Акт» на счёте открывает форму акта, заполненную из счёта (все одноимённые поля и строки; дата и статус — нет), и при сохранении акта пишет `sp_act_id` счёта; поле «Акт» в форме счёта редактируемое, но вручную его не меняли ни разу (история — 0 изменений). 12 актов без счёта созданы из карточки контрагента («Добавить акт»). Реализация — §17.

## 8. Платежи и распределение

Поля: `pay_no` (номер), `pay_date`, `pay_type` (Приход 735 / Expense 63), `type_payment` (Cashless Transfer 622 / Наличные 174 / пусто 2), `amount` (всегда ≥ 0, ≤ 2 знаков, один нулевой платёж — приход без статуса 2015 г.; знак задаёт `pay_type`), `spstatus`, `payer` (Accounts 725, Vendors 25, Contacts 5, пусто 43), `related_to` (Invoice 615, SalesOrder 7, пусто 176; у расходов — всегда пусто), `doc_no` (656), `pay_details` (662), банковские реквизиты контрагента `cf_1198…cf_1204`, `cf_1380` валютный счёт (1).

Источники распределения платежа на документ:
1. `sp_payments.related_to` — одно поле, **один документ на платёж** (Invoice или SalesOrder).
2. `vtiger_crmentityrel` (Invoice ↔ SPPayments) — 519 пар живых записей; ни один живой платёж не связан так с двумя счетами.

Строгое разбиение 798 живых платежей (`scripts/audit/sql/33_allocation_check.sql`, категория `alloc_partition`; ядро даёт те же счётчики):

| Категория | Платежей | Решение ядра (§12.4) |
|---|---|---|
| `related_to` → счёт, связь указывает тот же счёт | 425 | распределить |
| `related_to` → счёт, связи нет | 152 | распределить |
| `related_to` → заказ (SalesOrder) | 7 | распределить |
| `related_to` пуст, есть связь со счётом | 56: приходы 4, **расходы 52** | приходы — распределить; расходы — не распределять (Q-36) |
| **конфликт:** `related_to` → счёт, связь указывает другой счёт | 38 | распределить по `related_to`, отчёт (D-11) |
| не распределён (нет ни поля, ни связи) | 120 | нет |
| **итого** | 798 (буквально по D-11 — 678; распределяется 626: без 52 расходов, Q-36) | |

**Расходные платежи (исправлено 2026-09-30):** прежняя версия утверждала, что ни один расход не привязан к документу; это верно только для `related_to`. 52 из 63 расходов — платежи банковского импорта «Точка» 2018–2020 — связаны со счетами **клиентов** через связанный список: у всех 52 плательщик (поставщик или пусто) не совпадает с контрагентом счёта, а сумма — с итогом счёта; 51 счёт в статусе Paid, 1 — Sent. Это артефакт импорта, выбиравшего «первый счёт плательщика в статусе Sent». Буквальное D-11 распределило бы их на счета; **решение владельца (Q-36): не распределять**, исходная связь — в `vtigerData` и приватном отчёте.

Происхождение: банковский импорт (2018–2020, 188 платежей с `cf_1204`, пустое `spcompany`) выбирал счёт как **первый счёт этого плательщика в статусе Sent** — без сверки суммы и номера — и дублировал ссылку в `crmentityrel`. Ручные платежи (2021+) ставят `related_to`.

Сумма распределения в источнике не хранится — платёж относится к документу целиком.

Покрытие документов оплатами. «Оплачено» = распределения приходов в статусе Executed или без статуса (Q-37, D-49; запланированные, отменённые, отложенные и расходы не считаются). Слева — только по `related_to` и только Executed (`27_payments.sql`, взгляд аудита 2026-09-29), справа — по правилам контракта (`46_finance_contract.sql: coverage_d11`, ядро даёт те же счётчики):

| Статус счёта | всего | без оплат | 1 платёж | >1 | сумма = итог | частично | переплата |
|---|---|---|---|---|---|---|---|
| Paid | 561 | 40 / **36** | 466 / 468 | 55 / 57 | 473 / 473 | 16 / 17 | 32 / **35** |
| Created | 34 | 25 / 25 | 8 / 8 | 1 / 1 | 6 / 6 | 3 / 3 | 0 |
| Sent | 9 | 6 / 6 | 2 / 2 | 1 / 1 | 1 / 1 | 2 / 2 | 0 |
| Approved | 5 | 4 / 4 | 1 / 1 | 0 | 1 / 1 | 0 | 0 |
| пусто | 4 | 4 / 3 | 0 / 1 | 0 | 0 / 1 | 0 | 0 |
| Cancel / Credit Invoice | 17 / 6 | все | — | — | — | — | — |

Заказы (D-11): Одобрено 9 — без оплат 7, частично 2; Создано 4 — без оплат 3, оплачен 1; Created 1 — без оплат.

Правила контракта (для этапа 04.4):
1. `PaymentAllocation(payment, invoice|salesOrder, amount)`; при импорте `amount` = сумма платежа (источник не делит платежи).
2. Основной источник — `related_to`; связь `crmentityrel` используется, только если `related_to` пуст (приходы: 4). 38 конфликтов не угадываются: импортируются по `related_to` и попадают в приватный отчёт (Q-02, D-11). Расходы, связанные со счетом только связью (52), не распределяются (Q-36): связь — в `vtigerData` и отчёт.
3. Статус счёта **не** вычисляется из оплат при импорте; «Paid без оплат» (40 по `related_to`, 36 по правилам контракта) и переплаты (32 и 35) переносятся как есть и попадают в отчёт (Q-25, D-26).
4. `balance` Vtiger не поддерживается — не использовать как бизнес-значение.
5. Расходные платежи (Expense, 63) — `Payment(direction=outgoing)` без распределения; `related_to` у них пуст; плательщик-поставщик — собственная сущность `Vendor` (Q-07, D-13).
6. Платежи к SalesOrder (7, 2016–2017) — распределение на `salesOrder`.
7. Для новых платежей: сумма распределений платежа не больше суммы платежа, каждое распределение > 0 и в копейках (`AllocationCalculator::remainder`); остаток платежа = сумма − Σ распределений.

## 9. Счёт → оплата → акт: сквозная картина

Фактические цепочки: Quote → SalesOrder не используются (`SalesOrder.quoteid` пуст); SalesOrder → Invoice — 27 счетов (2016: 26, 2023: 1); Invoice → Act — 392; распределяется 626 платежей (на счета 619, на заказы 7); 52 расхода со связью со счётом не распределяются (Q-36). Для этапа 04.6 допустимы варианты без Quote/SalesOrder (большинство счетов). Формы цепочек по счетам, совпадение полей связанных пар и владельцы (перепроверено 2026-10-03) — §18.1.

## 10. Не проверено / открыто

- Q-36 (расходы со связью со счётом), Q-37 (приходы без статуса), Q-38 (элементы расчёта новых документов) закрыты владельцем 2026-09-30 (D-47, D-49).
- Не проверено: как SalesPlatform до обновления 2018-07 (Vtiger 6) считал налог строк — кода той версии нет; вывод §4 сделан по данным.
- Закрыто ранее: Q-03 (округление строк до копеек, D-29), Q-01 (номера как есть), Q-02 (распределение по `related_to`), Q-04 (без НДС), Q-18/Q-23/Q-25 (спорные записи как есть + отчёт), Q-31 (реквизиты не менялись).

## 11. Контракт сущностей EspoCRM (этап 04.1)

Сущности создаются на этапах 04.2–04.5 по этому контракту; в `field-map.csv`/`relations.csv` строки созданных сущностей имеют статус `реализовано (этап …)`; статуса `контракт (этап 04.1)` после этапа 04.6 нет — строки, которые ничего не переносят, `решено` (§18.4). Quote, SalesOrder, их позиции и LegalEntity реализованы на этапе 04.2 (§14), Invoice и InvoiceItem — на этапе 04.3 (§15), Payment, PaymentAllocation и оплата счетов и заказов — на этапе 04.4 (§16), Act, ActItem и `Invoice.act` — на этапе 04.5 (§17). Общие правила: деньги — поля `currency` с `decimal: true` (DECIMAL, без float, D-43), валюта только RUB; служебные поля импорта — D-41; даты «только дата» не пересчитываются (D-30); справочники — по словарю `vtigerValueMap` (D-38, генерируется на этапе сущности). Первая колонка таблиц — имена полей (их проверяет `tests/finance/ContractMapTest.php`).

### Document

Общие поля Quote, SalesOrder, Invoice и Act.

| Поле | Тип EspoCRM | Источник | Правило |
|---|---|---|---|
| `vtigerId` | int, уникальный, только чтение | `vtiger_crmentity.crmid` | ключ идемпотентности (D-41); пусто у документов EspoCRM |
| `number` | varchar(100) | `invoice_no` / `act_no` / `quote_no` / `salesorder_no` | строка как есть (D-17), у импортированных не меняется; новые — префикс + счётчик (§6); уникальность — только у созданных в EspoCRM |
| `name` | varchar(255), обязательное | `subject` | как есть |
| `status` | enum | `invoicestatus` / `sp_actstatus` / `quotestage` / `sostatus` | значения §5 по словарю D-38; пусто остаётся пустым |
| `account` | link Account, обязательное | `accountid` | заполнено у всех живых документов |
| `contact` | link Contact | `contactid` | |
| `opportunity` | link Opportunity | `potential_id` / `potentialid` | у Act колонки нет |
| `legalEntity` | link LegalEntity, обязательное | `spcompany` | `LegalEntityResolver` (§3, D-48) при сохранении импорта; исходное значение → `vtigerData.spcompany` (D-60) |
| `assignedUser`, `teams` | link User, linkMultiple Team | `vtiger_crmentity.smownerid` | пользователь → User, группа → Team |
| `createdAt`, `modifiedAt`, `createdBy`, `modifiedBy` | datetime, link User | `vtiger_crmentity` | D-30 |
| `currency` | валюта денежных полей (`…Currency`) | `currency_id`, `conversion_rate` | всегда RUB; курс 1.000 не переносится |
| `taxMode` | enum `individual` / `group` / `group_tax_inc` | `taxtype` | исходное значение; у новых — любое, налог 0 (D-21) |
| `sourceFormula` | enum (классы §12.3), только чтение | `region_id`, `taxtype`, `tax1…tax3` строк | вычисляет `SourceVerifier` при импорте; пусто у документов EspoCRM |
| `subtotal` | currency, decimal(25,8) | `subtotal` | эталон (D-05); новые — Σ `amount` строк |
| `discountAmount` | currency, decimal(25,8) | `discount_amount` | скидка документа суммой, ≥ 0 |
| `discountPercent` | decimal(25,3), 0…100 | `discount_percent` | в источнике 0; у новых — скидка процентом от `subtotal` вместо суммы (D-47) |
| `shippingAmount`, `shippingTaxPercent` | currency ≥ 0; decimal(25,3) | `s_h_amount`, `s_h_percent` | в источнике 0; у новых — доставка без налога, `shippingTaxPercent` только 0 (D-21, D-47) |
| `adjustment` | currency, decimal(25,8), со знаком | `adjustment` | в источнике 0; у новых — корректировка итога ± (D-47) |
| `preTaxTotal` | currency, decimal(25,8) | `pre_tax_total` | эталон; новые — `subtotal − скидка + shippingAmount` |
| `grandTotal` | currency, decimal(25,8) | `total` | эталон; новые — `preTaxTotal + adjustment` (≥ 0) |
| `totalsCheck` | enum `exact` / `rounded` / `mismatch` / `unverified`, только чтение | `SourceVerifier` | результат сверки хранимых итогов с пересчётом; исходные суммы не меняются (D-46) |
| `expectedSubtotal`, `expectedPreTaxTotal`, `expectedGrandTotal` | currency, decimal(25,8), только чтение | `SourceVerifier` | «Пересчёт ядра»: точный пересчёт итогов импортированного документа, показывается при `rounded`/`mismatch`; очищается при пересчёте в EspoCRM (D-59) |
| `sourceSubtotal`, `sourcePreTaxTotal`, `sourceGrandTotal` | currency, decimal(25,8), только чтение | исходные `subtotal`, `pre_tax_total`, `total` | «Итоги Vtiger»: записываются один раз при первом пересчёте импортированного документа (D-51, D-59) |
| `billingAddressStreet`, `billingAddressCity`, `billingAddressState`, `billingAddressPostalCode`, `billingAddressCountry` | address | `bill_street`, `bill_city`, `bill_state`, `bill_code`, `bill_country` | копия адреса на дату документа |
| `shippingAddressStreet`, `shippingAddressCity`, `shippingAddressState`, `shippingAddressPostalCode`, `shippingAddressCountry` | address | `ship_street`, `ship_city`, `ship_state`, `ship_code`, `ship_country` | то же |
| `termsAndConditions` | text | `terms_conditions` | у Act колонки нет |
| `description` | text | `vtiger_crmentity.description` | |
| `documents` | linkMultiple Document | `vtiger_senotesrel` | Invoice 72, Act 42 |
| `vtigerData` | jsonObject, только чтение, только администраторам | колонки без рабочего поля | `region_id`, `compound_taxes_info`, `tax`, `bill_pobox`, `ship_pobox` и поля модулей ниже (D-41) |
| `items` | hasMany Item | `vtiger_inventoryproductrel` | порядок `order` |

### Quote

| Поле | Тип EspoCRM | Источник | Правило |
|---|---|---|---|
| `dateValidUntil` | date | `validtill` | 15 из 24 |
| `inventoryManager` | link User | `inventorymanager` | 23 из 24; собственная сущность — без префикса `c` (D-12) |
| `salesOrders` | hasMany SalesOrder | `vtiger_salesorder.quoteid` | в источнике пусто |
| `invoices` | hasMany Invoice (обратная `Invoice.quote`) | — | связь EspoCRM, в источнике нет (D-58) |

В `vtigerData`: `carrier`, `shipping` (пусты).

### SalesOrder

| Поле | Тип EspoCRM | Источник | Правило |
|---|---|---|---|
| `dateDue` | date | `duedate` | 7 из 14 |
| `quote` | link Quote | `quoteid` | в источнике пусто у всех 14 |
| `invoices` | hasMany Invoice | `vtiger_invoice.salesorderid` | 27 счетов |
| `paymentAllocations` | hasMany PaymentAllocation | `sp_payments.related_to` | 7 платежей |
| `paidAmount`, `balanceAmount`, `settlementState` | currency, currency, enum `unpaid` / `partial` / `paid` / `overpaid`; хранимые, только чтение, audited | `AllocationCalculator::settle` | как у Invoice (D-64) |

В `vtigerData`: `carrier`, `pending`, `fromsite`, `vendor_id`, `exciseduty`, `salescommission`, периодичность (`enable_recurring`, `recurring_frequency`, `start_period`, `end_period`, `payment_duration`, `recurring_invoice_status`; закончилась в 2016, D-15).

### Invoice

| Поле | Тип EspoCRM | Источник | Правило |
|---|---|---|---|
| `dateInvoiced` | date, обязательное для формы и API | `invoicedate` | 635 из 636; у новых — сегодня по умолчанию (D-57) |
| `dateDue` | date, обязательное для формы и API | `duedate` | 536 из 636 (D-57) |
| `salesOrder` | link SalesOrder | `salesorderid` | 27 |
| `quote` | link Quote | — | в источнике нет: «Создать счёт» из предложения или заказа (D-58) |
| `act` | link Act (belongsTo), audited | `sp_act_id` | 392; фактически ≤ 1:1, ограничение 1:1 не вводится (§7); несколько счетов на один акт — полем «Акт» (§17) |
| `balanceSource` | currency, только чтение | `balance` | контроль, не бизнес-значение (§8.4) |
| `paymentAllocations` | hasMany PaymentAllocation | `sp_payments.related_to`, `vtiger_crmentityrel` | §8, D-11 |
| `paidAmount`, `balanceAmount`, `settlementState` | currency, currency, enum `unpaid` / `partial` / `paid` / `overpaid`; хранимые, только чтение, audited | `AllocationCalculator::settle` | контроль оплаты, пересчитывается при каждом изменении платежей и итога (D-64); статус счёта из них не выводится (D-26) |

В `vtigerData`: `customerno`, `received`, `exciseduty`, `salescommission`, `purchaseorder`.

### Act

| Поле | Тип EspoCRM | Источник | Правило |
|---|---|---|---|
| `dateAct` | date, обязательное для формы и API | `actdate` | 403 из 404; у новых — сегодня по умолчанию (D-69) |
| `invoices` | hasMany Invoice (обратная `Invoice.act`) | `vtiger_invoice.sp_act_id` | 12 актов без живого счёта; панель — только просмотр (D-70) |

`salesorderid` у актов пуст — поле не создаётся. Связи акта с платежами нет: ни один платёж источника не указывает на акт (D-69).

### Item

Строки документов: `QuoteItem`, `SalesOrderItem`, `InvoiceItem`, `ActItem` — одна структура.

| Поле | Тип EspoCRM | Источник | Правило |
|---|---|---|---|
| `vtigerId` | int, уникальный, только чтение | `lineitem_id` | D-41 |
| `quote`, `salesOrder`, `invoice`, `act` | link на свой документ, обязательное | `id` | у каждой сущности строк — одна своя ссылка |
| `order` | int | `sequence_no` | 1…n без пропусков у всех документов |
| `product` | link Product, обязательное | `productid` | Services/Products → Product (D-14) |
| `description` | text | `comment` | |
| `quantity` | decimal(25,3), > 0 | `quantity` | фактически ≤ 2 знаков |
| `unitPrice` | currency, decimal(27,8), ≥ 0 | `listprice` | |
| `discountAmount` | currency, decimal(27,8), ≥ 0 | `discount_amount` | скидка строки суммой |
| `discountPercent` | decimal(7,3), 0…100 | `discount_percent` | в источнике 0; у новых — процент от `quantity × unitPrice` вместо суммы (D-47) |
| `taxRate` | decimal(7,3) | `tax1` | 18 — только исторически (§4.2); у новых только 0 (D-21) |
| `amount` | currency, decimal(25,8), только чтение | вычисляется | `net` (§4); у импортированных — точно (долей копейки нет), у новых — округлено до копеек (D-29) |
| `purchaseCost` | currency, decimal(27,8), ≥ 0 | `purchase_cost` | себестоимость всей строки; в источнике 0 |
| `margin` | currency, decimal(27,8) | `margin` | исходное — как есть (проверка §4.9); у новых — `amount − purchaseCost` |
| `vtigerData` | jsonObject, только чтение | `tax2`, `tax3`, `description` | пусты |

### Payment

| Поле | Тип EspoCRM | Источник | Правило |
|---|---|---|---|
| `vtigerId` | int, уникальный, только чтение | `payid` | D-41 |
| `number` | varchar(100) | `pay_no` | как есть; уникальны; новые — счётчик без префикса (§6, с 991) |
| `name` | varchar(100), только чтение | — | равно `number` (название записи в ссылках) |
| `datePaid` | date, обязательное | `pay_date` | `D~M` в Vtiger; у новых — сегодня |
| `direction` | enum `incoming` / `outgoing`, обязательное | `pay_type` | Приход → incoming, Expense → outgoing; у новых — incoming (умолчание Vtiger) |
| `method` | enum `cash` / `bank` | `type_payment` | Наличные → cash, Cashless Transfer → bank; 2 пусто; у новых — bank (умолчание Vtiger) |
| `amount` | currency, decimal(25,8), ≥ 0, обязательное | `amount` | знак задаёт `direction`; новые — в копейках |
| `status` | enum | `spstatus` | Executed / Запланирован / Canceled / Delayed + пусто (остаётся пустым; в оплату входит как Executed — Q-37), словарь D-38; у новых — Executed (умолчание Vtiger) |
| `payer` | linkParent Account / Contact / Vendor | `payer` | 43 пусто |
| `legalEntity` | link LegalEntity | `spcompany` | пусто (188) — то же юрлицо (§3) |
| `documentNumber` | varchar(100) | `doc_no` | int → строка |
| `purpose` | varchar(255) | `pay_details` | |
| `counterpartyAccount`, `counterpartyBic`, `counterpartyBankName` | varchar | `cf_1198`, `cf_1200`, `cf_1202` | реквизиты контрагента — ПДн, в Git не попадают |
| `bankTransactionId` | varchar(100) | `cf_1204` | ключ дедупликации банковского импорта |
| `isForeignCurrencyAccount` | bool | `cf_1380` | |
| `assignedUser`, `teams`, `createdAt`, `modifiedAt`, `createdBy`, `modifiedBy` | как у документа | `vtiger_crmentity` | |
| `description` | text | `vtiger_crmentity.description` | |
| `documents` | linkMultiple Document | `vtiger_senotesrel` | 1 |
| `paymentAllocations` | hasMany PaymentAllocation | | |
| `allocationList` | jsonArray, нехранимое, audited | строки `PaymentAllocation` | таблица распределений в форме платежа (D-63) |
| `allocatedAmount`, `unallocatedAmount` | currency, нехранимые, только чтение | Σ строк; сумма − Σ | распределено и остаток платежа, считаются при чтении |
| `vtigerData` | jsonObject, только чтение | `analytics_code`, `debit`, `coracc_subacc`, `target_code`; исходные `related_to` и связи | |

### PaymentAllocation

| Поле | Тип EspoCRM | Источник | Правило |
|---|---|---|---|
| `payment` | link Payment, обязательное | `sp_payments.payid` | |
| `invoice` | link Invoice | `related_to` или связь `vtiger_crmentityrel` | ровно одно из `invoice` / `salesOrder` |
| `salesOrder` | link SalesOrder | `related_to` | 7 |
| `amount` | currency, decimal(25,8), > 0 | импорт — `amount` платежа | в копейках; Σ по платежу ≤ суммы платежа (§8.7) |
| `source` | enum `relatedTo` / `relationLink` / `manual`, только чтение | категория `SourceAllocationResolver` | происхождение распределения |
| `sourceConflict` | bool, только чтение | категория `conflict_rel_other_invoice` | 38; счёт из связи — в `vtigerData` и приватном отчёте |
| `vtigerData` | jsonObject, только чтение | категория и связи источника | |
| `order`, `name` | int, varchar, только чтение | — | порядок строки в таблице платежа; «номер платежа → номер документа» |
| `paymentDatePaid`, `paymentStatus` | foreign (дата и статус платежа), только чтение | — | колонки панели «Оплаты» счёта и заказа |

### LegalEntity

Одна запись (D-04). Значения реквизитов — только из источника при импорте, в Git не попадают.

| Поле | Тип EspoCRM | Источник | Правило |
|---|---|---|---|
| `vtigerCompanyKey` | varchar(255), уникальный, только чтение | `company` | `Default` |
| `name` | varchar | `organizationname` | |
| `addressStreet`, `addressCity`, `addressState`, `addressCountry`, `addressPostalCode` | address | `address`, `city`, `state`, `country`, `code` | |
| `phoneNumber`, `fax` | varchar | `phone`, `fax` | |
| `website` | url | `website` | |
| `logo` | image | `logoname` | файл логотипа — перенос на этапе 06.x; колонка `logo` пуста |
| `inn`, `kpp`, `okpo` | varchar | `inn`, `kpp`, `okpo` | |
| `bankAccount`, `bankName`, `bic`, `corrAccount` | varchar | `bankaccount`, `bankname`, `bankid`, `corraccount` | |
| `director`, `bookkeeper` | varchar | `director`, `bookkeeper` | |
| `entrepreneur`, `entrepreneurRegistration` | varchar | `entrepreneur`, `entrepreneurreg` | |

`vatid` пуст — поле не создаётся. Документы и платежи ссылаются на запись через `legalEntity` (D-48).

## 12. Расчётное ядро (этап 04.1)

Код: `custom/Espo/Modules/Itvolga/Tools/Finance/` (пространство имён `Espo\Modules\Itvolga\Tools\Finance`), PHP ≥ 8.3 + `bcmath` (есть на стенде и на production PHP 8.5.4), без зависимостей от EspoCRM и платных пакетов (D-45). Тесты: `task test:finance` (`tests/finance/run.php`).

### 12.1 Десятичная арифметика

- `Decimal` — неизменяемое десятичное число на bcmath. Вход — строка вида `-?\d+(\.\d+)?` (как отдаёт MySQL), int или `Decimal`; **float и прочие типы отклоняются** (`InvalidValue`), в том числе при вызове из кода без `strict_types`.
- Сложение, вычитание, умножение и процент (`x × p / 100`) — точные; округление — только явное `round(scale)`: 0,5 — от нуля (для положительных — вверх, D-29; для отрицательных — симметрично, как `ROUND` MySQL).
- `toFixed(scale)` не отбрасывает значащие цифры молча; `toString()` — кратчайшая запись.
- Разрядность (`Scale`): деньги — 2 знака, количество — 3, цена — 8, проценты — 3.

### 12.2 Новые документы (`DocumentCalculator`, D-47)

1. Скидка строки — суммой **или** процентом от `quantity × unitPrice` (процент округляется до копеек); сумма строки `amount = round(quantity × unitPrice − скидка, 2)`; маржа = `amount − purchaseCost`.
2. `subtotal = Σ amount` (итог = сумма округлённых строк, D-29); скидка документа — суммой **или** процентом от `subtotal` (округляется до копеек); `preTaxTotal = subtotal − скидка + shippingAmount`; налог 0 (D-21); `grandTotal = preTaxTotal + adjustment` (корректировка со знаком).
3. Проверки: хотя бы одна строка; количество > 0 (≤ 3 знаков), цена ≥ 0 (≤ 8), суммы скидок, доставки, корректировки и себестоимости — в копейках; проценты 0…100 (≤ 3 знаков); сумма и процент одновременно — ошибка (в Vtiger — один тип скидки); знак строки проверяется до округления (скидка больше суммы строки не исчезает в копейках).
4. Отклоняется с `RuleNotSupported` (правило и ссылка): НДС и налог доставки (D-21); отрицательные строки, скидка документа больше суммы строк, отрицательный итог, отрицательные значения, нулевое количество (D-47).

### 12.3 Исторические документы (`SourceVerifier`)

Классы формул (`FormulaClass`, поле `sourceFormula`) — только сочетания, встречающиеся в живых данных:

| Класс | Условие | Ожидаемые итоги |
|---|---|---|
| `noLineTax` | налога в строках нет (любой режим, любой `region_id`) | `subtotal = Σ net`, `preTaxTotal = total = subtotal − hdisc` |
| `lineTaxNotApplied` | individual, `region_id NULL`, налог в строках | то же (налог строк не входит в итоги) |
| `taxIncludedInPrice` | group_tax_inc, `region_id NULL`, налог в строках | то же (налог внутри цены) |
| `groupTaxAdded` | group, `region_id NULL`, одна ставка во всех строках, скидки документа нет | `total = preTaxTotal + round(round(preTaxTotal, 2) × ставка / 100, 2)` |
| `unverified` | всё остальное: налог в строках после 2018-07, процентные скидки, доставка, корректировка, групповой налог со скидкой или разными ставками, отрицательные количество, цена, скидка, ставка или сумма строки (возвраты), документ без строк | ожидаемых итогов нет; причина — в `reasons` |

Сравнение хранимого с пересчитанным (`TotalCheck`, поле `totalsCheck`): `exact` — равно точно; `rounded` — равно после округления пересчёта до копеек; `mismatch` — расхождение, показывается отдельно и не исправляется (D-05, D-46). Маржа строки (`MarginCheck`): `ok` (`net − purchaseCost`), `notComputed` (0 при ненулевой сумме), `mismatch`.

Результат на всех живых документах (срез `20260930T220947`, `SourceSnapshotTest`): 1078 из 1078 — `exact` по трём итогам, 0 `unverified`; классы и маржи совпадают со счётчиками независимого SQL (§4).

### 12.4 Платежи (`SourceAllocationResolver`, `AllocationCalculator`)

- `SourceAllocationResolver` — D-11 по категориям §8: распределить (`allocate`, сумма = платёж), нет распределения (`none` — в том числе расход со связью со счётом, Q-36), не решено (`unresolved` с причиной — только формы, которых нет в данных: удалённая или не документная цель `related_to`, несколько связей, заказ и связь одновременно, расход с `related_to`, нулевой платёж). Кандидат по буквальному D-11 сохраняется для отчёта.
- `AllocationCalculator::remainder` — остаток платежа; распределения > 0, в копейках, Σ ≤ суммы (`OverAllocation`).
- `AllocationCalculator::settle` — оплачено (приходы Executed и без статуса, Q-37), остаток `total − paid` (отрицательный при переплате), состояние `unpaid` / `partial` / `paid` / `overpaid`; прочие — исключённой суммой (D-49).
- На живых данных: категории 425/152/7/56/38/120 и покрытие счетов и заказов совпадают с SQL (§8); `unresolved` — 0; 52 расхода со связью — `none`.

### 12.5 Юрлицо (`LegalEntityResolver`)

`Default`, `По умолчанию`, пусто и NULL → ключ `Default` (единственная `LegalEntity`); иное значение — `UnknownLegalEntity` (сообщение без самого значения). На живых данных все 1876 значений документов и платежей разрешаются.

### 12.6 Как проверено

| Тест (`tests/finance/`) | Что проверяет |
|---|---|
| `DecimalTest` | разбор значений MySQL, отказ от float (в том числе в операциях из кода без `strict_types`), точность на границах DECIMAL(25,8), округление 0,5 от нуля (1.005 → 1.01, 2.675 → 2.68, −1.005 → −1.01) |
| `DocumentCalculatorTest` | D-29 (Σ округлённых строк ≠ округлению суммы), скидки суммой и процентом, доставка, корректировка ±, дробные часы, отказы D-21/D-47, повторный расчёт без дрейфа |
| `SourceVerifierTest` | синтетические документы всех 11 сочетаний «модуль × режим × класс» живых данных (список берётся из профиля источника; `tests/fixtures/synthetic/finance/source-documents.json`) и неподтверждённые формы, включая возвраты |
| `AllocationTest` | все категории D-11 (расход со связью — не распределяется; недопустимый `related_to` не заменяется связью) и неподтверждённые формы, остаток и перераспределение, состояние оплаты (пустой статус — оплата; распределения > 0 и в копейках на любом входе) |
| `LegalEntityResolverTest` | обе строки и пусто → одно юрлицо; иное — отказ без вывода значения |
| `ContractMapTest` | каждая финансовая строка `field-map.csv`/`relations.csv` с переносом имеет поле в §11 |
| `SourceSnapshotTest` (приватный срез; без него — пропуск) | все живые документы и платежи: классы, итоги, маржи, распределение, покрытие, юрлицо — против счётчиков профиля источника (`fixtures/source-profile.php`, серверные агрегаты); денежные контрольные суммы — против приватного `35_control_sums_private.tsv` и HMAC-дайджестов профиля |

Профиль источника пересобирается `task finance:profile -- <приватный срез>` (ключ HMAC — `/data/itvolga/espo-private/finance/control-digest.key`, вне Git). Негативные контроли (порча ядра: налог в итогах исторических документов, пустой статус не считается оплатой, распределение расходов, проверка знака строки после округления, пропуск платежа в суммах) роняют синтетические и приватные тесты.

## 13. Правила, которых нет в данных

Ничего не угадывается: правило либо подтверждено данными, либо принято владельцем, либо ядро отказывает.

| Правило | Что известно | Решение и поведение ядра |
|---|---|---|
| Распределение расходов, связанных со счетом клиента только связью | 52 расхода банковского импорта, плательщик ≠ контрагент, сумма ≠ итогу | не распределять (владелец, Q-36): `none`, связь — в отчёт |
| Приходы без статуса | 18 приходов 2015–2021, 5 связаны со счетами (4 — Paid) | считать оплатой как Executed (владелец, Q-37) |
| Процентная скидка строки и документа, доставка, корректировка ± в новых документах | в данных не встречаются; по коду Vtiger 7 процент — от `gross`/`subtotal`, доставка входит в `preTaxTotal`, корректировка прибавляется/вычитается | разрешены по D-47 (владелец, Q-38); налог доставки — нет (D-21) |
| Те же элементы в исторических документах | не встречаются | `unverified` (Vtiger считал их в браузере с плавающей точкой — воспроизведение не проверить) |
| Отрицательные строки и итоги (возвраты), нулевое количество | не встречаются | отказ (D-47) |
| Групповой налог со скидкой документа или разными ставками строк | по коду — база `subtotal − hdisc`; в данных только 2 счёта без скидки | исторические — `unverified`; новым не нужен (D-21) |
| Налог строк после обновления 2018-07 (individual: `subtotal` с налогом) | по коду Vtiger 7 — налог входит в `subtotal`; в данных нет | `unverified`; новым не нужен (D-21) |
| Налоговый учёт SalesPlatform до 2018-07 | кода Vtiger 6 нет | классы §12.3 выведены из данных; не проверено |

## 14. Реализация этапа 04.2 (Quote, SalesOrder, позиции, LegalEntity; 2026-10-01)

Сущности и поля — по §11 (проверено на стенде: колонки DECIMAL нужной точности, `number` varchar(100), уникальные `vtigerId` и `vtigerCompanyKey`); решения D-50…D-56. Код — `custom/Espo/Modules/Itvolga/` (`model.md`, раздел «Финансовые документы»).

### 14.1 Позиции в документе (D-50)

- Нехранимое поле документа `itemList` — полная таблица строк по порядку: `{id?, productId, description, quantity, unitPrice, discountAmount, discountPercent, taxRate, purchaseCost}` (строки — десятичные строки или целые). Строка без `id` создаётся, отсутствующая удаляется, `id` чужого документа или повтор — отказ; `order` = позиция в списке. При чтении `itemList` содержит также `order`, `productName`, `amount`, `margin` (значения как хранятся).
- Нет `itemList` в правке — строки не меняются (правка шапки пересчитывает по сохранённым строкам). Пустой список — отказ (`noLines`).
- Сохраняются вводимые значения скидки (сумма **или** процент); фактическая скидка процентом не хранится — она входит в `amount`, `preTaxTotal`, `grandTotal`.
- Отказы ядра и проверок — HTTP 400 с переводом `Global.messages.finance*` и местом («Строка 2, «НДС, %»»), без значения: float, неверная запись, лишние знаки, переполнение DECIMAL, НДС ≠ 0, доставка с налогом, обе скидки, процент > 100, количество ≤ 0, отрицательные значения и итоги, нет строк, неизвестный товар или строка.
- Предпросмотр: `POST /FinanceDocument/:entityType/calculate {id?, attributes}` — те же правила, ничего не пишет (живые итоги редактора; браузер с деньгами не считает).

### 14.2 Исторические документы (D-51)

| Правка импортированного документа | Итоги | `sourceFormula` / `totalsCheck` |
|---|---|---|
| статус, даты, контакт, сделка, ответственный, описание; товар, описание и порядок строк | хранимые итоги Vtiger без изменений | без изменений |
| расчётные данные (§14.1, D-51) | пересчёт ядром D-47; строки с `taxRate` ≠ 0 — отказ, пока пользователь не укажет 0 | очищаются; исходные итоги, расчётные данные шапки, `sourceFormula`, `totalsCheck` и строки — один раз в `vtigerData.sourceTotals` (`recalculatedAt` — UTC); снимок не заменяется, документ со снимком дальше считается рассчитанным в EspoCRM, даже если позже записаны пометки сверки |

Классификация при импорте — `task espo -- itvolga-finance-verify [--entity=…] [--id=…]` (`SourceVerifier`, нужен ключ `vtigerData.region_id`: NULL и 0 различаются; без ключа документ не классифицируется); каждый документ блокируется и перепроверяется в своей транзакции, сохраняются только `sourceFormula`/`totalsCheck` с `SaveOption::IMPORT`, суммы не трогаются (D-05).

Параллельные сохранения документа сериализуются блокировкой строки; сущность приводится к заблокированной строке: неизменённые расчётные данные, итоги и пометки берутся из строки (их видят расчёт и ответ API), изменённые сравниваются со строкой — ORM пишет только отличия от сохранённого, поэтому ни значение другого запроса, ни новый итог не теряются. Импорт (06.3) пишет документ и строки через ORM с `SaveOption::IMPORT` (значения и номер как в источнике), затем запускает эту команду.

### 14.3 Номера, юрлицо, связь документов (D-52, D-53, D-55)

- Новые номера: `ПРЕД_N`, `ЗАКАЗ_N` от `NextNumber` (старт — `cur_id` среза: 25 и 15, `app.itvolgaFinance`); занятые пропускаются; уникальность проверяется только у новых (D-17).
- `legalEntity` подставляется сервером у каждого документа (одна запись `Default`).
- `SalesOrder.quote` ↔ `Quote.salesOrders`; «Создать заказ» — `GET /FinanceDocument/Quote/:id/convertTo/SalesOrder` (заполненная форма). `SalesOrder.invoices`, `paymentAllocations` — этапы 04.3/04.4.
- Удаление документа удаляет его позиции (каскад в той же транзакции); номер не освобождается.

### 14.4 Доступ (D-54)

Директор — `Quote`, `SalesOrder` (полный), позиции и юрлицо — чтение; прочие роли — нет доступа (403, в меню нет вкладок). Позиции: чтение — по правам на документ (запись — `AclManager` документа, списки — по уровню чтения документа, фильтры `ForeignOnlyTeam/Own`), уровень позиции в роли доступ не расширяет; запись — никому. Справочник статусов — D-56 (подписи утверждены, `Delivered` — «Доставлено», Q-39).

## 15. Реализация этапа 04.3 (Invoice, InvoiceItem, контроль итогов; 2026-10-02)

Сущности и поля — по §11 и общему пути §14 (позиции через `itemList`, правило правки D-51, блокировка и номера), решения D-57…D-61. Проверено на стенде: колонки DECIMAL нужной точности, `date` для дат, `number` varchar(100), уникальный `vtigerId`, счётчик `Invoice` = 637.

### 15.1 Счёт

- Номер новых — `С-N` (кириллица), первый — 637; исходные `С-…`/`СЧЕТ_…` не меняются и не занимают счётчик (D-17, D-57).
- Статусы — словарь `vtigerValueMap/Invoice.json` (D-38): `AutoCreated`, `Cancel`, `Created`, `Approved`, `Sent`, `Credit Invoice`, `Paid` + пусто; подписи SalesPlatform, «Просрочен» у `Credit Invoice` утверждена (Q-41). Статус из оплат не выводится (D-26).
- Даты обязательны для формы и API (D-57); импорт их не проверяет.
- `balanceSource` — исходный `balance` как контрольное значение, только чтение; оплата и остаток — этап 04.4.
- Связи: контрагент, контакт, сделка, заказ, предложение (D-58), документы, архивная накладная (`VtigerArchive.invoice`), активности (D-61); обратные панели у Account, Contact, Opportunity, Document, Quote, SalesOrder.

### 15.2 Контроль итогов (D-59)

| Набор | Кто пишет | Когда очищается | Где виден |
|---|---|---|---|
| `sourceFormula`, `totalsCheck`, «Пересчёт ядра» (`expected*`) | `itvolga-finance-verify` (`SourceMarks`) | при пересчёте в EspoCRM; копия — в снимке `sourceTotals` | директору; «Пересчёт ядра» — при `rounded`/`mismatch` |
| «Итоги Vtiger» (`source*`) | сохранение с первым пересчётом импортированного документа (вместе со снимком) | никогда | директору, после пересчёта |

Хранимые итоги Vtiger не исправляются: расхождение показывается рядом (`totalsCheck` и «Пересчёт ядра»), а при правке расчётных данных исходные итоги остаются в «Итогах Vtiger» и снимке.

### 15.3 Импорт и юрлицо (D-60)

Импорт (06.3) пишет счёт и позиции через ORM с `SaveOption::IMPORT` и `SaveOption::SILENT` (§16.5): номер, даты (включая пустые), итоги, `balanceSource`, `vtigerData` (`region_id`, `spcompany` и прочие поля без рабочего поля) — как в источнике; затем `itvolga-finance-verify --entity=Invoice`. Каждое сохранение с этой опцией разрешает `vtigerData.spcompany` в единственную `LegalEntity`; неизвестное значение откатывает сохранение и останавливает команду без вывода значения.

### 15.4 Доступ

Как §14.4: директор — `Invoice` полностью, `InvoiceItem` — чтение по доступу к счёту; прочие роли — нет (403, вкладки нет); позиции напрямую не пишет никто.

## 16. Реализация этапа 04.4 (Payment, PaymentAllocation, оплата документов; 2026-10-02)

Сущности и поля — по §11; решения D-62…D-68. Проверено на стенде: `payment.amount`, `payment_allocation.amount`, `paid_amount`/`balance_amount` у `invoice` и `sales_order` — DECIMAL(25,8), `date_paid` — `date`, `number` varchar(100), уникальный `vtiger_id`, счётчик `Payment` = 991. Код — `Tools/Finance/Payment/` (чистое правило таблицы `AllocationEditor`), `Tools/FinancePayment/` (сохранение, оплата, импорт, история, «Добавить платёж», предпросмотр), `Hooks/Payment`, `Hooks/PaymentAllocation`; описание — `model.md`.

### 16.1 Факты источника (перепроверено 2026-10-02, только чтение)

- `SPPayments::save_module` пуст: сохранение платежа ничего больше не меняет — статус, `received` и `balance` счёта не трогаются (D-26).
- «Добавить платёж» на счёте или заказе (`SPPayments/views/Edit.php`): плательщик — контрагент документа, `related_to` — документ, сумма — итог документа (`hdnGrandTotal`, 2 знака); со страниц контрагента, контакта и поставщика — плательщик.
- Обязательны `pay_date` (`D~M`), `pay_type` (`V~M`), ответственный; `amount` в Vtiger необязателен (`N~O`, заполнен у 797 из 798, один — 0), в контракте — обязателен. Умолчания полей: «Приход», `Executed`, `Cashless Transfer`, `Default`. Номер — без префикса, `cur_id` 991.
- Доступ: общий доступ Public (`def_org_share = 2`), модуль скрыт во всех используемых профилях, кроме директорского (как Invoice).
- Справочники (шаг 41 дополнен `pay_type`, `type_payment`, `spstatus`): Приход 735 / Expense 63; Cashless Transfer 622 / Наличные 174 / пусто 2; Executed 776 / Запланирован 3 / Canceled 1 / пусто 18, `Delayed` настроен, не используется. Подписи SalesPlatform: Расход, Безналичный расчет, Выполнен, Отменен, Просрочен; у «Приход», «Наличные», «Запланирован» подписи нет — значения русские.
- История (`vtiger_modtracker`): `related_to` менялся у 43 платежей по одному разу (2018-09…2020-04) — 27 переносов «счёт → счёт» и 16 заполнений; статус — 2 раза «Запланирован → Executed», 1 раз «пусто → Executed». В Vtiger «повторное применение» — перенос платежа на другой документ.

### 16.2 Таблица распределений (D-63)

| Ввод | Результат |
|---|---|
| полная таблица `allocationList` | строка с `id` сохраняет свою строку; без `id` — новая или строка того же документа; отсутствующая — удаляется (отмена) |
| таблица не передана | строки не меняются; смена суммы, статуса или типа проверяется по сохранённым строкам |
| второй ряд того же документа | отказ `financeAllocationDuplicateTarget` |
| Σ строк > суммы / сумма < распределённой | `financeOverAllocation` / `financeAmountBelowAllocated` |
| расход со строками / переключение в расход со строками | `financeOutgoingAllocation` |
| строка ≤ 0, доли копейки, float, обе цели или ни одной, чужой `id`, нет документа или он недоступен на чтение (у новой, перенесённой — оба документа, с другой суммой, удалённой строки) | `financeAllocationNotPositive`, `financeTooManyDecimals`, `financeFloat`, `financeAllocationTargetExclusive` / `…Required`, `financeUnknownAllocation`, `financeAllocationUnknownTarget` |

Отказы — HTTP 400 с переводом и местом («Строка 2, «Сумма»»), без значений; ничего не пишется, номер не занимается. Переплата документа допустима. Предпросмотр формы — `POST /FinanceDocument/Payment/calculate {id?, attributes: {amount, direction, allocationList}}` → `{allocatedAmount, unallocatedAmount}` или `{error}`.

### 16.3 Оплата документа (D-64)

| Событие | Что пересчитывается |
|---|---|
| строка добавлена, изменена, удалена, перенесена | её документ (при переносе — оба) |
| статус или тип платежа изменён | все документы платежа |
| платёж удалён | все его документы (строки удаляются под «журналом», как при удалении документа) |
| итог документа изменён (позиции, скидка, корректировка) | остаток и состояние по сохранённому «оплачено» |
| документ создан | не оплачен, остаток = итог |
| документ удалён | его строки удаляются под «журналом» (блокирующим чтением, не каскадом ядра), остаток платежей растёт, в лентах платежей — заметка |

«Оплачено» — сумма строк приходов в статусе `Executed` и без статуса (Q-37); остаток — итог минус оплачено (отрицательный — переплата); `unpaid` / `partial` / `paid` / `overpaid`. Порядок блокировок и свежесть чтений — D-64; `itvolga-finance-settle [--entity] [--id] [--dry-run] [--silent]` пересчитывает документы по строкам и печатает только счётчики.

### 16.4 История и доступ (D-65, D-66, D-62)

Лента платежа — создание, изменения полей и таблицы распределений («было → стало»); журнал аудита счёта и заказа — изменения «Оплачено», «Остаток к оплате», «Состояние оплаты» с автором. Директор — платежи полностью, распределения — чтение по доступу к платежу; прочие роли — 403, вкладки нет. Прямая запись распределений, link/unlink связей платежа, документа и плательщика, массовые действия над распределениями, CSV-импорт финансовых сущностей и восстановление удалённых распределений закрыты для всех, включая администратора. Строки, удалённые вместе с платежом или документом, помечены владельцем (`PaymentAllocation.removedWith` = «Тип:id», служебное поле); восстановление такого платежа, счёта или заказа — 409 `financeRestoreOwnerDenied` (`OwnerRestorer`; строки — `financeRestoreDenied`), строки, отменённые правкой таблицы, ему не мешают.

### 16.5 Импорт (D-68)

Импорт (06.3) пишет платежи и строки — как и документы с позициями — через ORM с `SaveOption::IMPORT` и `SaveOption::SILENT` (`tests/stage04/import_fixture.php` — то же на синтетике; `IMPORT` сохраняет исходные значения, а ленту, аудит, уведомления о назначении и вебхуки ядро гасит только по `SILENT`; запись финансовой сущности с `IMPORT` без `SILENT` отклоняется `Hooks/Common/FinanceSilentImport` до записи): платёж — номер, статус и даты как в источнике, юрлицо из `vtigerData.spcompany`; строка — `source`, `sourceConflict`, `vtigerData` по D-11 (§8, `SourceAllocationResolver`), с проверкой платежа, документа, единственности и суммы; затем `itvolga-finance-settle`. Отчёт конфликтов (38) и связей расходов (52) — этап 06.3.

## 17. Реализация этапа 04.5 (Act, ActItem, связь счёта и акта; 2026-10-03)

Сущности и поля — по §11 и общему пути документов §14 (позиции через `itemList`, правило правки D-51, блокировка, номера, контроль итогов §15.2, юрлицо импорта §15.3); решения D-69…D-71. Проверено на стенде: колонки DECIMAL как у счёта, `date_act` — `date`, `number` varchar(100), уникальный `vtiger_id` у акта и позиций, неуникальный индекс `invoice.act_id`, таблица `act_document`, счётчик `Act` = 403. Код — запись `documents.Act` и `conversions.Invoice.Act` в `metadata/app/itvolgaFinance.json`, `Tools/FinanceDocument/ConversionSourceGuard.php`; описание — `model.md`.

### 17.1 Факты источника (перепроверено 2026-10-03, только чтение)

- 404 живых акта (1 удалён), 417 строк (391 акт — 1 строка, 13 — 2), все строки — услуги; дата пуста у 1 акта (диапазон 2018-06…2026-09), номер пуст у 1, номера — только цифры (`9` 8, `99` 92, `999` 303), 2 номера повторяются у 4 актов (все созданы в 2018), максимальный — 402, счётчик `cur_id` 403 без префикса.
- Статусы: Created 291, Sent 55, Received 39, Done 5, пусто 14; настроенный список `sp_actstatus` — Created, Sent, Done, Received (подписи SalesPlatform: Создан, Отправлен, Выполнен, Получен), умолчание поля — Created; обязательны (`~M`) дата, статус, контрагент и ответственный, название — нет (заполнено у всех).
- Режим налога: individual 383, group_tax_inc 21; `region_id` = 0 у всех, налога в строках нет (класс `noLineTax`); `spcompany` `Default` 402 / `По умолчанию` 2; скидка, доставка и корректировка шапки — 0; скидка строки — у 1 строки; дробные количества — у 97; маржа — у всех 417.
- Счёт → акт: 392 живых счёта → 392 разных живых акта; 12 живых актов без живого счёта (1 — только с удалённым счётом); совпадают контрагент 392, юрлицо 391, режим налога 389, итог 387 (у 5 итог акта больше), строки 387; дата акта раньше даты счёта у 20 пар; поле `sp_act_id` вручную не менялось (0 записей истории).
- Платежи: `related_to` — Invoice 616, SalesOrder 7, пусто 176; ни одной ссылки и связи `vtiger_crmentityrel` с актами.
- Связанные списки Vtiger: акт → счета, документы (42 живые связи), активности и подписанные записи (0 записей); контрагент → акты; документ → акты; комментарии к актам — 0. История статусов `vtiger_sp_actstatushistory` — 51 запись (2019-01…2022-01), не переносится (Q-27).
- Доступ: модуль виден в тех же профилях, что и счета; общий доступ Public.

### 17.2 Акт

| Что | Поведение |
|---|---|
| Номер | новые — счётчик без префикса с 403, занятые (в том числе импортированные и удалённых актов) пропускаются; импортированные — как есть, включая повторы и пустой (D-17) |
| Дата, статус | «Дата акта» обязательна для формы и API, по умолчанию — сегодня; импорт — как есть (в том числе пусто); статусы D-38, пусто остаётся пустым, новые — «Создан» |
| Итоги | ядро D-47 для новых, исходные итоги — эталон для импортированных (D-05), «Пересчёт ядра» и «Итоги Vtiger» — как у всех документов (D-59) |
| Связи | контрагент, контакт, юрлицо, ответственный и команды, документы, счета; обратные панели «Акты» у контрагента, контакта, документа; без сделки, условий, заказа, активностей, ленты и платежей |
| Доступ | директор — полностью; позиции — чтение по доступу к акту, напрямую не пишутся никем; прочие роли — 403, вкладки нет; вкладка «Акты» — между «Счета» и «Платежи» |

### 17.3 Счёт и акт (D-70, D-71)

| Действие | Результат |
|---|---|
| «Создать акт» на счёте без живого акта | форма акта, заполненная сервером (поля шапки и строки счёта, ссылка на счёт в `invoicesIds`); при сохранении — новый акт и `Invoice.act` в одной транзакции |
| «Создать акт» на счёте с живым актом | вместо кнопки — «Открыть акт»; запрос формы и сохранение — 409 `financeConversionLinked` |
| поле «Акт» в форме счёта | привязать счёт к существующему акту, перепривязать или очистить; несколько счетов на один акт; изменения — в журнале аудита счёта |
| панель «Счета» акта | список связанных счетов, только просмотр |
| удаление акта | акт и позиции удаляются; у счетов ссылка остаётся (имя не показывается, «Создать акт» снова доступен); восстановление администратором возвращает связь |
| удаление счёта | акт остаётся без этого счёта |

Правки счёта и акта друг друга не меняют: строки и итоги каждого документа хранятся отдельно (у 5 пар источника итоги различаются).

### 17.5 Исправления по ревью качества (D-72)

- Блокирующие чтения документов, платежей и распределений (сохранение, оплата, удаление, сверка, `itvolga-finance-verify`, `itvolga-finance-settle`) блокируют только строку самой записи (`RowLock`): прежде `FOR UPDATE` полной записи блокировал и строки из JOIN имён — контрагента, контакта, пользователей, единственного юрлица и акта счёта, — отчего независимые сохранения выстраивались в очередь и могли взаимно блокироваться.
- Позиции документов не восстанавливаются по отдельности (409 `financeRestoreItemDenied`); документ восстанавливается вместе с позициями, удалёнными вместе с ним, — строки, удалённые при живом документе (правкой таблицы или импортом), помечены `removedByEdit` и не возвращаются (`ItemRestorer`; прежде строка, удалённая правкой в ту же секунду, что и документ, возвращалась без пересчёта итога).
- Панель «Счета» акта — только просмотр (в меню строки нет правки и удаления счёта).

### 17.4 Импорт (06.3)

Импорт пишет акт и позиции через ORM с `SaveOption::IMPORT` и `SaveOption::SILENT` (§16.5): номер, дата и статус (в том числе пустые), итоги, `vtigerData` (`region_id`, `spcompany`) — как в источнике; затем `itvolga-finance-verify --entity=Act`. Связь со счётом записывает импорт счёта (`actId`), без заполнения формы; правило «один живой акт» на импорт не действует (`tests/stage04/import_fixture.php` — то же на синтетике).

## 18. Сквозной сценарий (этап 04.6; 2026-10-03)

Цепочка Quote → SalesOrder → Invoice → Act → Payment и варианты источника проверены на стенде тестами `tests/stage04/test_stage04_6.py` и в браузере; решения D-73…D-76. Нового функционала нет: исправлены дефект переноса команд и несогласованности доступа, номера и панелей.

### 18.1 Факты источника (перепроверено 2026-10-03, только чтение, срез `20261003T135407`, шаг `scripts/audit/sql/48_finance_chain.sql`)

| Форма цепочки по 636 живым счетам | Счетов |
|---|---|
| счёт без заказа, акта и оплат | 45 |
| только оплата | 172 |
| только акт | 33 |
| акт и оплата | 359 |
| из заказа, без оплаты | 16 |
| из заказа, с оплатой | 11 |

- Полной цепочки в источнике нет: предложения не становились заказами (0 из 24), у счетов из заказов нет актов. Из 14 заказов 12 выставлены счетом, 3 оплачены напрямую, 2 — и то и другое (их 11 счетов тоже оплачены, D-78).
- Связанные пары (поля, которые копирует конвертация): счёт → акт 392 — совпадают контрагент, контакт, ответственный и юрлицо 392, режим налога 389, итог 387, акт создан позже 392; заказ → счёт 27 — контрагент 26, контакт 17, ответственный 27, юрлицо 27, режим налога 27, итог 19, счёт создан позже 24 (3 счёта старше своего заказа — связаны позже полем).
- Платежи: приходы на счета 620 (плательщик — контрагент счёта у 580), расходы со связью со счётом 52 (не распределяются, Q-36), на заказы 7 (плательщик — контрагент 7).
- У всех финансовых записей один ответственный и один создатель (тот же пользователь): правила переноса ответственного данными не проверить — только кодом SalesPlatform (форма из документа заполняется одноимёнными полями, §7).
- Статус счёта и акт: Paid 562 (с актом 367), Cancel 17 (16), Created 33 (2), Sent 9 (4), Credit Invoice 6 (3), Approved 5, пусто 4 — статусы ставятся вручную (D-26).

### 18.2 Цепочка в EspoCRM

| Шаг | Действие | Переносится | Не переносится |
|---|---|---|---|
| Quote → SalesOrder | «Создать заказ» (D-52) | название, контрагент, контакт, сделка, ответственный, команды, режим налога, скидки, доставка, корректировка, адреса, условия, описание, строки (без сумм); ссылка `quote` | статус, номер, даты, итоги, пометки источника, юрлицо (подставляет сервер) |
| Quote/SalesOrder → Invoice | «Создать счёт» (D-58) | то же; из заказа — и его предложение | то же; дата счёта — сегодня, срок — вводит пользователь |
| Invoice → Act | «Создать акт» (D-71) | то же без сделки и условий; ссылка — ключ `act` счёта | то же; дата акта — сегодня |
| Invoice/SalesOrder → Payment | «Добавить платёж» (D-67) | плательщик — контрагент документа, сумма — итог документа, одна строка распределения | ответственный — текущий пользователь, не владелец документа; команды не копируются |

Правила, проверенные на одном наборе записей (`ChainTest`) и в вариантах источника (`VariantTest`):

- **Статусы** не копируются и не выводятся: у нового документа — своё умолчание («Создан», платёж — «Выполнен»), источник сохраняет свой; оплата, акт и отмена платежа статус документа не меняют (D-26).
- **Ответственный и команды** документа — как у источника; создатель — сохранивший пользователь; позднее изменение ответственного у источника на созданные документы не переносится. Исправлено: команды источника не загружались, и форма получала пустые команды вместо команд источника (G1, `DocumentConverter` загружает поля linkMultiple списка полей конвертации).
- **Итоги и налоги**: новый документ считает ядро (D-47) — при неизменных строках итоги всех документов цепочки равны; налог 0 в любом режиме (D-21); исторические ставки 18 % видны в форме, сохранение — отказ `financeVat` без записи и номера, после указания 0 — документ; исходные строки и итоги источника не меняются.
- **Номера**: новые — из счётчиков, заполнение формы номер не занимает; номер сохранённого документа или платежа меняет только импорт (D-74) — правка через API (поле только для чтения), пересчёт, сверка, оплата, ORM-сохранение без импорта номер не меняют; исходные номера (включая пустой и повторы актов) — как есть.
- **Доступ**: директор — вся цепочка; заместитель, менеджеры и пользователь без роли — 403 на записи, создание, заполнение форм и панели финансов у контрагента; смена статуса или типа платежа и его удаление требуют права чтения каждого документа платежа (D-73).
- **Навигация**: предложение — «Заказы», «Счета»; заказ — «Предложение», «Счета», «Оплаты»; счёт — «Предложение», «Заказ», «Акт», «Оплаты»; акт — «Счета»; платёж — ссылки на документы в таблице распределений; контрагент — вкладка «Финансы» (предложения, заказы, счета, акты, платежи); контакт — те же панели; сделка — предложения, заказы, счета. Панели документов — навигация (D-75).

### 18.3 Варианты источника

| Вариант | Что проверено |
|---|---|
| счёт без предложения и заказа (большинство) | акт и платёж из счёта, ссылки `quote`/`salesOrder` пусты, оплата, статус не меняется |
| заказ → счёт и прямая оплата заказа | оплата заказа и счёта независимы (2 заказа источника, D-78); у счёта из заказа может быть акт (в источнике — ни одного) |
| заказ привязан к старому счёту позже | связь видна в «Счетах» заказа; номер, статус и итоги счёта не меняются |
| акт без счёта (12 в источнике) | «Счета» пусты, в «Актах» контрагента; платежа к акту нет (404) |
| импортированные счёт, акт и платёж | номера Vtiger, «Оплачен»/«Получен»/пустой статус, пустой статус платежа засчитывается (Q-37), «Создать акт» — 409, «Добавить платёж» — итог источника; правки директора номера не меняют |
| исторические ставки 18 % → «Создать акт» | отказ `financeVat`, после 0 — акт; строки и итоги счёта прежние |

### 18.4 Покрытие полей и связей аудита

`docs/migration/finance-coverage.md` — генерируется `task finance:coverage` (`scripts/model/build_finance_coverage.py`) из `field-map.csv`, `relations.csv` и модели; `task model:check` проверяет, что документ свежий и открытых строк нет. Область: модули Quotes, SalesOrder, Invoice, Act, SPPayments, PurchaseOrder (записей нет), Consignment (архив), VTEItems (исключены), ссылки других модулей на документы, таблицы без модуля (строки, платежи, юрлицо, налоги и валюта, справочники, история статусов, нумерация, печатные формы, настройки Quoter) и общие колонки записей; таблицы, похожие на финансовые, но вне области, перечислены с причиной. Каждая строка получает один итог: перенос, рабочее поле (в источнике пусто), справочник, архив, ключ, настройка, этап 05, исключено, пусто или открыто; реализованная строка заново проверяется моделью. На срезе `20261003T135407`: 760 полей и 87 связей, открытых — 0; цепочка реестра (позиции, четыре конвертации, две цели платежей) — ok.

В картах статус `контракт (этап 04.1)` заменён окончательным (`build_maps.py`, `finance_status`): 38 строк, которые ничего не переносят (постоянный курс, канал создания, «звёздочки», теги, пустые служебные колонки, ключ и пустые реквизиты юрлица, справочник `spcompany`), и связь `Act.salesorderid` — `решено`; ключи платежа `sp_payments.payid`, `sp_paymentscf.payid` проверяются как `Payment.vtigerId` — `реализовано (этап 04.4)`.

### 18.5 Не проверено / открыто

- Решено владельцем 2026-10-03: совпадение сторон связанных документов при ручной привязке не проверяется (D-77, Q-42); оплата заказа и его счетов независима (D-78, Q-43).
- Правила переноса ответственного проверены кодом SalesPlatform и решениями владельца (D-52, D-67, D-71), данными — нет (один пользователь).
- Сверка значений живых записей после импорта — этапы 06.3–06.4; печатные формы — этап 05 (§19).

## 19. Печатные формы (этап 05; 2026-10-03)

Формы счёта, акта, ПКО, коммерческого предложения и заказа — код модуля (D-79…D-83, `print-forms.md` §3). Финансовые правила печати:

- **Суммы не пересчитываются.** Печатаются хранимые значения документа и строк (D-05): `subtotal`, `shippingAmount`, `preTaxTotal`, `adjustment`, `grandTotal`, `amount` строки. Скидка документа выводится как `subtotal + shippingAmount − preTaxTotal`, НДС — как `grandTotal − preTaxTotal − adjustment`. Строка «НДС» появляется, только если разность не ноль (2 счёта `groupTaxAdded`), иначе «Без налога (НДС)» (D-21). Контрольные поля (`expected*`, `source*`, снимок `sourceTotals`) не печатаются.
- **Скидка строки** — введённая сумма или процент от `quantity × unitPrice`, округлённый до копеек, как его применяет `DocumentCalculator` (D-47). Тогда `quantity × unitPrice − скидка` до округления строки равно `amount`.
- **Числа и даты** — `Tools/Finance/Printing/Formatter`: только `Decimal`, без округления и без float; дата «3 октября 2026 г.» — ICU (`IntlDateFormatter`, ru_RU, родительный падеж месяца; нужно расширение PHP `intl` — есть на стенде и в образе `php_docker` Ansible). Деньги и цены печатаются минимум с 2 знаками и со всеми значащими (цена до 8), количество — без хвостовых нулей. Разделитель групп — неразрывный пробел, десятичный — запятая.
- **Сумма прописью** — `AmountInWords` (словоформы SalesPlatform `num2str`, совпадение на 22 113 значениях). Работает по группам из трёх цифр строки, поэтому точна для любого DECIMAL(25,8). Сумма с долями копейки отклоняется, а не округляется.
- **ПКО** печатает сумму платежа (`amount`), а не распределения. Форма есть только у приходов (D-81).
- **Доступ к полям**: значение поля, которое пользователю запрещено читать, не печатается. Запрещённая сумма документа, строки или платежа, как и запрет таблицы строк `itemList`, отказывает в печати (403): форма без сумм вводила бы в заблуждение.
- **Условия** новых предложений, заказов и счетов по умолчанию — общий текст `vtiger_inventory_tandc` (D-83). Импорт (06.3) передаёт `termsAndConditions` источника явно.

Проверено на стенде — `tests/stage05/test_stage05.py`:
- исторические классы `lineTaxNotApplied` и `groupTaxAdded` (значения записаны SQL как у импорта);
- скидки строк суммой и процентом, скидка документа, доставка;
- пустые номер и дата, адрес документа и адрес контрагента;
- 60 строк акта на нескольких страницах;
- права ролей, отсутствие записи в БД (`CHECKSUM TABLE` до и после печати).

Чистые правила — `tests/finance/{PrintFormatterTest,AmountInWordsTest,PrintPresenterTest}.php`.
