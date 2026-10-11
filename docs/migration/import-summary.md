# Импорт Vtiger — сводка прогона (этапы 06.2–06.3)

Генерируется: `task import:summary -- <прогон>` (`scripts/import/importer.py summary`). Только счётчики: ни значений, ни идентификаторов записей. Машинный отчёт с причинами по каждой записи и колонке — вне Git (`/data/itvolga/espo-private/import/<прогон>/`). Контракт импорта — `import.md`.

- Прогон: `20261011T170315`; снимок: `20261006T201216`; код: `f09c1c5` (незакоммиченных файлов инструмента: 18).
- Итог: **findings**; проблемы: нет; находки: conflict=47, dangling=1, discrepancy:invoice_act_total=5, no_target=66, pending=9, type_conflict=23.
- «Тишина» (изменение числа строк стенда: уведомления, напоминания, подписки, записи ленты без vtigerId, письма, вебхуки, журнал действий): action_history_record=0, email_not_imported=0, note_not_imported=0, notification=0, reminder=0, stream_subscription=0, webhook_queue_item=0.

## Записи

| Сущность | Источник | Запись | Проверка | Удержаны | Возвращено после хуков |
|---|---|---|---|---|---|
| Account | 180 | unchanged=180 | equal=180 | — | — |
| Act | 404 | unchanged=404 | equal=404 | — | — |
| ActItem | 417 | unchanged=417 | equal=417 | — | — |
| Attachment | 205 | unchanged=205 | equal=205 | — | — |
| Call | 17 | unchanged=17 | equal=17 | — | — |
| Case | 45 | unchanged=45 | equal=45 | — | — |
| Contact | 341 | unchanged=341 | equal=341 | — | — |
| ContactAccess | 341 | skipped=214, unchanged=127 | absent=214, equal=127 | — | — |
| Document | 215 | unchanged=215 | equal=215 | — | — |
| DocumentFolder | 1 | unchanged=1 | equal=1 | — | — |
| Email | 29 | unchanged=29 | equal=29 | — | — |
| Invoice | 636 | unchanged=636 | equal=636 | — | — |
| InvoiceItem | 712 | unchanged=712 | equal=712 | — | — |
| KnowledgeBaseArticle | 63 | unchanged=63 | equal=63 | — | — |
| KnowledgeBaseCategory | 1 | unchanged=1 | equal=1 | — | — |
| Lead | 225 | unchanged=225 | equal=225 | — | — |
| LegalEntity | 1 | unchanged=1 | equal=1 | — | — |
| Meeting | 7 | unchanged=7 | equal=7 | — | — |
| Note | 78 | unchanged=78 | equal=78 | — | — |
| Opportunity | 156 | unchanged=156 | equal=156 | — | — |
| Payment | 799 | unchanged=799 | equal=799 | — | — |
| PaymentAllocation | 627 | unchanged=627 | equal=627 | — | — |
| Product | 28 | unchanged=28 | equal=28 | — | — |
| Project | 54 | unchanged=54 | equal=54 | — | — |
| ProjectTask | 493 | unchanged=493 | equal=493 | — | — |
| Quote | 24 | unchanged=24 | equal=24 | — | — |
| QuoteItem | 27 | unchanged=27 | equal=27 | — | — |
| SalesOrder | 14 | unchanged=14 | equal=14 | — | — |
| SalesOrderItem | 14 | unchanged=14 | equal=14 | — | — |
| Task | 62 | unchanged=62 | equal=62 | — | — |
| User | 7 | unchanged=7 | equal=7 | — | — |
| Vendor | 3 | unchanged=3 | equal=3 | — | — |
| VtigerArchive | 321 | unchanged=321 | equal=321 | — | — |

## Колонки источника по модулям

Все колонки всех прочитанных таблиц по живым записям модуля. «Правило» — колонка переносится правилом спецификации; для них значения сверены проверочным проходом (несверенный остаток — нули «0 = пусто», ожидание следующего этапа, удержанные записи). «Исключено»/«пусто» — судьба из `field-map.csv`, значения не переносятся. «Значений» — непустых по выражению аудита (`nonempty_expr`: ноль и «нет» — тоже значения); значимых (ненулевых, «да») в колонках «пусто по карте» нет — иначе прогон дал бы находку «карта устарела».

