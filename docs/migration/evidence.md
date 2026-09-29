# Доказательства аудита (этап 01)

Все команды — только чтение. Значения строк, секреты, номера телефонов и реквизиты здесь не приводятся. Приватные результаты лежат вне Git; ниже — только их пути.

## Сессия

| Параметр | Значение |
|---|---|
| Дата | 2026-09-29 |
| Окно проверок | 18:35–20:05 CEST (`date -Is` на сервере: `2026-09-29T18:34:59+02:00` в начале) |
| Источник | `sergey@serv.sergeyem.ru` (Ubuntu 26.04), MySQL 8.4.11 через `sudo -n mysql` (сокет), БД `vtiger7`, `asteriskcdrdb`; Apache-логи `server.itvolga_access.log*`; Asterisk CLI; файловая система |
| Локальные источники | `/data/server` (git `9dcf93a`): `CLAUDE.md`, `ansible/roles/{vtiger,asterisk,backup,php_docker,mysql}`, `ansible/playbooks/04-apps.yml`, `scripts/export-*.sh`; память прежних сессий `~/.claude/projects/-data-server/memory/` — как гипотезы |
| Приватный результат | `/data/itvolga/espo-private/audit/20260929T1840/` (основной), `/data/itvolga/espo-private/audit/20260929T2000-rerun/` (контрольный повтор); права `700`/`600` |
| Воспроизведение | `scripts/audit/run-audit.sh` (≈30 с); `AUDIT_TS=<имя>` задаёт каталог результата |

## Ограничения безопасности запросов

- Каждый SQL-пакет начинается с `SET SESSION TRANSACTION READ ONLY;` (`scripts/audit/lib.sh: remote_sql`).
- Запросы возвращают только `COUNT/SUM/MIN/MAX` дат, метаданные схемы и значения справочников (picklist/checkbox). Для текстовых полей — только признак непустоты.
- Тексты шаблонов, пути вложений, CDR и имена WAV обрабатываются **на сервере** скриптами из `scripts/audit/remote/`; наружу выходят счётчики, sha256-префиксы и списки плейсхолдеров. Временные файлы — `/tmp/espo_audit_*`, удаляются той же командой.
- Поля доступа контактов (`cf_1322`–`cf_1328`) и их история: только `COUNT`/`SUM(... <> '')`.

## Шаги и файлы

