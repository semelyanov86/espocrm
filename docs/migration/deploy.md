# Развёртывание EspoCRM на сервере (этап 09)

Задание — промпт 09 (`git show 2052380:MIGRATION_PROMPTS.md`). Код — `deploy/ansible/` (роль `espocrm`, плейбуки
`11-espocrm.yml` и `12-crm-switch.yml`, патч общих файлов `/data/server`); порядок этапов 10–11 и откат —
`cutover.md`; решения — D-180…D-188; проверки — `evidence.md`, «Этап 09». Production и `/data/server` на этапе 09 только
читались.

## 1. Где код и как он попадёт на сервер (D-180)

Ansible сервера живёт в `/data/server/ansible` (роли apache, php, php_docker, mysql, vtiger, lahic, backup, asterisk,
fail2ban…). До этапа 10 он только читается, поэтому развёртывание подготовлено как **наложение** на его коммит
`deploy/ansible/SERVER_BASE` (`ed38172`):

- новое — роль `roles/espocrm/`, плейбуки `11-espocrm.yml` (развёртывание и health-check) и `12-crm-switch.yml`
  (переключение `serv.itvolga.com`); оба не входят в `site.yml`, как `09-certs.yml` и `10-backup.yml`;
- общие файлы сервера — `deploy/ansible/server-ansible.patch` (18 файлов): переключатель `itvolga_crm_primary` и
  `enabled` у vhost Vtiger (`vars.yml`), секреты EspoCRM в `vault.yml.example`, флаг `enabled` роли apache, флаг
  `vtiger_cron_disabled` роли vtiger, тир `recordings` и ночной пакет EspoCRM роли backup, задачи Taskfile, таблицы
  `CLAUDE.md` сервера.

`task ansible:overlay` собирает чистый клон `/data/server` + роль + плейбуки + патч в `build/ansible-overlay` (в клоне нет
`vault.yml` и `.vault_pass` — они вне Git сервера); на нём выполняются собственные `task ansible:lint` и
`task ansible:syntax` сервера. На этапе 10 (с разрешения владельца) — `scripts/deploy/overlay.sh install --stage10`
(копирует роль и плейбуки, применяет патч в `/data/server`; требует чистое дерево на базе патча), затем коммит в
`/data/server`.

## 2. Что ставит роль

| Компонент | Значение | Где | Почему так |
|---|---|---|---|
| Ядро EspoCRM | 10.0.9, zip релиза GitHub, sha256 закреплён (тот же, что на стенде) | `/opt/espocrm/releases/EspoCRM-10.0.9/` → rsync в `/var/www/espocrm` (root, 755/644); отметка `.espocrm-core` | правка ядра на сервере — дрейф: `--check` его показывает, прогон возвращает; другая версия в отметке — остановка (обновление не автоматизировано) |
| Модуль Itvolga | `git archive` **коммита** `espocrm_module_ref` (по умолчанию `HEAD`) репозитория миграции на контроллере | `/opt/espocrm/module/<коммит>/` (маркер завершения распаковки `<коммит>.complete`) → rsync `--checksum` в `custom/Espo/Modules/Itvolga`, `client/custom/modules/itvolga` (root); отметка `.itvolga-module` | на сервер попадает только закоммиченное; EspoCRM не может менять, переименовать или подменить код модуля (родители — `root:espocrm 1775`) |
| PHP | **8.5** нативный (роль php: `php8.5-*`, на production 8.5.4); свой мастер `espocrm-php-fpm.service`, пул `espocrm` от пользователя `espocrm`, сокет `/run/espocrm-php-fpm/espocrm.sock` (www-data 0660) | `/etc/espocrm/php-fpm.conf` | рестарт EspoCRM не трогает `php8.5-fpm` (Firefly, Mautic) и `php74-fpm` (Vtiger, Lahic — PHP 7.4 в Docker остаётся как есть); `php` в PATH cron и консоли — shim `/opt/espocrm/bin/php` → `php8.5` (D-35) |
| Пользователь | системный `espocrm` (nologin) | | данные CRM недоступны сайтам www-data |
| БД | `espocrm`, `utf8mb4_unicode_ci` на общем MySQL 8.4 (роль mysql); `espocrm@127.0.0.1`, `caching_sha2_password`, права только на свою БД | | EspoCRM ходит по TCP; пароль ставится при создании (`espocrm_db_login_update: on_create`), смена — `-e espocrm_db_login_update=always` |
| Каталоги записи | `data/` (espocrm 0770; `data/upload`, `data/logs` создаются сразу — урок этапа 08), `custom/Espo/Custom` (espocrm 0770), `custom/Espo/Modules` и `client/custom` (`root:espocrm 1775`: запись через группу, sticky-бит) | | `check-file-permissions` ядра проверяет верхний уровень этих четырёх; код модуля внутри — root, переименовать его `espocrm` не может |
| Cron | `cron.php` каждую минуту от `espocrm`, вывод — `journalctl -t espocrm-cron` | `/etc/cron.d/espocrm` | как стенд; backup/restore паркуют файл как `espocrm.paused` |
| Vhost | `/etc/apache2/sites-available/espocrm.conf` (ссылка в `sites-enabled`): `public/` + alias `/client/`, остальное корня недоступно, PHP — в свой пул | | схема документации EspoCRM, как на стенде |
| Телефония | настройки EspoCRM (корень записей, правила, учётки AMI) — всегда; живая интеграция (`espocrm_telephony_enabled`) — пользователи AMI `manager.d/itvolga-espo.conf` (root:asterisk 0640, `manager reload` без рестарта), служба `espocrm-telephony` | §6 | прослушивание истории работает и без живой интеграции |
| fail2ban | jail `espocrm-auth`: отдельный журнал входа `espocrm_auth.log` (только `/api/v1/App/user`, с `X-Status-Reason`), 401 кроме `second-step-required` (верный пароль учётки с 2FA), 8 за 10 мин → бан на час | `/etc/fail2ban/{filter.d/espocrm-auth.conf,jail.d/espocrm.local}` | `ignoreip` роли fail2ban (офис, VPN) действует; обычный журнал `combined` не меняется |
| Инструменты | `espocrm`, `espocrm-config`, `espocrm-apply`, `espocrm-backup`, `espocrm-restore`, `espocrm-restore-check`, `espocrm-health`, `espocrm-fingerprint`, `espocrm-changes-since` | `/usr/local/sbin` (root 0750), библиотеки — `/usr/local/lib/espocrm`, настройки без секретов — `/etc/espocrm/espocrm.env` | §7 |