| Модуль | Колонок с правилом | Значений | Сверено | Расхождений | Неучтённых | Ключи | Исключено (колонок/значений) | Пусто по карте (колонок/значений) | Без строки карты (колонок/значений) |
|---|---|---|---|---|---|---|---|---|---|
| Accounts | 40 | 4190 | 4053 | 0 | 0 | 6 | 7/1080 | 12/720 | 0/0 |
| Act | 50 | 15871 | 15473 | 0 | 0 | 6 | 12/3243 | 6/404 | 0/0 |
| Assets | 21 | 51 | 51 | 0 | 0 | 3 | 5/15 | 5/3 | 0/0 |
| Attachments | 4 | 615 | 615 | 0 | 0 | 1 | 0/0 | 1/0 | 0/0 |
| Calendar | 13 | 398 | 398 | 0 | 0 | 3 | 14/374 | 8/34 | 5/0 |
| Consignment | 57 | 60 | 60 | 0 | 0 | 6 | 7/8 | 7/1 | 0/0 |
| Contacts | 46 | 8540 | 8428 | 0 | 0 | 7 | 11/3410 | 17/1023 | 0/0 |
| Documents | 22 | 2834 | 2817 | 0 | 0 | 4 | 6/1074 | 5/215 | 1/0 |
| Emails | 16 | 437 | 379 | 0 | 0 | 4 | 10/261 | 6/29 | 15/0 |
| Events | 16 | 723 | 723 | 0 | 0 | 3 | 11/520 | 11/208 | 2/0 |
| Faq | 11 | 691 | 628 | 0 | 0 | 3 | 7/378 | 5/63 | 1/0 |
| HelpDesk | 18 | 743 | 631 | 0 | 0 | 4 | 7/270 | 8/45 | 0/0 |
| Invoice | 62 | 31268 | 27870 | 0 | 0 | 7 | 10/4528 | 9/636 | 0/0 |
| JVmes | 12 | 2937 | 2937 | 0 | 0 | 3 | 5/1335 | 5/267 | 1/0 |
| Jivosite | 14 | 529 | 529 | 0 | 0 | 3 | 5/245 | 5/49 | 1/0 |
| Leads | 33 | 4413 | 3763 | 0 | 0 | 6 | 11/2250 | 26/450 | 0/0 |
| ModComments | 10 | 779 | 626 | 0 | 0 | 4 | 6/468 | 11/234 | 1/0 |
| OrganizationDetails | 22 | 22 | 22 | 0 | 0 | 0 | 1/1 | 2/0 | 0/0 |
| Potentials | 20 | 2691 | 2572 | 0 | 0 | 3 | 11/1560 | 16/312 | 0/0 |
| Products | 15 | 42 | 34 | 0 | 0 | 3 | 9/24 | 33/15 | 0/0 |
| Project | 20 | 946 | 928 | 0 | 0 | 3 | 6/270 | 5/54 | 0/0 |
| ProjectTask | 19 | 8895 | 8895 | 0 | 0 | 4 | 6/2465 | 5/493 | 0/0 |
| Quotes | 56 | 1105 | 1052 | 0 | 0 | 7 | 10/171 | 6/24 | 0/0 |
| SPPayments | 26 | 14470 | 14109 | 0 | 0 | 4 | 6/3807 | 5/799 | 0/0 |
| SalesOrder | 65 | 710 | 620 | 0 | 0 | 8 | 10/98 | 12/14 | 0/0 |
| ServiceContracts | 22 | 18 | 18 | 0 | 0 | 3 | 5/5 | 5/1 | 1/0 |
| Services | 19 | 359 | 338 | 0 | 0 | 4 | 7/150 | 10/50 | 0/0 |
| Users | 21 | 121 | 114 | 0 | 0 | 2 | 37/207 | 32/0 | 0/0 |
| Vendors | 12 | 27 | 27 | 0 | 0 | 4 | 6/15 | 14/3 | 0/0 |

