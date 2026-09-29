# Инвентаризация источника (Vtiger 7.1, serv.itvolga.com)

- **Срез:** 2026-09-29, 18:35–20:00 CEST (время сервера `+02:00`). Повторный полный прогон `scripts/audit/run-audit.sh` в 20:00 дал идентичные `field-map.csv` и `relations.csv`.
- **Метод:** только чтение — `SELECT` в сессиях `SET SESSION TRANSACTION READ ONLY`, `ls/stat/find/wc`, `asterisk -rx "... show ..."`. Значения строк не выгружались; наружу выходили только счётчики, схемы и значения справочников. Подробности и запросы — `evidence.md`.
- **Обозначения:** «живые» — `vtiger_crmentity.deleted=0`; «удалённые» — в корзине (`deleted=1`); «непустые» — `NOT NULL` и не пустая строка, для чисел — не ноль, для чекбоксов — значение `1`.

## 1. Платформа

| Компонент | Факт (проверено) | Прежняя гипотеза (README/CLAUDE/роли `/data/server`) |
|---|---|---|
| ОС | Ubuntu 26.04 LTS, ядро 7.0 | совпадает |
| CRM | Vtiger `7.1.0-201803`, patch `20180305`, **SalesPlatform 7.1.0 Service Pack 01** (`spServicePackVersion.txt`) | «Vtiger CRM 7.1» — без упоминания SalesPlatform |
| Каталог | `/var/www/serv_itvolga/vtiger7`, владелец `www-data` | совпадает |
| PHP | 7.4.33 в Docker-контейнере `php74-fpm` (образ `php-docker-local:7.4`), модули ionCube Loader, imap, mysqli, gd, zip, curl, intl, soap, mbstring | совпадает |
| БД | MySQL 8.4.11, база `vtiger7`: 784 таблицы, **534 непустые**, ~42.6 МБ | совпадает |
| Веб | Apache vhost `serv.itvolga.com` → fcgi `127.0.0.1:9074`, HTTP Basic Auth (1 общая учётная запись в htpasswd) | совпадает |
| PHP хоста (для EspoCRM, проверено 2026-09-29, этап 02) | нативный `php8.5-fpm` / `php8.5-cli` **8.5.4** (Ubuntu), пул `www` от `www-data`; расширения, нужные EspoCRM 10, есть все (`pdo_mysql gd zip mbstring curl xml exif bcmath intl pcntl posix`); значения FPM `php.ini` ниже рекомендаций EspoCRM: `memory_limit 128M`, `upload_max_filesize 2M`, `post_max_size 8M`, `max_execution_time 30`, `date.timezone UTC` | в прежних документах не упоминался |
| Apache (проверено 2026-09-29, этап 02) | 2.4.66, `mpm_event`, модули `proxy_fcgi rewrite headers ssl auth_basic`; сайтов в `sites-enabled` — 17 | — |
| Параметры MySQL (проверено 2026-09-29, этап 02) | глобальный `sql_mode=ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION` (не strict), `utf8mb4`/`utf8mb4_0900_ai_ci`, `time_zone=SYSTEM` (CEST), `bind_address=127.0.0.1`, `max_allowed_packet=64M`, `innodb_buffer_pool_size=128M`, `lower_case_table_names=0`; хост: 6 CPU, 18 ГБ ОЗУ, 744 ГБ свободно | — |
| Cron | `/etc/cron.d/vtiger`: `*/5` от `www-data` через `flock` + `sudo` враппер → `docker exec` в `php74-fpm` | совпадает |
| Язык/валюта/время | `ru_ru`, `Russia, Rubles`; в `config.inc.php` дважды задан `$default_timezone` (`Europe/Moscow`, затем некорректное `UTC+3`, которое PHP игнорирует). Фактический пояс записи дат: Europe/Moscow до 2022-10, Europe/Berlin с 2022-11 до 2026-06-12, UTC с 2026-06-13 (проверено по времени файлов и логу входа, D-30) | не документировано |
| Asterisk | 22.5.2 (apt), `chan_pjsip`, CDR: `cdr_adaptive_odbc` (MySQL `asteriskcdrdb.cdr`) + `cdr_csv` | совпадает с README роли `asterisk` |
| Backup | restic-тиры `db` (ночные `mysqldump` в `/var/backups/mysql`, есть `vtiger7.sql` и `asteriskcdrdb.sql`), `system` (`/etc`, `/var/www`, …) | **`/var/spool/asterisk/monitor` и `/var/log/asterisk/cdr-csv` в бэкап не входят**; глобальное исключение `**/vendor` исключает и `vtiger7/vendor` (восстановим по `composer.lock`) |

