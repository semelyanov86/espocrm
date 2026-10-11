# Импорт базовых сущностей — сводка прогона (этап 06.2)

Генерируется: `task import:summary -- <прогон>` (`scripts/import/importer.py summary`). Только счётчики: ни значений, ни идентификаторов записей. Машинный отчёт с причинами по каждой записи и колонке — вне Git (`/data/itvolga/espo-private/import/<прогон>/`). Контракт импорта — `import.md`.

- Прогон: `20261011T133152`; снимок: `20261006T201216`; код: `8af73eb` (незакоммиченных файлов инструмента: 4).
- Итог: **findings**; проблемы: нет; находки: conflict=8, dangling=1, missing_in_source=0, no_target=14, pending=931, records_held=3, type_conflict=22.
- «Тишина» (изменение числа строк стенда: уведомления, напоминания, подписки, записи ленты без vtigerId, письма, вебхуки, журнал действий): action_history_record=0, email=0, note_not_imported=0, notification=0, reminder=0, stream_subscription=0, webhook_queue_item=0.

## Записи

| Сущность | Источник | Запись | Проверка | Удержаны | Возвращено после хуков |
|---|---|---|---|---|---|
| Account | 180 | unchanged=180 | equal=180 | — | — |
| Call | 17 | unchanged=17 | equal=17 | — | — |
| Case | 45 | unchanged=45 | equal=45 | — | — |
| Contact | 341 | unchanged=341 | equal=341 | — | — |
| ContactAccess | 341 | skipped=214, unchanged=127 | absent=214, equal=127 | — | — |
| Lead | 225 | unchanged=225 | equal=225 | — | — |
| Meeting | 7 | unchanged=7 | equal=7 | — | — |
| Note | 78 | unchanged=75 | equal=75 | 06.3=3 | — |
| Opportunity | 156 | unchanged=156 | equal=156 | — | — |
| Project | 54 | unchanged=54 | equal=54 | — | — |
| ProjectTask | 493 | unchanged=493 | equal=493 | — | — |
| Task | 62 | unchanged=62 | equal=62 | — | — |
| User | 7 | unchanged=7 | equal=7 | — | — |

## Колонки источника по модулям

Все колонки всех прочитанных таблиц по живым записям модуля. «Правило» — колонка переносится правилом спецификации; для них значения сверены проверочным проходом (несверенный остаток — нули «0 = пусто», ожидание следующего этапа, удержанные записи). «Исключено»/«пусто» — судьба из `field-map.csv`, значения не переносятся. «Значений» — непустых по выражению аудита (`nonempty_expr`: ноль и «нет» — тоже значения); значимых (ненулевых, «да») в колонках «пусто по карте» нет — иначе прогон дал бы находку «карта устарела».

| Модуль | Колонок с правилом | Значений | Сверено | Расхождений | Неучтённых | Ключи | Исключено (колонок/значений) | Пусто по карте (колонок/значений) | Без строки карты (колонок/значений) |
|---|---|---|---|---|---|---|---|---|---|
| Accounts | 40 | 4190 | 4053 | 0 | 0 | 6 | 7/1080 | 12/720 | 0/0 |
| Calendar | 13 | 398 | 398 | 0 | 0 | 3 | 14/374 | 8/34 | 5/0 |
| Contacts | 46 | 8540 | 8427 | 0 | 0 | 7 | 11/3410 | 17/1023 | 0/0 |
| Events | 16 | 723 | 723 | 0 | 0 | 3 | 11/520 | 11/208 | 2/0 |
| HelpDesk | 18 | 743 | 631 | 0 | 0 | 4 | 7/270 | 8/45 | 0/0 |
| Leads | 33 | 4413 | 3763 | 0 | 0 | 6 | 11/2250 | 26/450 | 0/0 |
| ModComments | 10 | 779 | 600 | 0 | 0 | 4 | 6/468 | 11/234 | 1/0 |
| Potentials | 20 | 2691 | 2572 | 0 | 0 | 3 | 11/1560 | 16/312 | 0/0 |
| Project | 20 | 946 | 928 | 0 | 0 | 3 | 6/270 | 5/54 | 0/0 |
| ProjectTask | 19 | 8895 | 8895 | 0 | 0 | 4 | 6/2465 | 5/493 | 0/0 |
| Users | 21 | 121 | 113 | 0 | 0 | 2 | 37/207 | 32/0 | 0/0 |