## Исходы значений

| Модуль | Исходы |
|---|---|
| Accounts | archived=189, carried=3101, duplicate=6, linked=540, mapped=147, normalized=69, type_conflict=1, zero_empty=137 |
| Act | archived=1252, carried=11361, linked=2456, mapped=404, zero_empty=398 |
| Assets | archived=51 |
| Attachments | archived=3, carried=612 |
| Calendar | carried=292, linked=102, mapped=4 |
| Consignment | archived=60 |
| Contacts | archived=684, carried=5760, duplicate=5, linked=1258, mapped=42, no_target=14, normalized=152, not_applicable:D-23=5, protected=493, type_conflict=20, zero_empty=107 |
| Documents | archived=82, carried=879, derived_equal=568, linked=861, mapped=427, not_applicable:D-23=3, zero_empty=14 |
| Emails | archived=2, carried=203, duplicate=29, linked=87, mapped=29, normalized=29, zero_empty=58 |
| Events | archived=7, carried=404, derived_equal=100, linked=156, mapped=56 |
| Faq | carried=366, linked=189, mapped=73, zero_empty=63 |
| HelpDesk | archived=64, carried=353, linked=184, mapped=30, zero_empty=112 |
| Invoice | archived=1800, carried=20595, linked=4839, mapped=636, zero_empty=3398 |
| JVmes | archived=2937 |
| Jivosite | archived=529 |
| Leads | archived=30, carried=2598, duplicate=1, linked=675, mapped=288, normalized=170, type_conflict=1, zero_empty=650 |
| ModComments | archived=79, carried=234, dangling:not_a_user=1, linked=313, zero_empty=152 |
| OrganizationDetails | carried=21, linked=1 |
| Potentials | archived=469, carried=1345, linked=661, mapped=97, zero_empty=119 |
| Products | archived=1, carried=21, linked=9, mapped=3, zero_empty=8 |
| Project | archived=55, carried=572, linked=251, normalized=50, zero_empty=18 |
| ProjectTask | carried=6923, linked=1972 |
| Quotes | archived=49, carried=753, linked=203, mapped=47, zero_empty=53 |
| SPPayments | archived=612, carried=8125, linked=3776, mapped=1596, zero_empty=361 |
| SalesOrder | archived=70, carried=419, linked=104, mapped=27, zero_empty=90 |
| ServiceContracts | archived=18 |
| Services | archived=24, carried=188, linked=75, mapped=51, zero_empty=21 |
| Users | archived=1, carried=60, linked=1, mapped=49, normalized=3, not_applicable:D-37=7 |
| Vendors | carried=17, linked=9, type_conflict=1 |

## Связи