Каталоги приложения: `storage/` 247 файлов / 104 МБ, `test/` 1463 файла / 16 МБ (логотипы, `templates_c`, mosaico, маркеры лицензий `*.vte`), `vendor/` 1162 файла / 7.3 МБ, `cache/` 8.5 МБ, `logs/` 3.6 МБ.

## 2. Модули с данными

Все модули, где есть хоть одна запись (живая или удалённая). `presence=1` — модуль скрыт/выключен в Vtiger, но данные есть.

| Модуль | presence | живых | удалённых | полей | кастомных | полей с данными | первая запись | последняя запись | посл. изменение |
|---|---|---|---|---|---|---|---|---|---|
| PBXManager | 0 | 1116 | 0 | 30 | 0 | 20 | 2019-11-18 | 2024-07-30 | 2024-07-31 |
| SPPayments | 0 | 798 | 192 | 30 | 5 | 25 | 2015-10-20 | 2026-09-27 | 2026-09-27 |
| Invoice | 0 | 635 | 2 | 64 | 1 | 47 | 2016-01-27 | 2026-08-31 | 2026-09-27 |
| ProjectTask | 0 | 493 | 0 | 22 | 3 | 20 | 2019-03-16 | 2023-06-05 | 2023-06-07 |
| Act | 0 | 403 | 1 | 54 | 0 | 38 | 2018-07-16 | 2026-08-31 | 2026-08-31 |
| Contacts | 0 | 341 | 4 | 61 | 8 | 46 | 2015-12-14 | 2024-10-23 | 2024-10-23 |
| VTEItems | 1 | 286 | 0 | 19 | 0 | 8 | 2018-11-02 | 2018-11-02 | 2018-11-02 |
| JVmes | 1 | 267 | 5 | 11 | 0 | 9 | 2018-08-09 | 2019-03-28 | 2019-03-28 |
| Leads | 0 | 225 | 16 | 40 | 2 | 33 | 2015-10-13 | 2021-04-06 | 2022-11-14 |
| Documents | 0 | 215 | 12 | 20 | 1 | 18 | 2018-09-24 | 2026-08-26 | 2026-08-26 |
| SPCallPopup | 0 | 210 | 0 | 16 | 0 | 12 | 2020-12-01 | 2024-07-31 | 2024-07-31 |
| Accounts | 0 | 180 | 2 | 52 | 4 | 41 | 2015-12-14 | 2025-05-06 | 2026-08-31 |
| Potentials | 0 | 156 | 0 | 24 | 0 | 21 | 2015-12-04 | 2025-05-06 | 2025-11-30 |
| Calendar (Task+Events) | 0 | 86 | 100 | 30 (+33 Events) | 0 | 20 | 2018-09-14 | 2024-10-23 | 2024-10-23 |
| ModComments | 0 | 78 | 0 | 19 | 3 | 12 | 2018-09-23 | 2023-06-07 | 2023-06-07 |
| Faq | 0 | 63 | 0 | 14 | 0 | 12 | 2018-09-23 | 2023-04-13 | 2023-04-13 |
| Project | 0 | 54 | 0 | 23 | 1 | 21 | 2016-01-14 | 2023-06-01 | 2023-06-05 |
| Jivosite | 1 | 49 | 3 | 13 | 0 | 9 | 2018-08-09 | 2019-03-28 | 2019-03-28 |
| HelpDesk | 0 | 45 | 14 | 24 | 0 | 19 | 2015-10-20 | 2023-09-26 | 2023-09-26 |
| Emails | 0 | 29 | 151 | 22 | 0 | 17 | 2018-09-18 | 2019-10-03 | 2019-10-03 |
| Services | 0 | 25 | 0 | 29 | 1 | 21 | 2015-10-13 | 2024-04-28 | 2024-04-28 |
| Quotes | 0 | 24 | 0 | 58 | 1 | 38 | 2016-01-27 | 2018-10-07 | 2018-10-07 |
| SalesOrder | 0 | 14 | 0 | 70 | 1 | 45 | 2016-01-27 | 2023-06-14 | 2023-06-15 |
| Products | 1 | 3 | 0 | 42 | 0 | 13 | 2019-12-04 | 2019-12-04 | 2024-05-01 |
| Vendors | 0 | 3 | 0 | 23 | 1 | 12 | 2018-07-13 | 2018-09-29 | 2020-04-18 |
| Assets | 0 | 3 | 0 | 23 | 0 | 16 | 2023-06-19 | 2023-06-19 | 2023-06-19 |
| ServiceContracts | 0 | 1 | 0 | 24 | 0 | 17 | 2023-04-14 | 2023-04-14 | 2023-04-14 |
| Consignment | 0 | 1 | 0 | 57 | 0 | 36 | 2019-12-07 | 2019-12-07 | 2020-03-07 |
| Notifications | 1 | 1 | 0 | 10 | 0 | 7 | 2018-10-22 | 2018-10-22 | 2018-10-22 |
| Users | 0 | 7 пользователей | — | 76 | 0 | 52 | — | — | — |

