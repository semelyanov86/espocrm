# CLAUDE.md

Инструкции для Claude Code в репозитории миграции Vtiger 7.1 → EspoCRM. Основные правила проекта — в `AGENTS.md` (подключён ниже) и обязательны; этот файл добавляет только порядок работы сессии.

@AGENTS.md

## Начало сессии

1. Прочитать `TASKS.md`: текущий этап, блокеры, стартовая команда. Работать **только над одним этапом**.
2. Прочитать относящиеся к этапу файлы `docs/migration/` (карта полей и связей, решения `D-xx`, вопросы `Q-xx`).
3. Факты, от которых зависит этап, перепроверить read-only; при расхождении — исправить документ и указать дату проверки.
4. Промпт этапа: `git show 2052380:MIGRATION_PROMPTS.md` (файл удалён из рабочей копии).

## Команды

```bash
scripts/audit/run-audit.sh                 # полный read-only аудит источника (~30 с) → приватный каталог + карты
scripts/audit/sync-vtiger-src.sh           # обновить локальную копию кода Vtiger (без данных, секретов и закрытых модулей)
AUDIT_TS=<метка> scripts/audit/run-audit.sh
scripts/audit/build-pii-hashes.sh          # обновить приватные хеши ПДн для проверки Git
scripts/check-secrets.sh --self-test       # самопроверка правил сканера
scripts/check-secrets.sh --history         # обязательная проверка перед каждым коммитом
task stand:install | stand:health          # локальный стенд EspoCRM (docs/local-stand.md)
task stand:backup | stand:restore -- latest --yes
task espo -- rebuild                       # консоль EspoCRM; bin/command напрямую не запускать
task test:finance                          # тесты расчётного ядра финансов (этап 04.1)
task test:stage04                          # приёмочные тесты Quote/SalesOrder на стенде (этап 04.2)
```

- `docs/migration/field-map.csv` и `relations.csv` **не редактировать вручную**: правила — `scripts/audit/mapping.py`, генерация — `scripts/audit/build_maps.py` из приватного прогона.
- Приватные результаты: `/data/itvolga/espo-private/` — читать можно, выводить содержимое строк нельзя, в Git не добавлять.

## Работа с production

- Только чтение; SQL — через `scripts/audit/lib.sh` (`remote_sql`, `remote_sql_py`: `SET SESSION TRANSACTION READ ONLY`), скрипты на сервер — inline, без файлов.
- **Код Vtiger/SalesPlatform смотреть в локальной копии**, а не на сервере: `/data/itvolga/espo-private/vtiger-src/vtiger7/` (7.1.0 SP01, снята 2026-09-30, дата и версия — `COPIED_AT.txt`; обновить — `scripts/audit/sync-vtiger-src.sh`). В копии только код: без `storage/`, `test/`, `cache/`, `logs/`, `user_privileges/`, `packages/`, `config*.php` с паролями и без закрытых модулей VTE/ITS4You (ionCube, их код не используется). Копия приватная: не в Git, фрагменты с захардкоженными ПДн (например, `modules/SPPayments/models/BankApi.php`) не выводить. Данные (БД, файлы вложений) — только read-only SQL и адресные проверки на сервере.
- Не выполнять широкие `find`/`cat` по серверу и не печатать исходники с данными: только адресные пути и `grep` по ключевым словам с маскированием.
- Поля доступа контактов (`Contacts.cf_1322`–`cf_1328`) и их история — только счётчики.

## Завершение этапа

1. Обновить `TASKS.md` (статус, проверки с датой, пути приватных отчётов без содержимого, стартовая команда следующего этапа) и затронутые `docs/migration/*`.
2. `scripts/check-secrets.sh --history` → 0 находок; `git diff --cached` — только безопасные артефакты.
3. Отдельный коммит (Conventional Commits, тело на английском); SHA — в итоговом ответе.
4. Внешнее ревью: закоммиченный результат отдать Codex `gpt-6.1-sol` (с 2026-09-30; этапы 01–02 — `gpt-6-sol`) в отдельном git worktree, read-only, без сети и без доступа к `/data/itvolga/espo-private`:
   `env -i HOME=$HOME PATH=$PATH codex exec -m gpt-6.1-sol --sandbox read-only --ephemeral -C <worktree> -o <review.md> - < prompt.md`.
   Каждое замечание проверить самостоятельно, исправить подтверждённые, записать итог в `docs/migration/evidence.md` и `TASKS.md`.
5. Остановиться: следующий этап — только в новой сессии; этапы 10 и 11 — только по отдельному явному разрешению пользователя.

## Стиль

- Общение и документация — на русском; код, идентификаторы, комментарии и сообщения коммитов — на английском.
- Непроверенное помечать явно («не проверено», `mapping_status=не проверено`, вопрос `Q-xx`); не выдавать предположения за факты.

## Проверка интерфейса: Playwriter