| Источник связи | Исходы | Сверено | Расхождений |
|---|---|---|---|
| `cntactivityrel:Contacts->Call` | linked=1 | 1 | 0 |
| `cntactivityrel:Contacts->Meeting` | linked=2 | 2 | 0 |
| `cntactivityrel:Contacts->Task` | linked=3 | 3 | 0 |
| `contpotentialrel:Contacts->Potentials` | linked=5 | 5 | 0 |
| `crmentityrel:Accounts->Calendar` | duplicate=20, linked=2 | 22 | 0 |
| `crmentityrel:Accounts->Contacts` | linked=20 | 20 | 0 |
| `crmentityrel:Accounts->HelpDesk` | duplicate=3 | 3 | 0 |
| `crmentityrel:Accounts->Invoice` | conflict=1, duplicate=442 | 442 | 0 |
| `crmentityrel:Accounts->Potentials` | duplicate=63 | 63 | 0 |
| `crmentityrel:Accounts->Project` | duplicate=3 | 3 | 0 |
| `crmentityrel:Accounts->SPPayments` | duplicate=180 | 180 | 0 |
| `crmentityrel:Contacts->Calendar` | duplicate=2, linked=1 | 3 | 0 |
| `crmentityrel:Contacts->Emails` | duplicate=1 | 1 | 0 |
| `crmentityrel:Contacts->HelpDesk` | linked=3 | 3 | 0 |
| `crmentityrel:Contacts->Invoice` | duplicate=2 | 2 | 0 |
| `crmentityrel:Contacts->Jivosite` | linked=1 | 1 | 0 |
| `crmentityrel:Contacts->SPPayments` | duplicate=5 | 5 | 0 |
| `crmentityrel:Invoice->Calendar` | duplicate=1 | 1 | 0 |
| `crmentityrel:Invoice->Consignment` | duplicate=1 | 1 | 0 |
| `crmentityrel:Invoice->SPPayments` | conflict=38, duplicate=426, linked=4, no_target=52 | 482 | 0 |
| `crmentityrel:Leads->Calendar` | conflict=3, duplicate=32, linked=3 | 35 | 0 |
| `crmentityrel:Leads->Emails` | duplicate=1 | 1 | 0 |
| `crmentityrel:Leads->Jivosite` | duplicate=37 | 37 | 0 |
| `crmentityrel:Potentials->Calendar` | duplicate=24 | 24 | 0 |
| `crmentityrel:Potentials->Emails` | duplicate=23 | 23 | 0 |
| `crmentityrel:Potentials->Invoice` | duplicate=20 | 20 | 0 |
| `crmentityrel:Potentials->Quotes` | duplicate=1 | 1 | 0 |
| `crmentityrel:Potentials->Services` | linked=3 | 3 | 0 |
| `crmentityrel:Project->ProjectTask` | conflict=5, duplicate=481 | 481 | 0 |
| `crmentityrel:Vendors->SPPayments` | duplicate=23 | 23 | 0 |
| `email_track:Emails` | archived=23 | 23 | 0 |
| `salesmanactivityrel:Users->Call` | linked=17 | 17 | 0 |
| `salesmanactivityrel:Users->Meeting` | linked=7 | 7 | 0 |
| `salesmanactivityrel:Users->Task` | linked=62 | 62 | 0 |
| `salesmanattachmentsrel:Users Image` | linked=1 | 1 | 0 |
| `seactivityrel:Accounts->Call` | linked=2 | 2 | 0 |
| `seactivityrel:Accounts->Meeting` | linked=3 | 3 | 0 |
| `seactivityrel:Accounts->Task` | linked=18 | 18 | 0 |
| `seactivityrel:Contacts->Email` | linked=1 | 1 | 0 |
| `seactivityrel:Invoice->Task` | linked=1 | 1 | 0 |
| `seactivityrel:Leads->Call` | linked=12 | 12 | 0 |
| `seactivityrel:Leads->Email` | linked=1 | 1 | 0 |
| `seactivityrel:Leads->Meeting` | linked=1 | 1 | 0 |
| `seactivityrel:Leads->Task` | linked=19 | 19 | 0 |
| `seactivityrel:Potentials->Email` | linked=27 | 27 | 0 |
| `seactivityrel:Potentials->Meeting` | linked=3 | 3 | 0 |
| `seactivityrel:Potentials->Task` | linked=21 | 21 | 0 |
| `seattachmentsrel:Contacts Image` | linked=1 | 1 | 0 |
| `seattachmentsrel:Documents Attachment` | linked=199 | 199 | 0 |
| `seattachmentsrel:Emails Attachment` | linked=1 | 1 | 0 |
| `seattachmentsrel:ModComments Attachment` | linked=2 | 2 | 0 |
| `senotesrel:Accounts->Documents` | linked=6 | 6 | 0 |
| `senotesrel:Act->Documents` | linked=42 | 42 | 0 |
| `senotesrel:Consignment->Documents` | linked=2 | 2 | 0 |
| `senotesrel:Contacts->Documents` | linked=3 | 3 | 0 |
| `senotesrel:Faq->Documents` | linked=3 | 3 | 0 |
| `senotesrel:HelpDesk->Documents` | linked=4 | 4 | 0 |
| `senotesrel:Invoice->Documents` | linked=72 | 72 | 0 |
| `senotesrel:Leads->Documents` | linked=5 | 5 | 0 |
| `senotesrel:Potentials->Documents` | linked=40 | 40 | 0 |
| `senotesrel:Project->Documents` | linked=6 | 6 | 0 |
| `senotesrel:ProjectTask->Documents` | linked=37 | 37 | 0 |
| `senotesrel:SPPayments->Documents` | linked=1 | 1 | 0 |
| `tags:Faq` | linked=29 | 29 | 0 |
| `tags:HelpDesk` | linked=2 | 2 | 0 |
| `tags:ProjectTask` | linked=2 | 2 | 0 |
| `user2role` | linked=7 | 7 | 0 |
| `users2group` | linked=4 | 4 | 0 |
| `crmentityrel:Contacts->PBXManager` | pending:07.2=1 | — | — |
| `crmentityrel:Contacts->SPCallPopup` | pending:07.2=1 | — | — |
| `crmentityrel:Leads->PBXManager` | pending:07.2=2 | — | — |
| `crmentityrel:Leads->SPCallPopup` | pending:07.2=2 | — | — |
| `crmentityrel:SPCallPopup->Contacts` | pending:07.2=1 | — | — |
| `crmentityrel:SPCallPopup->Leads` | pending:07.2=2 | — | — |