«Полей» — строк `vtiger_field` модуля (включая общие из `vtiger_crmentity` и поля строк документов); «с данными» — хотя бы одно непустое значение в живых записях.

**Calendar** хранит и задачи, и события (`vtiger_activity.activitytype`): живые — Task 34, Call 17, Meeting 7, кастомный тип «Письмо» 28; удалённые — Meeting 100 (все удалены 2018-07-13 за 4 минуты). **Emails** — отдельный `setype`: 29 живых, 151 удалённое.

Вложения (`setype` вида `* Attachment`/`* Image`, не модули): Documents Attachment 199, MailManager Attachment 34 живых + 334 удалённых, ModComments Attachment 2, Emails Attachment 1, Contacts Image 1, Users Image 1.

**Активно используются сейчас (записи в 2026 г.):** Invoice, Act, SPPayments, Documents, Accounts (изменения). Остальное — история: звонки в PBXManager до 2024-07, заявки до 2023-09, проекты до 2023-06, Jivosite до 2019-03.

### Модули без данных

Dashboard, Home, Events (отдельно, данные в Calendar), PriceBooks, PurchaseOrder, Rss, Reports (записей-сущностей нет; определения отчётов — в `vtiger_report`), Campaigns, Portal, Webmails, SPPDFTemplates (шаблоны — в `sp_templates`), Import, MailManager, Mobile, WSAPP, ModTracker (история — в `vtiger_modtracker_*`), SPCMLConnector, Search, SPTips, SPDynamicBlocks, SPKladr, SPUnits, RecycleBin, Google, CustomerPortal, EmailTemplates (шаблоны — в `vtiger_emailtemplates`), ProjectMilestone, SMSNotifier, SPSocialConnector, SPVoipIntegration, Webforms, ExtensionStore, VTEStore, DragDropDocuments, QuotingTool, SignedRecord, ListviewColors, VTEPopupReminder, KanbanView, HideFields, AdvancedCustomFields, ControlLayoutFields, RelatedBlocksLists, CustomFormsViews, SummaryReport, ModuleLinkCreator, UserLogin, MaskedInput, CalendarPopup, VTEQuickEdit, VTEHistoryLog, RealTimeFieldFormulas, VTEComments, CalendarHorizontal, VTEReports, DuplicateCheckMerge, VTEWidgets, TimeTracker, VTEAdvanceMenu, GoogleAddress, RoomsMessages, RoomsUsers, Rooms, VTEProgressbar, DynamicBlocks, FieldAutofill, AutomatedBackup, Team, VTEConditionalAlerts, Quoter, VTEButtons, VTECustomHeader, VTEMailConverter, CurrencyWidget, ITS4YouReports, VTEEmailMarketing. Их конфигурационные таблицы классифицированы в `field-map.csv` (категории «настройки расширений», «метаданные»).

