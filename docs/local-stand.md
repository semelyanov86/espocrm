# Локальный стенд EspoCRM (этап 02)

Воспроизводимая установка EspoCRM **без Docker** на рабочей станции разработчика: ядро EspoCRM — в корне этого репозитория, собственная MySQL, собственный пул PHP-FPM, Apache vhost `crm.itvolga.test`, cron, health-check, локальные backup/restore. Проверено 2026-09-29 на Ubuntu 24.04 (результаты — `docs/migration/evidence.md`, раздел «Этап 02»).

## Быстрый старт

```bash
task stand:install        # установка/обновление (идемпотентно), в конце — health-check
task stand:health         # проверка стенда
```

Вход: **http://crm.itvolga.test**, пользователь `admin`, пароль — строка `ESPO_ADMIN_PASSWORD` в приватном файле `/data/itvolga/espo-private/stand/local.env` (генерируется при первой установке, права 600, в Git не попадает):

```bash
grep ESPO_ADMIN /data/itvolga/espo-private/stand/local.env
```

Сменить пароль: `task espo -- set-password admin` (спросит новый) и записать его в `ESPO_ADMIN_PASSWORD` — по нему health-check проверяет вход.

## Модель CRM (этап 03)

Код модели — модуль `custom/Espo/Modules/Itvolga` (+ `client/custom/modules/itvolga`), описание — `docs/migration/model.md`. После установки с нуля или изменения метаданных:

```bash
task model:apply          # clear-cache, rebuild, роли/команды/вкладки (itvolga-setup-acl), отметка времени клиента
task test:stage03         # приёмочные тесты модели и доступа на синтетических данных
task model:check          # сверка field-map.csv / relations.csv с метаданными
```

`model:apply` очищает кэш, поэтому до следующего запуска cron (≤ 1 мин) health-check сообщает `cron: last cron.php run … missing` — это ожидаемо.

Фирменный вид (D-127): логотип, фавиконка, футер «Центр информационных технологий» и страница входа приходят из модуля, поэтому видны сразу после `task model:apply` (клиент перечитывает их после `update-app-timestamp`, который входит в `model:apply`). Первичные настройки — название приложения, тема Light, без аватаров — `task stand:install` ставит только при первой установке (`ESPO_APPLICATION_NAME`, `ESPO_THEME` в `deploy/local/stand.conf`); дальше их меняют в «Настройках».

## Что устанавливается и где

| Компонент | Версия / значение | Где | Почему так |
|---|---|---|---|
| EspoCRM | 10.0.9 (последний релиз на 2026-09-29), архив с GitHub, sha256 закреплён | корень репозитория; список файлов ядра — `.espocrm-core` | «в этом каталоге»; в Git — только `custom/`, `client/custom/` |
| PHP | 8.5 (`php8.5`, `php-fpm8.5`; на production хосте — 8.5.4) | отдельный master `itvolga-espo-php-fpm.service`, пул `espocrm`, сокет `/run/itvolga-espo-php-fpm/espocrm.sock` | та же ветка PHP, что на production; EspoCRM 10 требует PHP 8.3–8.5 |
| MySQL | 8.4.11 (как на production), официальный generic tarball, sha256 закреплён, подпись GPG проверена | бинарники `/opt/itvolga-espo/mysql-8.4.11` (симлинк `/opt/itvolga-espo/mysql`), данные `/var/lib/itvolga-espo-mysql`, `127.0.0.1:3384`, сокет `/run/itvolga-espo-mysql/mysqld.sock`, `itvolga-espo-mysql.service` | системная MySQL рабочей станции — 8.0 (EOL); отдельный экземпляр не трогает чужие базы и перезапускается независимо |
| БД | `espocrm`, `utf8mb4_unicode_ci`; учётка `espocrm@127.0.0.1` (пароль — `DB_PASSWORD` в `local.env`); `root@localhost` — `auth_socket` (без пароля, только `sudo`) | | EspoCRM подключается только по TCP (параметра сокета нет); `sql_mode` глобально как на production |
| Apache | vhost `crm.itvolga.test` → `public/`, alias `/client/`, PHP → пул FPM | `/etc/apache2/sites-available/crm.itvolga.test.conf`, логи `/var/log/apache2/crm.itvolga.test-*.log` | схема из документации EspoCRM для production |
| Cron | `cron.php` каждую минуту от `espocrm`, параллельные задачи включены | `/etc/cron.d/itvolga-espo`, вывод — `journalctl -t itvolga-espo-cron` | |
| Пользователь | системный `espocrm` (nologin) — процессы PHP-FPM и cron | | данные CRM недоступны другим сайтам, работающим от `www-data` |
| Конфиги | отрендерены из шаблонов `deploy/local/templates/*.tmpl` | `/etc/itvolga-espo/{my.cnf,php-fpm.conf}`, `/etc/systemd/system/itvolga-espo-*.service` | в Git — только шаблоны без секретов |
| Секреты | `DB_PASSWORD`, `ESPO_ADMIN_USERNAME`, `ESPO_ADMIN_PASSWORD` | `/data/itvolga/espo-private/stand/local.env` (600), шаблон — `deploy/local/local.env.example` | вне Git; не экспортируются, передаются только нужной программе через stdin или окружение одной команды, не через argv |
| Backup | `db.sql.gz`, `files.tar.gz`, `table-counts.tsv`, `MANIFEST`, `SHA256SUMS` | `/data/itvolga/espo-private/stand/backups/<время>[-метка]/` (700/600) | содержат `config-internal.php` и данные — только приватно |