Для UI-проверок основной инструмент — скилл **`playwriter`** (установлен владельцем 2026-09-30): управляет браузером Chrome владельца через расширение Playwriter. Применять вместо Playwright MCP и `/metaswarm:visual-review`.

- Перед первой командой в сессии загрузить скилл и прочитать `playwriter skill` целиком; работать в своей сессии: `playwriter session new --tab-group test`, дальше `playwriter -s <id> -e '…'` / `-f файл.js`; свои вкладки закрывать, чужие не трогать.
- Где можно: локальный стенд `crm.itvolga.test` — на синтетических данных (`tests/stage03/ui_fixture.py create|delete`); production Vtiger `serv.itvolga.com` — только просмотр по правилам ниже (раздел metaswarm, Visual review): без сохранения форм и действий, без карточек и списков с полями доступа контактов.
- Снимки — только в `/data/itvolga/espo-private/stand/evidence/<этап>/` (права 600), не в Git и не в `/tmp`. Сессию Playwriter создавать из этого каталога: песочница пишет только в каталог сессии и `/tmp`.
- Вход на стенд: `tests/stage03/ui_login.js` (`state.who = "admin" | "deputy" | "access"`; для фикстуры этапа 04.2 `tests/stage04/ui_fixture.py` — `state.who = "director" | "fdeputy"` и `state.usersEnv` = её `ui-users.env`); пароли читаются из приватных файлов через `await import('node:fs')` (песочный `require('node:fs')` не читает вне каталога сессии) и не печатаются.
- Известные особенности (2026-09-30): фокус на полях входа провоцирует менеджер паролей браузера, вкладка отключается — значения полей входа задавать через DOM; `#logout` перезагружает приложение и отключает вкладку — выходить удалением cookies только домена стенда (`Network.deleteCookies`, никогда `clearBrowserCookies`); после `task model:apply` (новая отметка времени) EspoCRM показывает окно «Приложение было обновлено» — закрыть его перед кликами; `HeapProfiler` через расширение недоступен; поля выбора EspoCRM — не нативные `select`, варианты читать из выпадающего списка.
- Особенности 2026-10-01: штатные числовые поля EspoCRM (decimal/currency) после `locator.fill()` не попадают в сохранение — вводить с клавиатуры (`click` → `Control+A` → `keyboard.type`); `page.screenshot` упирается в тайм-аут расширения, когда вкладка в фоне (на передний план не выводить — проверять снимком доступности).
- Пример проверки состояния модели клиента — `tests/stage03/ui_password_model_check.js`.

## metaswarm

Плагин [metaswarm](https://github.com/dsifry/metaswarm) подключён как вспомогательный инструмент (настройка 2026-09-29, профиль — `.metaswarm/project-profile.json`). Его skills **не отменяют** правила `AGENTS.md` и этого файла: один этап за сессию, production только на чтение, приватность данных, внешнее ревью Codex. При конфликте приоритет у правил проекта.

- Команды: `/start-task` (`/start`), `/prime`, `/brainstorm`, `/review-design`, `/self-reflect`, `/pr-shepherd`; остальные — `/metaswarm:<skill>`.
- Тесты не требуются (решение владельца, 2026-09-29): coverage gate в `.coverage-thresholds.json` отключён; TDD и тестовые инструменты без запроса пользователя не добавлять.
- Codex (`.metaswarm/external-tools.yaml`): адаптер не передаёт `-m`, модель берётся из `~/.codex/config.toml`. Ревью этапа — только прямой командой из п. 4 «Завершения этапа». Делегировать Codex реализацию (`implement` = `--full-auto`: сеть и чтение `/data/itvolga/espo-private` не изолированы) — только с явного разрешения пользователя.
- Visual review (`/metaswarm:visual-review`, Playwright Chromium) — запасной вариант; основной — Playwriter (раздел выше). Правила ниже действуют для любого браузерного инструмента: можно снимать локальный стенд и production Vtiger `serv.itvolga.com` (разрешение пользователя, 2026-09-29).
  - На production — только просмотр: не сохранять формы, не запускать действия, массовые операции, рассылки, workflow и click-to-call. Служебные записи самого входа (история входов, сессия) — допустимое исключение из запрета записи.
  - Поля доступа контактов (`cf_1322`–`cf_1328`) не должны попадать на снимки: карточки и списки с ними не открывать или скрывать блок до снимка.
  - Скриншоты production и стенда с реальными данными — только в `/data/itvolga/espo-private/`; не в Git и не в `/tmp`. Учётные данные для входа — вне Git.
- База знаний `.beads/` — локальная, в Git не попадает; не записывать в неё значения строк, ПДн, реквизиты доступа и содержимое приватных отчётов.
- Pre-commit hook `.githooks/pre-commit` запускает `scripts/check-secrets.sh --history`; в новом клоне включить: `git config core.hooksPath .githooks`. `--no-verify` не использовать.