Секреты — только vault сервера (`vault.yml.example` патча): `vault_db_espocrm_password` (≥ 16),
`vault_espocrm_admin_password` (≥ 12), `vault_espocrm_ami_listener_secret`, `vault_espocrm_ami_dialer_secret` (16–200
символов из `A-Z a-z 0-9 ._~+=@%^*!-` — секрет попадает в `manager.d` как есть, а `;` начинает комментарий Asterisk); MySQL root — существующий `vault_mysql_root_password`. Роль проверяет их до любых изменений; в задачах с
ними — `no_log`, в argv их нет (stdin помощников). На сервере секреты лежат там же, где у ядра: `data/config-internal.php`
(БД) и `/etc/espocrm/telephony.json` (0600 root, учётки AMI).

## 3. Кто обслуживает `serv.itvolga.com` (D-181, D-182)

Отдельного имени у EspoCRM нет (решение владельца 2026-10-17). Один переключатель в `vars.yml` сервера:

| `itvolga_crm_primary` | `serv.itvolga.com` | EspoCRM | Vtiger |
|---|---|---|---|
| `vtiger` (до переключения) | Vtiger (vhost роли apache, Basic Auth) | только `https://serv.itvolga.com:8443` на `127.0.0.1` (SSH-туннель владельца, health-check) | работает, cron активен |
| `maintenance` (окно) | страница 503 «CRM переезжает» (`Retry-After`), ACME доступен | `127.0.0.1:8443` | vhost выключен, cron закомментирован (ожидание идущего `vtigercron.php`) |
| `espocrm` (после) | EspoCRM | и `127.0.0.1:8443` | vhost выключен, cron закомментирован; файлы, БД, docroot в `php74-fpm`, роли — остаются |

Смена: правка `vars.yml` → коммит → `task crm:switch` (`12-crm-switch.yml`: роли apache и espocrm приходят к одному
состоянию, `apache2ctl -t`, **один** reload в конце play, `force_handlers`, безусловный reload после прерванного
прогона; затем `espocrm-health`). Откат — вернуть значение и тот же запуск. `siteUrl` EspoCRM до переключения —
`https://serv.itvolga.com:8443`, после — `https://serv.itvolga.com`: RP ID ключей безопасности — имя хоста без порта,
поэтому ключи, зарегистрированные через туннель, действуют и после переключения.