| # | Что | Команда/файл | Результат (приватно) |
|---|---|---|---|
| 1 | Модули, поля, колонки, таблицы, PK, общие таблицы | `sql/01_tabs.sql` … `06_shapes.sql` | `01_tabs.tsv` … `06_shapes.tsv` |
| 2 | Точные `COUNT(*)` всех 784 таблиц | `gen_sql.py table-counts` | `10_table_counts.tsv` |
| 3 | Непустые/ненулевые значения каждой колонки 534 непустых таблиц | `gen_sql.py column-counts` (один проход на таблицу, `JSON_OBJECT`) | `11_column_counts.raw` |
| 4 | Непустые значения полей по **живым** записям модуля (join `vtiger_crmentity`, для Calendar/Events/Emails — фильтр `activitytype`) | `gen_sql.py field-live-counts` | `12_field_live_counts.raw` |
| 5 | Распределение целей ссылочных полей и владельцев | `gen_sql.py reference-targets` | `13_reference_targets.tsv` |
| 6 | Распределения значений справочников и чекбоксов | `gen_sql.py picklist-values` | `14_picklist_values.tsv` |
| 7 | Связи, кардинальности | `sql/20_relations.sql`, `sql/32_cardinality.sql` | `20_*.tsv`, `32_*.tsv` |
| 8 | Пользователи (без имён), роли, профили, шаринг, владельцы | `sql/21_acl.sql` | `21_acl.tsv` |
| 9 | Файлы вложений на диске | `remote/check_attachments.py` | `22_attachments_files.tsv` |
| 10 | Шаблоны: плейсхолдеры, хеши | `sql/23_templates.sql` → `remote/template_tokens.py` | `23_templates.tsv` |
| 11 | Использование модулей по access-логам (2026-09-15…29) | `remote/access_log_usage.py` | `24_access_usage.tsv` |
| 12 | Хронология, workflows, cron, обработчики, отчёты, история | `sql/25_activity_workflows.sql` | `25_*.tsv` |
| 13 | Пересчёт итогов документов | `sql/26_finance.sql`, `sql/34_finance_config.sql` | `26_*.tsv`, `34_*.tsv` |
| 14 | Платежи, нумерация, счёт→акт | `sql/27_payments.sql`, `sql/33_allocation_check.sql` | `27_*.tsv`, `33_*.tsv` |
| 15 | PBXManager, VoIP-настройки (только признаки заполненности) | `sql/28_pbx.sql` | `28_pbx.tsv` |
| 16 | Asterisk, AMI (без секретов), CDR CSV, WAV, бэкапы | `remote/telephony_inventory.sh`, `sql/40_cdr.sql` | `29_telephony.txt`, `40_cdr.tsv` |
| 17 | CSV↔MySQL CDR, WAV↔`recordingpath` | `remote/cdr_overlap.py` | `30_cdr_overlap.tsv` |
| 18 | Документы, почта, портал, Google, расширения | `sql/31_misc.sql` | `31_misc.tsv` |
| 19 | Денежные контрольные суммы (**приватно**) | `sql/35_control_sums_private.sql` | `35_control_sums_private.tsv` |
| 20 | Сводная таблица колонок | `consolidate.py` | `columns.tsv` |
| 21 | Карты для Git | `build_maps.py` → `docs/migration/field-map.csv`, `relations.csv` | — |

Контроль воспроизводимости: полный повтор в 20:00 (`20260929T2000-rerun`) — `field-map.csv` и `relations.csv` идентичны первому прогону (`diff` пуст), счётчики вложений и CDR совпали.

## Ключевые воспроизводимые запросы

```sql
-- Модули и число записей (01_tabs.sql)
SELECT t.name, (SELECT COUNT(*) FROM vtiger_crmentity c WHERE c.setype=t.name AND c.deleted=0) live,
       (SELECT COUNT(*) FROM vtiger_crmentity c WHERE c.setype=t.name AND c.deleted=1) deleted
FROM vtiger_tab t;

-- Одно юрлицо: справочник и использование (34_finance_config.sql, 14_picklist_values)
SELECT spcompany, presence FROM vtiger_spcompany;
SELECT company, (inn<>'') has_inn FROM vtiger_organizationdetails;
SELECT YEAR(invoicedate), SUM(spcompany='Default'), SUM(spcompany='По умолчанию') FROM vtiger_invoice GROUP BY 1;

-- Класс формулы итога документа (34_finance_config.sql: formula_class)
-- Счёт → акт (27_payments.sql: invoice_act)
SELECT COUNT(DISTINCT sp_act_id), MAX(cnt) FROM (SELECT sp_act_id, COUNT(*) cnt FROM vtiger_invoice
  WHERE sp_act_id<>0 GROUP BY sp_act_id) x;

-- Конфликты распределения платежей (33_allocation_check.sql: rel_vs_related_to)

-- Поля доступа: только число заполненных
SELECT SUM(cf_1324 IS NOT NULL AND TRIM(cf_1324)<>'') FROM vtiger_contactscf cf
  JOIN vtiger_crmentity c ON c.crmid=cf.contactid AND c.deleted=0;
SELECT d.fieldname, COUNT(*) FROM vtiger_modtracker_detail d WHERE d.fieldname IN ('cf_1322','cf_1324','cf_1326','cf_1328') GROUP BY 1;

-- PBXManager по месяцам и шаблон ссылок записи (28_pbx.sql)
SELECT REGEXP_REPLACE(REGEXP_SUBSTR(recordingurl,'^[a-z]+://[^/]+'),'[0-9]','9'), COUNT(*) FROM vtiger_pbxmanager GROUP BY 1;
```