## Исходы значений

| Модуль | Исходы |
|---|---|
| Accounts | archived=189, carried=3101, duplicate=6, linked=540, mapped=147, normalized=69, type_conflict=1, zero_empty=137 |
| Calendar | carried=292, linked=102, mapped=4 |
| Contacts | archived=684, carried=5760, duplicate=5, linked=1257, mapped=42, no_target=14, normalized=152, pending:06.3=6, protected=493, type_conflict=20, zero_empty=107 |
| Events | archived=7, carried=404, derived_equal=100, linked=156, mapped=56 |
| HelpDesk | archived=64, carried=353, linked=184, mapped=30, zero_empty=112 |
| Leads | archived=30, carried=2598, duplicate=1, linked=675, mapped=288, normalized=170, type_conflict=1, zero_empty=650 |
| ModComments | archived=79, carried=234, dangling:not_a_user=1, linked=308, pending:06.3=80, zero_empty=77 |
| Potentials | archived=469, carried=1345, linked=661, mapped=97, zero_empty=119 |
| Project | archived=55, carried=572, linked=251, normalized=50, zero_empty=18 |
| ProjectTask | carried=6923, linked=1972 |
| Users | archived=1, carried=60, mapped=49, normalized=3, not_applicable:D-37=7, pending:06.3=1 |

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
| `crmentityrel:Accounts->Potentials` | duplicate=63 | 63 | 0 |
| `crmentityrel:Accounts->Project` | duplicate=3 | 3 | 0 |
| `crmentityrel:Contacts->Calendar` | duplicate=2, linked=1 | 3 | 0 |
| `crmentityrel:Contacts->HelpDesk` | linked=3 | 3 | 0 |
| `crmentityrel:Invoice->Calendar` | pending:06.3=1 | 0 | 0 |
| `crmentityrel:Leads->Calendar` | conflict=3, duplicate=32, linked=3 | 35 | 0 |
| `crmentityrel:Potentials->Calendar` | duplicate=24 | 24 | 0 |
| `crmentityrel:Project->ProjectTask` | conflict=5, duplicate=481 | 481 | 0 |
| `salesmanactivityrel:Users->Call` | linked=17 | 17 | 0 |
| `salesmanactivityrel:Users->Meeting` | linked=7 | 7 | 0 |
| `salesmanactivityrel:Users->Task` | linked=62 | 62 | 0 |
| `seactivityrel:Accounts->Call` | linked=2 | 2 | 0 |
| `seactivityrel:Accounts->Meeting` | linked=3 | 3 | 0 |
| `seactivityrel:Accounts->Task` | linked=18 | 18 | 0 |
| `seactivityrel:Invoice->Task` | pending:06.3=1 | 0 | 0 |
| `seactivityrel:Leads->Call` | linked=12 | 12 | 0 |
| `seactivityrel:Leads->Meeting` | linked=1 | 1 | 0 |
| `seactivityrel:Leads->Task` | linked=19 | 19 | 0 |
| `seactivityrel:Potentials->Meeting` | linked=3 | 3 | 0 |
| `seactivityrel:Potentials->Task` | linked=21 | 21 | 0 |
| `tags:HelpDesk` | linked=2 | 2 | 0 |
| `tags:ProjectTask` | linked=2 | 2 | 0 |
| `user2role` | linked=7 | 7 | 0 |
| `users2group` | linked=4 | 4 | 0 |
| `crmentityrel:Accounts->Invoice` | pending:06.3=443 | — | — |
| `crmentityrel:Accounts->SPPayments` | pending:06.3=180 | — | — |
| `crmentityrel:Contacts->Emails` | pending:06.3=1 | — | — |
| `crmentityrel:Contacts->Invoice` | pending:06.3=2 | — | — |
| `crmentityrel:Contacts->Jivosite` | pending:06.3=1 | — | — |
| `crmentityrel:Contacts->PBXManager` | pending:07.2=1 | — | — |
| `crmentityrel:Contacts->SPCallPopup` | pending:07.2=1 | — | — |
| `crmentityrel:Contacts->SPPayments` | pending:06.3=5 | — | — |
| `crmentityrel:Leads->Emails` | pending:06.3=1 | — | — |
| `crmentityrel:Leads->Jivosite` | pending:06.3=37 | — | — |
| `crmentityrel:Leads->PBXManager` | pending:07.2=2 | — | — |
| `crmentityrel:Leads->SPCallPopup` | pending:07.2=2 | — | — |
| `crmentityrel:Potentials->Emails` | pending:06.3=23 | — | — |
| `crmentityrel:Potentials->Invoice` | pending:06.3=20 | — | — |
| `crmentityrel:Potentials->Quotes` | pending:06.3=1 | — | — |
| `crmentityrel:Potentials->Services` | pending:06.3=3 | — | — |
| `crmentityrel:SPCallPopup->Contacts` | pending:07.2=1 | — | — |
| `crmentityrel:SPCallPopup->Leads` | pending:07.2=2 | — | — |
| `vtiger_seattachmentsrel:Contacts->attachment` | pending:06.3=1 | — | — |
| `vtiger_seattachmentsrel:ModComments->attachment` | pending:06.3=2 | — | — |
| `vtiger_senotesrel:Accounts->Documents` | pending:06.3=6 | — | — |
| `vtiger_senotesrel:Contacts->Documents` | pending:06.3=3 | — | — |
| `vtiger_senotesrel:HelpDesk->Documents` | pending:06.3=4 | — | — |
| `vtiger_senotesrel:Leads->Documents` | pending:06.3=5 | — | — |
| `vtiger_senotesrel:Potentials->Documents` | pending:06.3=40 | — | — |
| `vtiger_senotesrel:Project->Documents` | pending:06.3=6 | — | — |
| `vtiger_senotesrel:ProjectTask->Documents` | pending:06.3=49 | — | — |