## Колонки таблиц связей

Строки таблиц связей в границах этапа: «пара» — колонки, из которых строится связь (строки сверены ниже), «ждёт этапа» — связи следующего этапа, «не переносится» — с причиной (D-144).

| Колонка | Судьба | Значений |
|---|---|---|
| `vtiger_cntactivityrel.activityid` | пара | 6 |
| `vtiger_cntactivityrel.contactid` | пара | 6 |
| `vtiger_contpotentialrel.contactid` | пара | 5 |
| `vtiger_contpotentialrel.potentialid` | пара | 5 |
| `vtiger_crmentityrel.crmid` | пара | 1936 |
| `vtiger_crmentityrel.module` | пара | 1936 |
| `vtiger_crmentityrel.relcrmid` | пара | 1936 |
| `vtiger_crmentityrel.relmodule` | пара | 1936 |
| `vtiger_email_track.access_count` | пара | 23 |
| `vtiger_email_track.click_count` | пара | 23 |
| `vtiger_email_track.crmid` | пара | 23 |
| `vtiger_email_track.mailid` | пара | 23 |
| `vtiger_freetagged_objects.module` | пара | 33 |
| `vtiger_freetagged_objects.object_id` | пара | 33 |
| `vtiger_freetagged_objects.tag_id` | пара | 33 |
| `vtiger_freetagged_objects.tagged_on` | не переносится: время постановки тега — у значения multiEnum его нет | 33 |
| `vtiger_freetagged_objects.tagger_id` | не переносится: автор постановки тега — у значения multiEnum его нет | 33 |
| `vtiger_freetags.id` | пара | 14 |
| `vtiger_freetags.owner` | не переносится: автор тега Vtiger | 14 |
| `vtiger_freetags.raw_tag` | пара | 14 |
| `vtiger_freetags.tag` | не переносится: нормализованная форма raw_tag (значение тега — raw_tag) | 14 |
| `vtiger_freetags.visibility` | не переносится: видимость тега Vtiger (теги EspoCRM — значения поля) | 14 |
| `vtiger_groups.description` | не переносится: группы воспроизводятся командами (D-39), описание не переносится | 3 |
| `vtiger_groups.groupid` | пара | 3 |
| `vtiger_groups.groupname` | пара | 3 |
| `vtiger_salesmanactivityrel.activityid` | пара | 86 |
| `vtiger_salesmanactivityrel.smid` | пара | 86 |
| `vtiger_salesmanattachmentsrel.attachmentsid` | пара | 1 |
| `vtiger_salesmanattachmentsrel.smid` | пара | 1 |
| `vtiger_seactivityrel.activityid` | пара | 109 |
| `vtiger_seactivityrel.crmid` | пара | 109 |
| `vtiger_seattachmentsrel.attachmentsid` | пара | 203 |
| `vtiger_seattachmentsrel.crmid` | пара | 203 |
| `vtiger_senotesrel.crmid` | пара | 221 |
| `vtiger_senotesrel.notesid` | пара | 221 |
| `vtiger_user2role.roleid` | пара | 7 |
| `vtiger_user2role.userid` | пара | 7 |
| `vtiger_users2group.groupid` | пара | 4 |
| `vtiger_users2group.userid` | пара | 4 |

