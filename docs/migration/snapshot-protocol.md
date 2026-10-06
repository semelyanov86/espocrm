# Протокол защищённого снимка

Сгенерирован `task snapshot:protocol -- 20261006T192211` (`scripts/snapshot/snapshot.py`). Только счётчики, размеры и идентификаторы схемы; значений строк, имён файлов и реквизитов нет. Формат, границы, права и очистка — `docs/migration/snapshot.md`.

- Снимок: `20261006T192211`, формат `itvolga-vtiger-snapshot` v1; печать (sha256 файла SHA256SUMS): `a027b4422faf3e277613eaf620fe750484bf01482f5589ef2c26dddac51c902b`.
- Код: `b0ba74399db0`; источник: MySQL 8.4.11, `time_zone=SYSTEM` (`CEST`), `sql_mode=ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION`.
- Проверка: `2026-10-06T17:54:38Z` … `2026-10-06T17:54:49Z` — **пройдена**.

## Границы согласованности

| Часть | Граница | Время (UTC) |
|---|---|---|
| БД vtiger7, asteriskcdrdb | одна транзакция `READ ONLY` с `CONSISTENT SNAPSHOT` (InnoDB); 3 таблицы MyISAM — неизменны от начала до конца транзакции | 2026-10-06T17:22:13.613039Z … 2026-10-06T17:22:17.862584Z (4.8 с) |
| файлы `cdr-csv` | файлы целиком на момент описи | опись 2026-10-06T17:22:29Z |
| файлы `monitor` | время изменения ≤ конца транзакции | опись 2026-10-06T17:22:30Z |
| файлы `vtiger` | время изменения ≤ конца транзакции | опись 2026-10-06T17:22:17Z |

## Состав

| Часть | Таблиц | Строк | Размер |
|---|---:|---:|---:|
| БД `vtiger7` | 784 | 197076 | 1.9 MiB (сжато) |
| БД `asteriskcdrdb` | 1 | 114 | 0.0 MiB (сжато) |

| Файлы | Корень источника | Файлов | Размер | Новее границы (не взяты) | Ссылок/спецфайлов |
|---|---|---:|---:|---:|---:|
| `cdr-csv` | `/var/log/asterisk/cdr-csv` (.) | 1 | 0.0 MiB | 0 | 0/0 |
| `monitor` | `/var/spool/asterisk/monitor` (.) | 173 | 1221.3 MiB | 0 | 0/0 |
| `vtiger` | `/var/www/serv_itvolga/vtiger7` (storage, test/logo, test/upload) | 266 | 105.3 MiB | 0 | 0/0 |

## Проверки