## Таблицы связей источника

Строки таблиц связей по живым записям этапа (SQL) и строки, получившие исход планировщика — должны совпадать.

| Таблица | Строк в источнике | Учтено |
|---|---|---|
| `vtiger_cntactivityrel` | 6 | 6 |
| `vtiger_contpotentialrel` | 5 | 5 |
| `vtiger_crmentityrel` | 1392 | 1392 |
| `vtiger_freetagged_objects` | 4 | 4 |
| `vtiger_salesmanactivityrel` | 86 | 86 |
| `vtiger_seactivityrel` | 80 | 80 |
| `vtiger_seattachmentsrel` | 3 | 3 |
| `vtiger_senotesrel` | 113 | 113 |
| `vtiger_user2role` | 7 | 7 |
| `vtiger_users2group` | 4 | 4 |

## Цель вне источника

| Сущность | Живые с vtigerId вне источника | Вне диапазона ключей | Удалённые с vtigerId |
|---|---|---|---|
| Account | 0 | 0 | 55 |
| Call | 0 | 0 | 0 |
| Case | 0 | 0 | 0 |
| Contact | 0 | 0 | 0 |
| ContactAccess | 0 | 0 | 0 |
| Lead | 0 | 0 | 51 |
| Meeting | 0 | 0 | 0 |
| Note | 0 | 0 | 0 |
| Opportunity | 0 | 0 | 0 |
| Project | 0 | 0 | 0 |
| ProjectTask | 0 | 0 | 0 |
| Task | 0 | 0 | 0 |
| User | 0 | 0 | 0 |

## Счётчики преобразований

`phone_duplicate_in_record` 12, `phone_local` 124, `phone_multi` 7, `phone_other` 6, `phone_plus` 12, `phone_ru10` 117, `phone_ru11` 474, `phone_short` 23, `phone_type_conflict` 22