Сертификат — уже выпущенный для Vtiger `serv.itvolga.com` (роль certbot, `09-certs.yml`): vhost-превью на 8443 и
публичный vhost EspoCRM используют его; продление (`--webroot`) обслуживают `:80` того vhost, которому принадлежит имя.

## 4. Вход без HTTP Basic Auth (D-183)

Клиент EspoCRM в каждом запросе API шлёт собственный `Authorization: Basic <логин:токен>` (`client/lib/espo-main.js`,
`setupAjax`): Apache с Basic Auth сверил бы его с htpasswd и ответил 401 — EspoCRM за обычной Basic Auth не работает.
Решение владельца 2026-10-17 — согласованная замена: **без Basic Auth**, вход EspoCRM + обязательная 2FA. Роль держит:
`auth2FA`, `auth2FAForced`, методы `Totp` и `ItvolgaSecurityKey`, ограничение неудачных попыток по имени пользователя
(`authUsernameFailedAttemptsLimitEnabled`; по IP — ядро, 10 за 60 с), сложность пароля (10 символов, цифра, оба
регистра), jail fail2ban. Ядро требует 2FA только от обычных пользователей: администраторы включают её сами
(`espocrm-health` предупреждает «admin без 2FA»). Анонимный API — 401, служебные пути (`data/`, `application/`,
`vendor/`, `custom/`, `install/`, отметки роли) — 403/404 (проверяет health-check).

## 5. Настройки как код (D-184, D-185)

Каждый прогон роли сравнивает и, если отличаются, пишет (`espocrm-config set` — значения через stdin, в ответе только
имена): блок `database` (реквизиты из vault), `siteUrl` режима, `useWebSocket=false`, `jobRunInParallel=true`,
`adminExtensionUpload=false`, `adminUpgradeDisabled=true`, 2FA и пароли (§4), `defaultPermissions` = `espocrm`,
`cleanupDeletedRecords=false` (до последней дельты, D-185), `itvolgaSecurityKeyRpId` (если задан). В `--check` то же
сравнение без записи (`diff`) — дрейф виден. Правка этих настроек в интерфейсе откатится следующим прогоном. Первичная
установка (`files/install.sh`) — последовательность стенда (`config:populate`, `defaultPermissions`, реквизиты, `rebuild`,
администратор, язык Russian/пояс Europe/Moscow/RUB/формат дат стенда, задания, `app-check`, `isInstalled` последним).

Применение модуля (`espocrm-apply` — команды `task model:apply` стенда: `clear-cache`, `rebuild`, `itvolga-setup-acl`,
`itvolga-setup-finance`, `itvolga-finance-settle --silent`, `itvolga-setup-reports`, `update-app-timestamp`, reload
PHP-FPM, рестарт работающего слушателя) — когда последнее успешно применённое состояние (`/var/lib/espocrm/apply-applied`:
ядро + коммит модуля) отличается от развёрнутого, и после исправления дрейфа файлов (`apply-pending`): прерванный
прогон применится следующим. Рестарты PHP-FPM, слушателя и `manager reload` — задачами роли, не обработчиками: в роли
нет `flush_handlers`, Apache перечитывает конфигурацию один раз в конце play. Пароль администратора ставится при установке; после restore пакета
стенда (он приносит своего администратора) — разово `-e espocrm_admin_reset=true`.

## 6. Телефония (этап 07.1, D-171)

- Корень записей `/var/spool/asterisk/monitor` (asterisk:asterisk 0750) — ACL `u:espocrm:rx` и default ACL; родитель
  `/var/spool/asterisk` на production — `asterisk:root 0750` (проверено только чтением 2026-10-17), поэтому ещё ACL
  **только прохода** `u:espocrm:--x` на нём (ACL одного корня, как в примере этапа 07.1, не дал бы дойти до файлов).
  На сервере нет пакета `acl` (setfacl, проверено 2026-10-17) — роль его ставит.
- `/etc/espocrm/telephony.json` (0600 root) → `itvolga-setup-telephony` (stdin), когда sha256 файла отличается от последнего
  применённого (`/var/lib/espocrm/telephony-applied`); после этого — рестарт слушателя (правила и учётки он читает только
  при старте); запасной внутренний номер `108` — только если в EspoCRM он не задан.