| Код | Проверка | Итог | Счётчики |
|---|---|---|---|
| V1 | печать SHA256SUMS и права 700/600 | пройдена | bad_permissions 0, extra 0, mismatch 0, missing 0, sealed 1583 |
| V2.cdr-csv | файлы части cdr-csv = опись (размер, sha256) | пройдена | extra 0, files 1, mismatch 0, missing 0 |
| V2.monitor | файлы части monitor = опись (размер, sha256) | пройдена | extra 0, files 173, mismatch 0, missing 0 |
| V2.vtiger | файлы части vtiger = опись (размер, sha256) | пройдена | extra 0, files 266, mismatch 0, missing 0 |
| V3.vtiger7 | строки vtiger7: формат, порядок, число и дайджест = данные сервера | пройдена | bad_tables 0, rows 197076, tables 784 |
| V3.asteriskcdrdb | строки asteriskcdrdb: формат, порядок, число и дайджест = данные сервера | пройдена | bad_tables 0, rows 114, tables 1 |
| V4.vtiger7 | восстановленная копия vtiger7: схема, число строк, дайджесты и счётчики колонок | пройдена | differ 0, schema_equal 1, tables 784 |
| V4.asteriskcdrdb | восстановленная копия asteriskcdrdb: схема, число строк, дайджесты и счётчики колонок | пройдена | differ 0, schema_equal 1, tables 1 |
| C1 | каждая пара «таблица.колонка» field-map.csv есть в снимке | пройдена | absent 0, map_rows 3242, pairs 2854, tables 554 |
| C2 | источник каждой связи relations.csv есть в снимке | пройдена | relations 287, unresolved 0 |
| C3 | каждый модуль с записями есть в field-map.csv | пройдена | deleted 502, live 5807, modules_with_records 29, unmapped 0 |
| C4 | field-map.csv, пересобранная по снимку = карта в Git (кроме счётчиков) | пройдена | committed 3242, count_changed 0, decision_changed 0, fresh 3242, only_committed 0, only_fresh 0 |
| C5 | relations.csv, пересобранная по снимку = карта в Git (кроме счётчиков) | пройдена | committed 287, count_changed 0, decision_changed 0, fresh 287, only_committed 0, only_fresh 0 |
| C6 | файл каждого живого вложения есть в снимке | пройдена | deleted_found 0, deleted_missing 334, live 238, live_found 238, live_missing 0, orphan_files 8, orphan_files_after_t0 0, rows 572 |
| C7 | принятые потери источника (D-23): фото контактов и документы без вложения | сведения | contact_images_without_file 5, internal_documents_without_attachment 3 |
| C8 | логотип юрлица (logoname) есть в снимке | пройдена | found 1, logos 1 |
| C9 | запись каждого CDR (recordingpath) есть в снимке | пройдена | cdr_rows 114, found 93, missing 0, outside_monitor 0, recording_paths 93, wav_files 173, wav_without_cdr 80 |
| C11 | CDR CSV (Master.csv) есть в снимке | пройдена | present 1 |
| C10 | CDR CSV: строки, после T0, общие uniqueid с MySQL | сведения | csv_rows 204, csv_rows_18_fields 204, csv_rows_after_t0 0, csv_rows_with_mysql_uniqueid 114 |
| V5 | временные базы стенда удалены (по точному имени) | пройдена | created 2, dropped 2 |

## Модули с записями

| Модуль | Живых | Удалённых |
|---|---:|---:|
| Accounts | 180 | 2 |
| Act | 404 | 1 |
| Assets | 3 | 0 |
| Calendar | 86 | 100 |
| Consignment | 1 | 0 |
| Contacts | 341 | 4 |
| Documents | 215 | 12 |
| Emails | 29 | 151 |
| Faq | 63 | 0 |
| HelpDesk | 45 | 14 |
| Invoice | 636 | 2 |
| JVmes | 267 | 5 |
| Jivosite | 49 | 3 |
| Leads | 225 | 16 |
| ModComments | 78 | 0 |
| Notifications | 1 | 0 |
| PBXManager | 1116 | 0 |
| Potentials | 156 | 0 |
| Products | 3 | 0 |
| Project | 54 | 0 |
| ProjectTask | 493 | 0 |
| Quotes | 24 | 0 |
| SPCallPopup | 210 | 0 |
| SPPayments | 799 | 192 |
| SalesOrder | 14 | 0 |
| ServiceContracts | 1 | 0 |
| Services | 25 | 0 |
| VTEItems | 286 | 0 |
| Vendors | 3 | 0 |

## Вложения (`vtiger_attachments`)

| setype | deleted | Итог | Строк |
|---|---|---|---:|
| Contacts Image | 0 | found | 1 |
| Documents Attachment | 0 | found | 199 |
| Emails Attachment | 0 | found | 1 |
| MailManager Attachment | 0 | found | 34 |
| MailManager Attachment | 1 | missing | 334 |
| ModComments Attachment | 0 | found | 2 |
| Users Image | 0 | found | 1 |

## Права и очистка

Каталог снимка — `700`, файлы — `600`, владелец — разработчик; временные базы стенда удалены по точному имени (создано 2, удалено 2). Удаление снимка — `task snapshot:delete -- 20261006T192211 --yes`.