Все имена, пути, порты и версии — в `deploy/local/stand.conf`; любое значение переопределяется переменной окружения (`MYSQL_PORT=3390 task stand:install`).

## Требования

- Ubuntu 24.04+ (glibc ≥ 2.28), `sudo` без пароля для пользователя-разработчика (скрипты запускаются от него, привилегированные шаги — через `sudo -n`).
- Apache 2.4 с `rewrite`, `proxy`, `proxy_fcgi`, `setenvif` (включаются автоматически), `cron`.
- PHP 8.5 CLI и FPM с расширениями `bcmath ctype curl dom exif gd iconv json mbstring openssl pdo_mysql xml xmlwriter zip` (+ `pcntl posix` в CLI). На Ubuntu 24.04 PHP 8.5 ставится из PPA `ondrej/php`: `sudo apt install php8.5-cli php8.5-fpm php8.5-mysql php8.5-gd php8.5-zip php8.5-mbstring php8.5-curl php8.5-xml php8.5-bcmath`.
- `curl unzip rsync xz-utils python3 acl libaio1t64`.

Проверка требований — шаг `preflight`: при нехватке чего-либо установка останавливается со списком недостающего.

## Команды

| Команда | Что делает |
|---|---|
| `task stand:install` | все шаги: `preflight private user core perms mysql fpm espo apache cron health`; отдельные шаги — `task stand:install -- perms cron` |
| `task stand:health` | health-check; код возврата 1 при любой ошибке |
| `task stand:status` / `stand:start` / `stand:stop` | состояние; запуск; остановка (сначала запись cron и FPM с ожиданием процессов задач, затем MySQL) |
| `task stand:restart` | перезапуск MySQL и PHP-FPM, reload Apache, health-check |
| `task stand:logs` | журнал сервисов, ошибки vhost, последний лог EspoCRM |
| `task stand:backup -- [--label имя] [--online]` | локальный backup; по умолчанию cron и FPM приостанавливаются (≈1 с), `--online` — без остановки |
| `task stand:backups` | список backup |
| `task stand:restore -- <имя\|путь\|latest> [--yes] [--skip-custom] [--no-safety-backup]` | восстановление |
| `task stand:restore-cleanup` | удалить остатки неудачного restore (`espocrm__prev_*`, `espocrm__restore_*`, `.restore-aside-*`) после отката; health-check предупреждает о них |
| `task stand:uninstall -- --yes [--purge]` | удалить сервисы/vhost/cron/конфиги (только файлы с меткой шаблонов стенда); `--purge` — также данные MySQL (только каталог с меткой `.itvolga-espo-stand`), бинарники MySQL стенда, ядро и `data/` (только при наличии `.espocrm-core`), пользователя `espocrm` |
| `task espo -- <команда>` | консоль EspoCRM (`rebuild`, `clear-cache`, `app-check`, `run-job Cleanup`, `version`…) |
| `task espo:rebuild` | `clear-cache` + `rebuild` |
| `task db:shell` | MySQL-консоль базы `espocrm` от MySQL root |

**Не запускать `bin/command` напрямую:** его shebang `#!/usr/bin/env php` может выбрать другую версию PHP, а созданные файлы достанутся не тому пользователю. Только `task espo -- …` (`scripts/stand/espo.sh`).

## Что проверяет health-check

Сервисы (active + enabled); MySQL: версия, порт, `sql_mode`, число таблиц; EspoCRM: версия, `db:check`, `app-check`, `check-file-permissions` от `espocrm`; DNS `crm.itvolga.test`; HTTP: главная страница и её CSS, запрет `data/`, `application/`, `vendor/`, `custom/`, `install/`, файлов репозитория; API: аноним и неверный пароль → 401, вход как в браузере (пароль → токен + cookie секрета → запросы по токену), версия, системные требования глазами PHP-FPM (версия PHP, расширения, БД, права записи), выход (токен после выхода → 401); cron: запись в `/etc/cron.d`, версия `php` в `PATH` cron, давность последнего `cron.php`, успешные задачи за 15 мин, упавшие за сутки; права: `data/` = `espocrm:espocrm 770`, `config-internal.php` не читается `www-data`, пароли только в `config-internal.php`, ядро не изменяемо `espocrm`, приватный файл 600 / каталог 700; совпадение установленных конфигов с шаблонами Git; наличие backup. Секреты, токены и тела ответов не печатаются.

## Права