## Таблицы связей источника

Строки таблиц связей по живым записям этапа (SQL) и строки, получившие исход планировщика — должны совпадать.

| Таблица | Строк в источнике | Учтено |
|---|---|---|
| `vtiger_cntactivityrel` | 6 | 6 |
| `vtiger_contpotentialrel` | 5 | 5 |
| `vtiger_crmentityrel` | 1936 | 1936 |
| `vtiger_email_track` | 23 | 23 |
| `vtiger_freetagged_objects` | 33 | 33 |
| `vtiger_salesmanactivityrel` | 86 | 86 |
| `vtiger_salesmanattachmentsrel` | 1 | 1 |
| `vtiger_seactivityrel` | 109 | 109 |
| `vtiger_seattachmentsrel` | 203 | 203 |
| `vtiger_senotesrel` | 221 | 221 |
| `vtiger_user2role` | 7 | 7 |
| `vtiger_users2group` | 4 | 4 |

## Цель вне источника

Записи EspoCRM с vtigerId: живые вне источника; вне диапазона реальных ключей (синтетика тестов, ключи ≥ 900 000 000); удалённые в EspoCRM — в диапазоне реальных ключей и вне его.

| Сущность | Живые с vtigerId вне источника | Вне диапазона ключей | Удалённые (реальные ключи) | Удалённые (вне диапазона) |
|---|---|---|---|---|
| Account | 0 | 0 | 0 | 57 |
| Act | 0 | 0 | 324 | 2 |
| ActItem | 0 | 0 | 375 | 0 |
| Attachment | 0 | 0 | 0 | 0 |
| Call | 0 | 0 | 0 | 0 |
| Case | 0 | 0 | 0 | 0 |
| Contact | 0 | 0 | 0 | 0 |
| ContactAccess | 0 | 0 | 0 | 0 |
| Document | 0 | 0 | 0 | 0 |
| DocumentFolder | 0 | 0 | 0 | 0 |
| Email | 0 | 0 | 0 | 0 |
| Invoice | 0 | 0 | 39 | 702 |
| InvoiceItem | 0 | 0 | 58 | 0 |
| KnowledgeBaseArticle | 0 | 0 | 0 | 0 |
| Lead | 0 | 0 | 0 | 53 |
| Meeting | 0 | 0 | 0 | 0 |
| Note | 0 | 0 | 0 | 0 |
| Opportunity | 0 | 0 | 0 | 0 |
| Payment | 0 | 0 | 66 | 0 |
| PaymentAllocation | 0 | 0 | 0 | 0 |
| Product | 0 | 0 | 0 | 0 |
| Project | 0 | 0 | 0 | 0 |
| ProjectTask | 0 | 0 | 0 | 0 |
| Quote | 0 | 0 | 157 | 6 |
| QuoteItem | 0 | 0 | 0 | 0 |
| SalesOrder | 0 | 0 | 0 | 0 |
| SalesOrderItem | 0 | 0 | 0 | 0 |
| Task | 0 | 0 | 0 | 0 |
| User | 0 | 0 | 0 | 0 |
| Vendor | 0 | 0 | 0 | 0 |
| VtigerArchive | 0 | 0 | 0 | 0 |

## Финансы: сверка итогов и налогов (этап 06.3)

Исходные итоги и строки — эталон (D-05): импорт их не пересчитывает. Каждый документ проверен чистым ядром (`SourceVerifier`, «Пересчёт ядра»): класс формулы, сравнение каждого итога с точным пересчётом по строкам, маржа строк. Каждое расхождение (округление, несовпадение, неподтверждённая формула, маржа, разные итоги связанных счёта и акта) — с причиной в приватном `discrepancies.jsonl`.

