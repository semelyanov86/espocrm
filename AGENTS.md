# AGENTS.md — правила проекта миграции Vtiger 7.1 → EspoCRM

Этот файл читает каждый агент/сессия **до** начала работы. Затем — `TASKS.md` и относящиеся к этапу файлы `docs/migration/`.

## Цель

Перенести CRM `serv.itvolga.com` (Vtiger 7.1.0 + SalesPlatform SP01 + расширения VTE/ITS4You) на EspoCRM **без платных расширений** (Sales Pack, Advanced Pack, VoIP Integration и т. п.). Финансовые документы (Quote, SalesOrder, Invoice, Act, Payment), печатные формы и телефония реализуются собственным открытым кодом в этом репозитории.

## Этапность

- Работа идёт по этапам из `TASKS.md`: **один этап за сессию**. Не переходить к следующему этапу в той же сессии.
- Если этап заблокирован — сделать всю независимую работу, записать блокер в `TASKS.md`, закоммитить и остановиться.
- Каждая сессия заканчивается: обновлением `TASKS.md` и затронутых `docs/migration/*`, проверкой `git diff` и секретов (`scripts/check-secrets.sh`), отдельным коммитом, SHA в итоговом ответе.
- При расхождении документов и живого сервера приоритет у **свежей read-only проверки**; карту исправить и указать дату проверки.

## Production

- Рабочий сервер `sergey@serv.sergeyem.ru` и локальный репозиторий `/data/server` (Ansible) — **только чтение** до этапа 10 (размещение рядом с Vtiger) и 11 (переключение), каждый требует отдельного явного разрешения пользователя.
- Разрешено на сервере: `SELECT` в сессии `SET SESSION TRANSACTION READ ONLY`, `ls/stat/find/wc/du`, `asterisk -rx "... show ..."`, чтение логов для агрегатов. Запрещено: любые записи в БД/файлы, рестарты сервисов (Asterisk, Apache, php74-fpm, MySQL), изменения cron, установка пакетов.
- Код Vtiger/SalesPlatform анализируется по локальной приватной копии `/data/itvolga/espo-private/vtiger-src/vtiger7/` (`scripts/audit/sync-vtiger-src.sh`: только код, без данных, секретов и закрытых модулей VTE/ITS4You); на сервере — только данные (read-only SQL) и адресные проверки.
- Скрипты для сервера передаются **inline** (`scripts/audit/lib.sh`: `remote_sql_py`, `remote_py` — base64 в `python3 -c`, shell — через `bash -s`); файлы на сервере не создаются. Если временный файл неизбежен — `mktemp` + `trap rm` в одной SSH-команде.
- Не перезапускать production Asterisk и не менять транки/маршрутизацию. AMI — только локальный, минимальные права.
- Сохранять PHP 7.4 / контейнер `php74-fpm`: им пользуется Lahic.
- Старые `scripts/export-vtiger.sh`, `task export:vtiger`, `task migrate:vtiger` из `/data/server` относятся к прежнему серверу — не использовать как готовый экспорт.

## Данные и приватность

- В Git **не попадают**: дампы БД, выгрузки строк, вложения, аудио (WAV), персональные данные, реквизиты доступа, реальные реквизиты организаций и клиентов, приватные отчёты сверки.
- Приватные результаты — вне репозитория: `/data/itvolga/espo-private/` (права `700`). В Git — только код, шаблоны конфигов, обезличенные сводки (счётчики, схемы, распределения значений справочников).
- **Поля доступа контактов** (`Contacts.cf_1322` AnyDesk ID, `cf_1324` AnyDesk Password, `cf_1326` Hostname, `cf_1328` IP) и их история в `vtiger_modtracker_detail`: значения **никогда** не выводить в консоль, логи, отчёты, тесты, фикстуры. Только счётчики и хеши, вычисленные на сервере.
- Имена людей, телефоны, e-mail, ИНН/счета, IP клиентов в документах заменяются на `user#<id>`, счётчики или шаблоны (`С-999`).
- Запросы для доказательств — в `scripts/audit/sql/*.sql` или `docs/migration/evidence.md`: воспроизводимые, без значений строк и без секретов.
- Секреты (пароли БД, AMI, API-ключи) — только вне Git (vault/`.env` вне репозитория); в Git — шаблоны `*.example`. Секреты стенда — `/data/itvolga/espo-private/stand/local.env`, backup стенда — `/data/itvolga/espo-private/stand/backups/` (содержат `config-internal.php`).
- Тестовые данные — только синтетические: фикстуры в `tests/fixtures/synthetic/`, тесты создают и удаляют свои записи сами (`tests/stage03/`); JSON вне `custom/Espo/{Custom,Modules}/`, `client/custom/` и этого каталога игнорируется `.gitignore`.