- `espocrm_telephony_enabled: true` — файл пользователей AMI (рендер = `deploy/production/telephony/manager.d-itvolga-espo.conf.example`
  с секретами vault; проверено побайтно на проверочной машине), `manager reload`, служба слушателя (автозапуск),
  самопроверка прав `--check`. `false` — файла нет, служба остановлена, интеграция в EspoCRM выключена.

## 7. Инструменты на сервере

| Команда (root) | Что делает |
|---|---|
| `espocrm <команда>` | консоль EspoCRM от `espocrm` с PHP 8.5 и чистым окружением (не `bin/command`) |
| `espocrm-config set\|diff\|get` | настройки без значений в argv (`get` — только root: может вернуть секреты) |
| `espocrm-health` | службы; версия, `db:check`, `app-check`, права записи; настройки §4–5; HTTP через `127.0.0.1` с SNI сайта и проверкой цепочки (превью всегда, публичный vhost — в режимах `maintenance`/`espocrm`); вход администратора (если переданы `HEALTH_USER`/`HEALTH_PASSWORD`; ответ «нужен второй шаг» 2FA засчитывается); переключатель vhost; cron и задания; права (`data/` 770, `config-internal.php` недоступен www-data, код неизменяем для `espocrm` — через `access(2)`); записи разговоров (чтение файла) и файлы записей у звонков; слушатель; ночной пакет ≤ 26 ч; срок сертификата; остатки restore |
| `espocrm-backup [--label L] [--online]` / `--nightly` | пакет (§8) |
| `espocrm-restore <пакет\|имя\|nightly> [--yes] [--server-config F]` | восстановление (§8) |
| `espocrm-restore-check [пакет] [--from-restic] [--recordings] [--mysql <БД>]` | практическая проверка восстановления без касания живой системы (§8) |
| `espocrm-fingerprint take L \| diff A B` | отпечаток: алгоритм `scripts/stand/fingerprint.py` (CHECKSUM TABLE без журналов, sha256 файлов `data/upload`) — дайджест стенда и production сравнимы |
| `espocrm-changes-since '<UTC>' \| --against <пакет> [--export]` | для отката (D-188): по времени — созданное/изменённое/удалённое после момента в таблицах с отметками времени; `--against` — полное сравнение с пакетом момента переключения во временной БД (добавленное, удалённое, связи «многие-ко-многим», смена флага удаления, изменённое); счётчики по таблицам, `--export` — приватный TSV на сервере |

Блокировка `/run/lock/espocrm-ops.lock`: одновременно идёт одна операция backup/restore/проверки; роль не запускается во
время неё (проверка без создания файла).

## 8. Backup и восстановление (D-186)

- **Формат пакета** — как у стенда (`scripts/stand/backup.sh`): `db.sql.gz` (mysqldump `--single-transaction`),
  `files.tar.gz` (`data/` без `cache`/`tmp`, `custom/Espo/{Custom,Modules}`, `client/custom`), `table-counts.tsv`,
  `MANIFEST` (+ `origin=production`, `host`; `git_head` — коммит модуля), `SHA256SUMS`. По умолчанию слушатель, cron и
  PHP-FPM приостановлены на секунды (`counts_exact=1`). Пакеты — `/var/backups/espocrm/bundles/` (700/600).
- **Ночной пакет** — хук тира `db` роли backup (`backup_db_pre_hooks`, после `mysqldump` всех БД, 02:30):
  `espocrm-backup --nightly` → `/var/backups/espocrm/nightly` без сжатия (restic сжимает и дедуплицирует), предыдущий —
  `nightly.prev`. Сбой хука не останавливает дампы и restic остальных БД: тир завершается ошибкой в конце (письмо).
  Живой `data/` исключён из тира `system` (код `/var/www/espocrm` в нём остаётся). Дамп `espocrm` попадает и в общий
  `mysqldump` тира — дублирование дедуплицирует restic.
- **Записи разговоров** — новый тир `recordings` (`/var/spool/asterisk/monitor` и `/var/log/asterisk/cdr-csv`,
  ежедневно 03:15, гибрид, `--keep-daily 14 --keep-weekly 8 --keep-monthly 24`); сам CDR — БД `asteriskcdrdb` тира `db`.
  На 2026-10-17 записи — 187 файлов, 1,3 ГБ.