- **Ядро** (всё из `.espocrm-core`): установщик до записи проверяет, что каждый элемент ядра игнорируется `.gitignore` и не совпадает с файлом в Git; владелец — разработчик, `755/644`; `espocrm` не может его менять, поэтому обновления и расширения — только через скрипты, не через UI (загрузка расширений в UI отключена: `adminExtensionUpload=false`, решение D-03 — без платных пакетов).
- **`data/`**: `espocrm:espocrm`, `0770` — настройки с секретами, вложения, кэш, логи; прочие пользователи (включая `www-data` и разработчика) внутрь не попадают, чтение — через `sudo`.
- **`custom/Espo/Custom`, `custom/Espo/Modules`, `client/custom`** (в Git): владелец — разработчик; `espocrm` получает `rwX` через ACL, default ACL сохраняет общий доступ к новым файлам в обе стороны (Git и правки в UI EspoCRM работают без смены владельца).
- **Сокет FPM**: `www-data:www-data 0660` — к пулу обращается только Apache.

Повторно выставить права: `task stand:install -- perms`.

## Backup и restore

Backup: `mysqldump --single-transaction` своей MySQL 8.4 + архив `data/` (без `cache/` и `tmp/`) и каталогов кастомизаций + точные числа строк всех таблиц + `MANIFEST` (версии, git HEAD, кодировка БД) + `SHA256SUMS`. По умолчанию на время снятия (доли секунды) снимается запись cron, останавливается PHP-FPM и скрипт дожидается завершения процессов `espocrm` (включая параллельные задачи) — дамп, числа строк и файлы описывают одно состояние (`counts_exact=1`). С `--online` сервисы не останавливаются: дамп остаётся согласованным снимком, но числа строк сняты рядом с ним (`counts_exact=0`), и restore при их расхождении только предупреждает. Неудавшийся backup удаляется целиком.

Restore (`restore.sh`):
1. проверка `SHA256SUMS` и версии EspoCRM, страховочный backup текущего состояния (`…-pre-restore`);
2. приостановка cron и FPM, ожидание процессов задач;
3. импорт дампа во **временную БД** `espocrm__restore_<время>` и сверка чисел строк всех таблиц с backup (строгая для `counts_exact=1`) — повреждённый или несогласованный backup не трогает живую БД: restore прерывается, стенд продолжает работать как был;
4. подмена: живые таблицы → `espocrm__prev_<время>`, таблицы временной БД → `espocrm` (атомарный `RENAME TABLE`);
5. замена `data/` (и каталогов кастомизаций, если нет `--skip-custom`; при незакоммиченных изменениях в них restore отказывается), прежние каталоги — в `…/stand/.restore-aside-<время>`; права, реквизиты БД из текущего `local.env`, `rebuild`, cron;
6. ожидание первого `cron.php` и health-check. Только после успешной проверки удаляются `espocrm__prev_<время>` и `.restore-aside-<время>`. При любой ошибке после шага 4 cron и FPM остаются остановленными, прежние таблицы и каталоги сохраняются, а скрипт печатает команду отката (`restore.sh <…-pre-restore> --yes --no-safety-backup`).

Хранение backup не ограничено — лишние удалять вручную из `/data/itvolga/espo-private/stand/backups/`.

## Удаление и установка с нуля

```bash
task stand:uninstall -- --yes --purge   # всё, кроме файлов Git, local.env и backup
task stand:install                      # с нуля (скачает и сверит архивы заново)
task stand:restore -- latest --yes      # при необходимости вернуть данные
```

## Ограничения и заметки

- **Обновление EspoCRM не автоматизировано:** при смене `ESPO_VERSION` установщик останавливается. Порядок для будущего этапа: backup → новое ядро → `task espo -- migrate` → health-check (не проверено).
- Только HTTP; HTTPS и Basic Auth — как на production, на этапе 09.
- WebSocket и daemon не используются (фоновые задачи — cron + параллельные процессы); почта не настроена.
- Параллельные задачи EspoCRM (библиотека spatie/async) запускают дочерние процессы как `php` из `PATH`; поэтому cron и консоль получают `PATH` с shim `/opt/itvolga-espo/bin/php` → `php8.5`, а health-check проверяет версию. Системный `php` рабочей станции 2026-09-29 переключён на 8.5 (`php-switch 8.5`), но стенд от этого не зависит.
- Другие локальные сайты, работающие от `www-data` (mod_php), теоретически могут обратиться к FastCGI-сокету пула; прямого доступа к файлам `data/` у них нет. Для локального стенда риск принят; для production изоляция решается на этапе 09.
- Штатные задачи EspoCRM `Check for New Version`, `Check for New Versions of Installed Extensions`, `Sync Currency Rates` обращаются к внешним серверам раз в сутки; для production решить на этапе 09.
- Язык, часовой пояс, валюта и форматы (`ru_RU`, `Europe/Moscow`, `RUB`, `DD.MM.YYYY`, `HH:mm`) заданы при установке как предложение (D-37) и уточняются на этапе 03.