## 3. Кастомные поля

Все поля с `generatedtype=2` и колонки `cf_*` (подробно — `field-map.csv`, колонка `custom`). Непустых значений — среди живых записей.

| Модуль | Колонка | Метка | Тип | Непустых |
|---|---|---|---|---|
| Contacts | `cf_1322` | Anydesc ID | text 20 | 122 — **поле доступа** |
| Contacts | `cf_1324` | Anydesc Password | text 20 | 121 — **поле доступа (пароль)** |
| Contacts | `cf_1326` | Hostname | text 190 | 125 — **поле доступа** |
| Contacts | `cf_1328` | IP | text 50 | 125 — **поле доступа** |
| Contacts | `cf_1372`…`cf_1378` | подписки/оригиналы документов (4 чекбокса) | checkbox | 1, 0, 1, 0 |
| Accounts | `cf_1109`/`cf_1111`/`cf_1113`/`cf_1115` | Расчётный счёт / Банк / Корр. счёт / БИК | text | 156 / 78 / 154 / 155 |
| Leads | `cf_1107` | Приоритет | picklist | 187 |
| Leads | `cf_1165` | Jivosite ID | int | 52 |
| Vendors | `cf_1206` | ИНН | text 15 | 2 |
| SPPayments | `cf_1198`/`cf_1200`/`cf_1202`/`cf_1204` | Счёт / БИК / Банк контрагента / № банковской транзакции | text | 602 / 190 / 208 / 188 |
| SPPayments | `cf_1380` | Валютный счёт | checkbox | 1 |
| ProjectTask | `cf_1354` | Show In Stat | checkbox | 30 |
| ProjectTask | `cf_1320` | Git Commit | url | 257 |
| Services | `cf_billable_time_tracker` | Billable Time (TimeTracker) | checkbox | 23 |
| Events | `invoiceid`, `salesorder_id`, `timesheet_id`, `duration_seconds` | кастомные ссылки | uitype 10 / text | 0 |
| ModComments | `cf_comment_picklist`, `cf_comment_picklist_two` | — | picklist | 0 |
| Documents | `cf_for_field` | — | text | 1 |
| Quotes/SalesOrder/Invoice/PurchaseOrder | `tax` (`presence=1`) | скрытое служебное | text | Invoice 2 |

SalesPlatform-поля с `generatedtype=1`, но нестандартные для Vtiger: `Accounts.inn` (90), `Accounts.kpp` (76), `*.vk_url`, `spcompany` во всех финансовых модулях и в Potentials, `Invoice.sp_act_id` (391), `Invoice.potential_id` (428), `Contacts.support_start_date`/`support_end_date` (205/205).

Физических колонок `cf_*` без описания в `vtiger_field` с данными нет (есть только колонки таблиц-справочников и пустые `vtiger_crmentity.cf_view*`).

## 4. Статусы и справочники (живые записи)

Полные распределения — в приватном `14_picklist_values.tsv`; ниже — ключевые. Пустое значение обозначено `∅`.