## Код и структура

- `scripts/audit/` — воспроизводимый аудит источника (`run-audit.sh`).
- `docs/migration/` — постоянная память миграции (карта полей, связи, решения, вопросы, доказательства).
- Локальный стенд (этап 02, `docs/local-stand.md`): ядро EspoCRM распаковывается в корень репозитория из закреплённого релиза и в Git не попадает; настройки — `deploy/local/stand.conf`, шаблоны — `deploy/local/templates/`, скрипты — `scripts/stand/`, команды — `Taskfile.yml`. Консоль EspoCRM — только `task espo -- …` (от пользователя `espocrm`, PHP 8.5), не `bin/command` напрямую. Ядро не править: изменения — только в `custom/`, `client/custom/`.
- Модель CRM (этап 03, D-40): модуль `custom/Espo/Modules/Itvolga` (метаданные, layouts, i18n, хуки, API, команда `itvolga-setup-acl`) и `client/custom/modules/itvolga`; `custom/Espo/Custom` — только для правок администратора. Описание — `docs/migration/model.md`; развёртывание — `task model:apply`, тесты — `task test:stage03`, сверка с картой — `task model:check`. Словарь значений (`metadata/vtigerValueMap`) и опции enum не править вручную: генератор `scripts/model/build_value_maps.py`.
- Финансы (этап 04.1, D-45): контракт сущностей — `docs/migration/finance-contract.md` §11; расчётное ядро без зависимостей от EspoCRM — `custom/Espo/Modules/Itvolga/Tools/Finance/` (bcmath, float запрещён, исходные суммы не пересчитываются); тесты — `task test:finance` (приватная часть — по срезу аудита, печатает только счётчики), профиль источника — `task finance:profile -- <срез>`. Правила, которых нет в данных, ядро отклоняет (Q-36…Q-38), а не угадывает.
- Будущие этапы: импорт в `scripts/import/`, тесты в `tests/`, Ansible — отдельно, по этапу 09.
- Язык общения и документации — русский; код, идентификаторы и комментарии в коде — английский.
- Имена: собственные сущности — `Invoice`, `InvoiceItem`, `Act`, `ActItem`, `Payment`, `PaymentAllocation`, `Quote`, `SalesOrder`, `Product`, `Project`, `ProjectTask`, `Vendor`, `LegalEntity`, `VtigerArchive`, `ContactAccess`; кастомные поля стандартных сущностей — с префиксом `c` (`cInn`); на каждой импортируемой сущности — `vtigerId`, при наличии номера — `vtigerNo`/`number`; нераспределённые значения — `vtigerData` (JSON, только чтение).
- Деньги — десятичная арифметика, без float. Исходные суммы Vtiger — эталон: пересчёт не должен молча их менять.

## Проверка интерфейса

- Инструмент — скилл `playwriter` (браузер Chrome владельца через расширение Playwriter; установлен 2026-09-30); подробности, помощники и известные особенности — `CLAUDE.md`, раздел «Проверка интерфейса: Playwriter».
- Локальный стенд — только на синтетических данных (`tests/stage03/ui_fixture.py`), вход — `tests/stage03/ui_login.js` (пароли из приватных файлов, не печатаются).
- Production Vtiger `serv.itvolga.com` — только просмотр: не сохранять формы и не запускать действия (массовые операции, рассылки, workflow, click-to-call); карточки и списки с полями доступа контактов (`cf_1322`–`cf_1328`) не открывать.
- Снимки экрана — только в `/data/itvolga/espo-private/stand/evidence/<этап>/`, не в Git; cookies браузера удалять только для домена стенда.

## Проверки перед коммитом

1. `scripts/check-secrets.sh` — регулярные выражения + сверка хешей реальных ПДн (если доступен приватный список хешей).
2. `git status` / `git diff --cached` — только безопасные артефакты.
3. Никаких файлов из `/data/itvolga/espo-private/` и `/data/server/backup/`.