- Класс формулы: groupTaxAdded=2, lineTaxNotApplied=184, noLineTax=891, taxIncludedInPrice=1.
- Сверка итогов: exact=1078.
- Маржа строк: notComputed=265, ok=905.
- Причины расхождений: linked_invoice_act_totals_differ=5.
- Распределение платежей (D-11, категория:решение): both_same_invoice:allocate=426, conflict_rel_other_invoice:allocate=38, rel_only:allocate=4, rel_only:none=52, related_to_invoice_only:allocate=152, related_to_salesorder:allocate=7, unallocated:none=120.
- Пометки источника (`itvolga-finance-verify`): Act: noLineTax / exact (unchanged)=404, Invoice: groupTaxAdded / exact (unchanged)=2, Invoice: lineTaxNotApplied / exact (unchanged)=148, Invoice: noLineTax / exact (unchanged)=485, Invoice: taxIncludedInPrice / exact (unchanged)=1, Quote: lineTaxNotApplied / exact (unchanged)=23, Quote: noLineTax / exact (unchanged)=1, SalesOrder: lineTaxNotApplied / exact (unchanged)=13, SalesOrder: noLineTax / exact (unchanged)=1.
- Оплата документов (`itvolga-finance-settle --silent`): Invoice unchanged=636, SalesOrder unchanged=14; расхождение после пересчёта: 0.
- Счётчики номеров (cur_id источника, только вверх): изменений 0, ниже источника: 0.

## Агрегаты (точные суммы decimal)

Одни и те же меры тремя способами: SQL восстановленного источника, значения плана, SQL стенда. «Чтение» — SQL источника = план по всем записям; «запись» — план = SQL стенда по импортированным записям (без удалённых и пересчитанных в EspoCRM — ответы владельца). Суммы — только в приватном `aggregates.json`.

| Сравнение | Мер | Не равно |
|---|---|---|
| чтение | 69 | 0 |
| запись | 69 | 0 |

Исключено из сравнения записи: нет.

## Файлы

Каждый файл: байты из проверенного снимка (размер и sha256 по запечатанной описи), запись в хранилище стенда, проверочный проход (файл есть, sha256 совпадает) и скачивание через стенд администратором (200 и sha256 источника). Внешние ссылки документов не открываются — переносятся дословно. Каждый недоступный файл — с причиной в приватном `files.jsonl`.

| Владелец | Итоги |
|---|---|
| Contact | ok=1 |
| Document | ok=199 |
| Email | ok=1 |
| LegalEntity | ok=1 |
| Note | ok=2 |
| User | ok=1 |
| source | accepted=8 |

- Сохранено и скачано: 205; принятые потери D-23 (имя файла без файла в источнике): 8; не найдено в снимке: 0.
- Оставлены в снимке по решениям: mailmanager_attachments=34.

## Счётчики преобразований

`allocation:both_same_invoice:allocate` 426, `allocation:conflict_rel_other_invoice:allocate` 38, `allocation:rel_only:allocate` 4, `allocation:rel_only:none` 52, `allocation:related_to_invoice_only:allocate` 152, `allocation:related_to_salesorder:allocate` 7, `allocation:unallocated:none` 120, `archive_link:Assets.account:linked` 3, `archive_link:Assets.product:linked` 3, `archive_link:Consignment.account:linked` 1, `archive_link:Consignment.invoice:linked` 1, `archive_link:JVmes.parentArchive:linked` 267, `archive_link:Jivosite.lead:kept` 12, `archive_link:Jivosite.lead:linked` 37, `archive_link:ServiceContracts.account:linked` 1, `external_url_invalid` 1, `phone_duplicate_in_record` 12, `phone_local` 124, `phone_multi` 7, `phone_other` 6, `phone_plus` 12, `phone_ru10` 117, `phone_ru11` 475, `phone_short` 23, `phone_type_conflict` 23
