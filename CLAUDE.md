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
AUDIT_TS=<метка> scripts/audit/run-audit.sh
scripts/audit/build-pii-hashes.sh          # обновить приватные хеши ПДн для проверки Git
scripts/check-secrets.sh --self-test       # самопроверка правил сканера
scripts/check-secrets.sh --history         # обязательная проверка перед каждым коммитом
task stand:install | stand:health          # локальный стенд EspoCRM (docs/local-stand.md)
task stand:backup | stand:restore -- latest --yes
task espo -- rebuild                       # консоль EspoCRM; bin/command напрямую не запускать
```

- `docs/migration/field-map.csv` и `relations.csv` **не редактировать вручную**: правила — `scripts/audit/mapping.py`, генерация — `scripts/audit/build_maps.py` из приватного прогона.
- Приватные результаты: `/data/itvolga/espo-private/` — читать можно, выводить содержимое строк нельзя, в Git не добавлять.

## Работа с production

- Только чтение; SQL — через `scripts/audit/lib.sh` (`remote_sql`, `remote_sql_py`: `SET SESSION TRANSACTION READ ONLY`), скрипты на сервер — inline, без файлов.
- Не выполнять широкие `find`/`cat` по серверу и не печатать исходники с данными: только адресные пути и `grep` по ключевым словам с маскированием.
- Поля доступа контактов (`Contacts.cf_1322`–`cf_1328`) и их история — только счётчики.

## Завершение этапа

1. Обновить `TASKS.md` (статус, проверки с датой, пути приватных отчётов без содержимого, стартовая команда следующего этапа) и затронутые `docs/migration/*`.
2. `scripts/check-secrets.sh --history` → 0 находок; `git diff --cached` — только безопасные артефакты.
3. Отдельный коммит (Conventional Commits, тело на английском); SHA — в итоговом ответе.
4. Внешнее ревью: закоммиченный результат отдать Codex `gpt-6-sol` в отдельном git worktree, read-only, без сети и без доступа к `/data/itvolga/espo-private`:
   `env -i HOME=$HOME PATH=$PATH codex exec -m gpt-6-sol --sandbox read-only --ephemeral -C <worktree> -o <review.md> - < prompt.md`.
   Каждое замечание проверить самостоятельно, исправить подтверждённые, записать итог в `docs/migration/evidence.md` и `TASKS.md`.
5. Остановиться: следующий этап — только в новой сессии; этапы 10 и 11 — только по отдельному явному разрешению пользователя.

## Стиль

- Общение и документация — на русском; код, идентификаторы, комментарии и сообщения коммитов — на английском.
- Непроверенное помечать явно («не проверено», `mapping_status=не проверено`, вопрос `Q-xx`); не выдавать предположения за факты.