- **Invoice.invoicestatus:** Paid 561, Created 33, Cancel 17, Sent 9, Credit Invoice 6, Approved 5, ∅ 4.
- **Act.sp_actstatus:** Created 290, Sent 55, Received 39, Done 5, ∅ 14.
- **SPPayments:** `pay_type` Приход 735 / Expense 63; `spstatus` Executed 776, Запланирован 3, Canceled 1, ∅ 18; `type_payment` Cashless Transfer 622, Наличные 174, ∅ 2.
- **Quotes.quotestage:** Принято 11, Доставка 8, Создано 3, Delivered 1, Просмотрено 1. **SalesOrder.sostatus:** Одобрено 9, Создано 4, Created 1.
- **spcompany:** Invoice — Default 547 / По умолчанию 88; Act — 401/2; Quotes — 22/2; SalesOrder — 13/1; Potentials — 124/29/∅ 3; SPPayments — 473/137/∅ 188; Consignment — Default 1. Справочник `vtiger_spcompany` содержит ровно эти два значения.
- **hdnTaxType:** Invoice individual 601, group_tax_inc 32, group 2; Act individual 382, group_tax_inc 21; Quotes individual 24; SalesOrder individual 13, group_tax_inc 1.
- **Potentials.sales_stage:** Closed Won 54, Qualification 28, Переговоры 22, Perception Analysis 19, Value Proposition 16, Negotiation or Review 7, Proposal or Price Quote 6, Needs Analysis 2, Closed Lost 1, Id. Decision Makers 1.
- **Leads.leadstatus:** ∅ 145, Есть Контакт 24, Горячий 13, Попытка связаться 13, Теплый 12, Предв. классифицирован 6, Холодный 6, Qualified 2, Контакт в будущем 2, Ненужное Обращение 1, Утерянное Обращение 1. `leadsource`: Холодный звонок 50, Веб-сайт 57, Jivosite 28, ∅ 62, прочие ≤ 8.
- **HelpDesk.ticketstatus:** Closed 30, Open 11, In Progress 2, Wait For Response 2; `ticketpriorities` Normal 23, Высокий 13, Low 9.
- **ProjectTask.projecttaskstatus:** Completed 460, In Progress 16, Open 11, Deferred 5, ∅ 1. **Project.projectstatus:** completed 35, Выполняется 6, Обсуждение 3, Внедрен 2, waiting for feedback 2, Ознакомление 1, on hold 1, ∅ 4.
- **Calendar:** задачи `taskstatus` Completed 31, In Progress 2, Not Started 1; события `eventstatus` Held 50, Planned 2.
- **Faq.faqstatus:** Published 51, Reviewed 12. **Documents:** `filelocationtype` I 202 / E 13; все в одной папке «По умолчанию».
- **PBXManager.callstatus/direction:** outbound completed 543, busy 127, no-answer 90, прочие; inbound completed 217, no-answer 59, прочие (подробно — `telephony-sources.md`).

Значения справочников смешаны: часть хранится на английском (`Paid`, `Closed Won`) и отображается переводом, часть добавлена на русском. Стандартизация — `open-questions.md` Q-11.

## 5. Пользователи, владельцы, ACL

- **Пользователи:** 7, все `Active`; администраторы — `user#1` (`is_admin='on'`) и `user#8` (`is_admin='1'` — другой формат значения). Роли: Директор (`user#1`, `user#10`), Заместитель директора (`user#6`, `user#7`, `user#8`), Менеджер по продажам (`user#5`), Менеджер клиентов (`user#9`). Внутренние номера телефонии (`phone_crm_extension`) заданы у 5 пользователей; `vtiger_asteriskextensions` пуста.
- **Роли:** иерархия Организация → Директор → Заместитель директора → {Менеджер клиентов, Кассир-бухгалтер, Механик, Менеджер по продажам, Водитель–экспедитор, Водитель–бригадир, Сотрудники склада, Лаборант}. Роли без пользователей — 7.
- **Профили (используемые):** «Администратор» (роль Директор) — всё; «Заместитель директора+Профиль» — скрыты Invoice, Act, SPPayments, Quotes, SalesOrder, Potentials, Leads, Vendors, Assets, Consignment, ServiceContracts; «Менеджер по Продажам+Профиль» — скрыты Accounts, Contacts, Documents, HelpDesk, Project/ProjectTask и все финансовые; «Менеджер клиентов+Профиль» — скрыты Accounts, Contacts, Emails, Leads, PBXManager, финансовые. Полевые ограничения — только read-only системных полей.
- **Общий доступ (`vtiger_def_org_share`):** Private — Accounts, Contacts, Potentials, Calendar/Events, Documents, Emails, HelpDesk, Invoice, Quotes, SalesOrder, Project, ProjectTask, PBXManager, SPCallPopup, Jivosite, JVmes; Public (чтение/правка/удаление) — Leads, Act, SPPayments, ModComments, Services, Vendors, Products, ServiceContracts, Assets, Consignment, VTEItems. Faq в `vtiger_def_org_share` отсутствует (поведение Vtiger по умолчанию не проверялось). Правило шаринга: 1 (`role2role` H3→H3, модуль Contacts). Группы: «Отдел Поддержки» (3 пользователя), «Отдел Маркетинга» (1), «Отдел Продаж» (0).
- **Поля доступа контактов** видимы и редактируемы во всех 11 профилях (`profile2field.visible=0`, `readonly=0`); фактически их видят пользователи, которым доступен модуль Contacts (Директор, Заместители). Отдельной защиты нет.
- **Владельцы:** почти все записи принадлежат `user#1`; исключения — Contacts (`user#6` 68, `user#8` 58), PBXManager (`user#6` 133, `user#7` 12, `user#8` 149), Documents (`user#9` 31), ProjectTask (`user#9` 65 и др.), ModComments (`user#8` 11, `user#9` 2); группа «Отдел Поддержки» владеет 1 Account, 1 Contact, 1 Potential, 1 Project, 3 ProjectTask. Висячих владельцев нет. Автор (`smcreatorid`) почти везде `user#1` (перенос данных при обновлении 2018 г.).