- **Восстановление** `espocrm-restore` — порт `scripts/stand/restore.sh`: проверка SHA256SUMS и версии; блокировка и
  остановка писателей **до** страховочного пакета `pre-restore` (он снимается под той же блокировкой и описывает ровно
  заменяемое состояние); сохранение серверных ключей конфигурации — `database`, `itvolgaTelephony*`, включая запасной
  внутренний номер (у тестовой АТС стенда 119, на production 108); отсутствующий ключ после restore удаляется; после
  сбоя живая конфигурация может отсутствовать или быть чужой, поэтому откат получает файл неудачного прогона
  (`--server-config`); импорт во временную БД и сверка чисел строк (строго для `counts_exact=1`), атомарный
  `RENAME TABLE`, замена `data/` (и для пакета этого сервера — `custom/Espo/Custom`, `client/custom` кроме модуля; модуль
  никогда не берётся из пакета), возврат серверных ключей и настроек роли (`/etc/espocrm/settings.json`), `rebuild`,
  запуск PHP-FPM, cron и слушателя (в каком бы состоянии их ни оставил прежний сбой), `espocrm-health`; прежние таблицы и
  каталоги удаляются только после успешной проверки, иначе печатается команда отката (с `--server-config`). `cryptKey`,
  `passwordSalt`, `hashSecretKey` берутся **из пакета**: ими зашифрованы пароли `ContactAccess`. Проверено на
  проверочной машине: сбой распаковки после замены таблиц → напечатанный откат → отпечаток = состоянию до сбоя.
- **Практическая проверка** `espocrm-restore-check`: дамп пакета — во временную БД `espocrm__check_<время>`
  (`sql_log_bin=0`, удаляется), числа строк = записи пакета, файлов в архиве = MANIFEST, у каждой строки вложения есть файл
  (не меньше, чем в живой системе), выборка до 20 файлов побайтно равна живым; `--from-restic` — тот же ночной пакет из
  последнего снимка тира `db` (путь DR); `--recordings` — последний снимок тира `recordings` во временный каталог,
  каждый файл сравнивается с живым (размер и sha256); `--mysql vtiger7` — дамп Vtiger из тира `db` во временную БД,
  набор таблиц = живой (числа строк расходятся только на работу после дампа — счётчик). Отчёт — счётчики,
  `/var/backups/espocrm/checks/<время>.json`.

## 9. Проверка на одноразовой машине (этап 09)

`task ansible:test` (`scripts/deploy/test-target.sh`, `deploy/ansible/tests/`): контейнер Ubuntu 26.04 (digest образа
тестовой АТС стенда) с systemd; роли сервера **без изменений** — php, mysql, apache, fail2ban, backup (rclone — локальный
remote вместо Mail.ru), фикстуры — сертификат `serv.itvolga.com` от тестового CA, Asterisk архива Ubuntu с AMI как на
production, синтетические WAV, страница-маркер и cron Vtiger; vault — случайные значения по `vault.yml.example`
(`build/ansible-test`, 600). Шаги: роль дважды (`changed=0`), `--check --diff` (`changed=0`), сценарий backup →
изменение → restore (отпечаток = отпечатку пакета) → проверки пакета и restic `db`/`recordings` → пакет «формата стенда»,
телефония (права AMI, слушатель, повтор `changed=0`, выключение), переключение `maintenance` → `espocrm` → `vtiger` (каждое
дважды, `changed=0`). Итоги и найденные дефекты — `evidence.md`, «Этап 09».

## 10. Ограничения и не проверено

- Не проверено на production (этап 09 его не меняет): выпуск и продление сертификата для этого vhost, объёмы данных
  production, restic в Облако Mail.ru, соседство с `php74-fpm` (контейнер PHP 7.4 в проверку не входит), бан fail2ban
  (jail загружается, фильтр проверен `fail2ban-regex`, срабатывание бана не моделировалось), пакет production → `scripts/stand/restore.sh` стенда (формат тот
  же по построению; проверить на этапе 10 до окна, `cutover.md`).
- Обновление EspoCRM не автоматизировано: другая версия в `.espocrm-core` останавливает роль.
- Исходящая почта EspoCRM (рассылка отчётов, сброс пароля) не настроена — Q-55; живая телефония до переключения — Q-56.
- `htpasswd` роли apache требует `python3-passlib` на сервере (есть на production; на проверочной машине — фикстура).
- `/usr/bin/test` Ubuntu 26.04 — `rust-coreutils` (на production тот же пакет, `dpkg -S`, только чтение 2026-10-17):
  `test -r/-w` не учитывает ACL (проверено на проверочной машине: `ls` каталога записей от `espocrm` работает, `test -r`
  отвечает «нет») — проверки прав в инструментах роли идут через `access(2)`.