Файловые проверки (выполнялись через `ssh … 'sudo -n bash -s'`):

```bash
cat /var/www/serv_itvolga/vtiger7/spServicePackVersion.txt; grep vtiger_current_version vtigerversion.php
find /var/spool/asterisk/monitor -type f -printf '%TY-%Tm %s\n' | awk '{m[$1]++; s[$1]+=$2} END{for(k in m) print k, m[k], s[k]}'
awk -F'","' '{print substr($10,1,7)}' /var/log/asterisk/cdr-csv/Master.csv | sort | uniq -c
awk -F= '/^\s*(enabled|port|bindaddr)\s*=/' /etc/asterisk/manager.conf     # без secret
grep -o -E "'[A-Z_]+'\s*=>" config.performance.php                          # только ключи
```

## Проверка гипотез из прежних документов

| Гипотеза | Источник | Вердикт |
|---|---|---|
| Vtiger 7.1 на PHP 7.4 в Docker, cron через враппер от www-data | `/data/server` CLAUDE.md, роль `vtiger` | подтверждено |
| «Vtiger CRM 7.1» (без уточнения) | CLAUDE.md | уточнено: SalesPlatform 7.1 SP01 + ~40 расширений VTE/ITS4You (ionCube) |
| CDR пишется в MySQL `asteriskcdrdb.cdr` через ODBC, CSV — дубль | README роли `asterisk` | подтверждено; MySQL-строки только с 2026-08, CSV — с 2026-06-13 |
| Записи в `/var/spool/asterisk/monitor` | README роли | подтверждено (166 WAV); каталог **не** в бэкапе |
| `unanswered=no` в `cdr.conf` | README роли | не проверено |
| Старые скрипты экспорта `scripts/export-*.sh` | `/data/server` | относятся к старому серверу; `export-asterisk.sh` переносил только звуки IVR |
| Срез 2026-09-28 | постановка | **не найден** (Q-29) |
| URL записи Vtiger `127.0.0.1:5000` | постановка | подтверждено: 1033 ссылки, коннектор отсутствует |
| `Default`/`По умолчанию` — одно значение | постановка | подтверждено (D-04) |
| «Многочисленные связи Invoice → Act» | постановка (этап 04.5) | фактически ≤ 1:1 (391 счёт → 391 акт); ограничение 1:1 всё равно не вводится |

## Что проверить не удалось

- Какие печатные формы используются: журналов генерации PDF нет, POST-параметры в access-логах не пишутся.
- Логика модулей VTE/ITS4You и части Settings: код зашифрован ionCube.
- Часовой пояс хранения дат (Q-05) — требует сравнения с UI.
- История звонков 2024-07-31…2026-06-12 — источников нет.

## Инцидент вывода в консоль сессии

Значения полей доступа контактов не выводились ни разу. При этом в консоль сессии (не в файлы и не в Git) попало: (1) при широком `find` по серверу — имена каталогов пользовательского облака OpenCloud; (2) при чтении `modules/SPPayments/models/BankApi.php` — одно ФИО, захардкоженное в коде как исключаемый контрагент; (3) при чтении `defaults/main.yml` роли `asterisk` из `/data/server` — служебные номера телефонов, уже хранящиеся в том репозитории. Меры: поиск по файловой системе — только по конкретным путям; исходный код Vtiger читается через `grep` по ключевым словам с маскированием; содержимое `/data/server` не копируется в этот репозиторий.

## Проверка Git перед коммитом

`scripts/check-secrets.sh` (регулярные выражения по секретам/ПДн + сверка sha256 с хешами реальных ПДн из БД, подготовленными на сервере) — результат фиксируется в `TASKS.md`.