## 6. Связи

Полный перечень с распределениями и кардинальностями — `relations.csv` (287 строк). Ключевое:

- Поля-ссылки (uitype 10/51/57/73/76/80…) по каждому модулю, включая висячие и ссылки на удалённые записи (PBXManager.customer → 23 удалённых Contacts).
- `vtiger_crmentityrel` — 2677 строк; многие пары дублируют поля-ссылки (Accounts→Invoice 442, Accounts→SPPayments 180, Project→ProjectTask 486), часть — самостоятельные M:N (Potentials→Services 3, Project→HelpDesk 1).
- Активности: `vtiger_seactivityrel` 260 (1 родитель на активность), `vtiger_cntactivityrel` 6, `vtiger_salesmanactivityrel` 186 (приглашённые пользователи).
- Документы: `vtiger_senotesrel` 233 (M:N; до 15 документов на задачу проекта), `vtiger_seattachmentsrel` 203.
- Строки документов `vtiger_inventoryproductrel`: Invoice 711 (до 6 на счёт), Act 416 (до 2), Quotes 27, SalesOrder 14, Consignment 3; позиции ссылаются на Services (и 3 раза на Products).
- **Invoice → Act** (`Invoice.sp_act_id`): 391 живой счёт → 391 разный акт; ни один акт не связан с двумя счетами; 12 живых актов без живого счёта.
- **Платежи:** `SPPayments.related_to` → Invoice 615 / SalesOrder 7 / пусто 176, плюс `crmentityrel` Invoice↔SPPayments; у 38 платежей эти два источника указывают **разные** счета, 120 платежей не распределены (разбиение — `finance-contract.md` §8).

## 7. Вложения и файлы

- `vtiger_attachments` 572 строки: живые 238 — **все файлы найдены** на диске (`storage/<год>/<месяц>/<неделя>/<id>_<имя>`), ~106 МБ; 334 удалённых вложения MailManager — файлов нет (ожидаемо).
- Documents: 202 внутренних (файл) + 13 внешних (URL); у 3 внутренних документов нет строки вложения; 12 из 13 внешних и 199 внутренних связаны с записями. MIME: application 175, image 23, text 1.
- В `storage/` 247 файлов, из них 8 не связаны ни с одной строкой `vtiger_attachments` (3 в корне, 5 в 2018 г.).
- `Contacts.imagename` заполнено у 6 контактов, но изображение-вложение одно — 5 имён без файла.
- `test/logo` (11 файлов логотипов), `test/upload` (8 файлов), `test/mosaico` (шаблоны email-маркетинга) — вне `vtiger_attachments`.

## 8. Бизнес-логика

- **Workflows** (`com_vtiger_workflows` 26, все `status=1`, все помечены `defaultworkflow` кроме Products/Services/SPUnits): уведомления по email (HelpDesk ×11, Contacts, Accounts, Potentials, Calendar, Events), `UpdateInventory` для Invoice (2 одинаковых workflow) и PurchaseOrder, `SendPortalLoginDetails`, `processCodeUnit`/`processUsageUnit` (SPUnits), `VTUpdateFieldsTask` Potentials → `forecast_amount`, `SPCallPopupCustomTask`. Две задачи (`task_id` 17, 18) ссылаются на несуществующий workflow. Пользовательских бизнес-правил, влияющих на суммы, не найдено.
- **Обработчики событий:** 34, все стандартные Vtiger/SalesPlatform/VTE (ModTracker, RecurringInvoice, InvoiceHandler, PBXManagerHandler, EmailLookup, CheckDuplicate, FollowRecord, AdvancedCustomFields).
- **Планировщик (`vtiger_cron_task`):** активны Workflow, RecurringInvoice, SendReminder, MailScanner, ScheduleReports, VTEMailConverter, VTEEmailMarketing, AutomatedBackup (каждые 30 мин), Reports4You; выключены Scheduled Import, SPCMLConnector (1С), VTEReports (status 2).
- **Периодические счета:** 3 SalesOrder с `enable_recurring=1`, периоды закончились в 2016 г.; счетов из заказов — 26 в 2016 г. и 1 в 2023 г. Фактически не используется.
- **Отчёты:** 28 (25 стандартных + «Отчёт по платежам», «Отчёт по проектным задачам», «Оперативные задачи …» по сотруднику); фильтров списков 69 (4 пользовательских у Contacts, 1 у ProjectTask).
- **Кастомный код** (вне расширений): `req.php` (вебхук Jivosite: создаёт записи через webservice от `user#1`, права `777`), `addLink.php` (добавление ссылки интеграции банка «Точка»), `modules/SPPayments/actions/TochkaIntegrator.php` + `models/BankApi.php` (импорт выписки банка «Точка» API v1 в SPPayments: плательщик по ИНН `Accounts.inn`/`Vendors.cf_1206`, счёт — **первый счёт в статусе Sent этого плательщика**, дедупликация по `cf_1204`; использовался в 2018–2020 гг.), `vtdm.php` (удаление модуля по GET-параметру без проверки прав), `script-add.php` (тест). Много модулей VTE/ITS4You зашифровано ionCube — их логика не читается, учитываются только данные.
- **Интеграции с секретами в БД** (значения не выводились): 3 IMAP-учётки `vtiger_mail_accounts`, Google OAuth (2 строки, 100 сопоставлений событий календаря, 286 сопоставлений контактов WSAPP), шлюз PBXManager (ключи `webappurl`, `outboundcontext`, `vtigersecretkey`), настройки SPVoipIntegration (провайдер по умолчанию zadarma; заполнены только URL провайдеров), `vtiger_ws_userauthtoken` 2.

## 9. История изменений

- `vtiger_modtracker_basic` 10 328, `vtiger_modtracker_detail` 110 582, `vtiger_modtracker_relations` 3 004; период 2018-07 … 2026-09. Больше всего — Invoice (21 016 значений), PBXManager (16 609), SPPayments (15 741), Act (14 285), ProjectTask (9 952).
- **Значения полей доступа есть в истории:** `cf_1322` 126 записей, `cf_1324` (пароль) 135 (прежних непустых 9, новых 131), `cf_1326` 126, `cf_1328` 127.
- Истории статусов: `vtiger_invoicestatushistory` 588 (2018-07…2026-09), `vtiger_sp_actstatushistory` 51 (до 2022-01), `vtiger_potstagehistory` 9.
- `vtiger_loginhistory` 1 737 (журнал входов — ПДн, не переносится).

## 10. Находки безопасности (без изменений production)

1. Пароли AnyDesk и другие поля доступа хранятся открытым текстом, видимы всем профилям с доступом к Contacts и дублируются в истории изменений.
2. `vtdm.php` позволяет удалить модуль GET-запросом без проверки прав (защищён только общей Basic Auth vhost).
3. `req.php` с правами `777` принимает вебхук без проверки подписи и пишет лог в корень сайта (файла лога сейчас нет).
4. Общая учётная запись Basic Auth для всех пользователей.
5. Записи разговоров и CSV CDR не входят в резервное копирование.
