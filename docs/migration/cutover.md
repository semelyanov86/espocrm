# Runbook: размещение рядом с Vtiger (этап 10), переключение (этап 11) и откат

Подготовлено на этапе 09 (2026-10-17). Каждый шаг этапов 10 и 11 выполняется **только после отдельного явного разрешения
владельца** (`AGENTS.md`); до него production и `/data/server` только читаются. Код и его контракт — `deploy.md`, решения —
D-180…D-193, проверки этапа 09 — `evidence.md`, «Этап 09». **Этап 10 выполнен 2026-10-18** (§1.7, `evidence.md`,
«Этап 10»); §2 — план окна этапа 11 с временами, измеренными на этапе 10. Команды `task …` без пометки — этого репозитория; «сервер:» —
Taskfile `/data/server` (после установки наложения); «на сервере:» — `ssh sergey@serv.sergeyem.ru`, затем `sudo …`.

## 0. Принципы

- `serv.itvolga.com` принадлежит одной системе: переключатель `itvolga_crm_primary` (`vtiger` → `maintenance` →
  `espocrm`) в `vars.yml` сервера, применение — сервер: `task crm:switch` (D-181). Откат — то же значение назад.
- Импорт и сверка — **на стенде** (как репетиция 08); на production приходит проверенное состояние пакетом backup через
  `espocrm-restore`, равенство подтверждает отпечаток (стенд `task stand:fingerprint` = сервер `espocrm-fingerprint`,
  D-187). Перед последней дельтой — обратный путь production → стенд, чтобы сохранить сделанное в EspoCRM до
  переключения (пароли, 2FA, ключи безопасности, настройки).
- Без HTTP Basic Auth: вход EspoCRM + обязательная 2FA (D-183). Ключи безопасности, зарегистрированные через туннель
  `:8443`, действуют и после переключения (RP ID = `serv.itvolga.com`, D-182).
- Vtiger, PHP 7.4/`php74-fpm`, cron Vtiger (закомментирован), БД `vtiger7`, файлы и роли **не удаляются**; удаление —
  отдельное решение после периода проверки.
- `cleanupDeletedRecords` EspoCRM включён (решение владельца, D-185); исходящая почта EspoCRM — сервер Vtiger (D-189); живая
  телефония — с этапа 10 (D-190).

## 1. Этап 10 — EspoCRM рядом с Vtiger

### 1.1 Перед изменениями (только чтение)

```bash
source scripts/audit/lib.sh && remote_sh 'stat -c "%n %U:%G %a" /var/spool/asterisk /var/spool/asterisk/monitor;
  command -v setfacl || echo "no acl"; php8.5 -m | grep -c -E "^(bcmath|intl|pdo_mysql|sodium|zip|gd)$";
  df -h / | tail -1; systemctl list-timers --no-legend "backup-*" | wc -l'
scripts/deploy/overlay.sh status            # база патча = HEAD /data/server, иначе — перенести патч на новую базу
```
Ожидание (2026-10-17): `/var/spool/asterisk` `asterisk:root 750`, `monitor` `asterisk:asterisk 750`, `no acl`, 6
расширений, свободно ≥ 700 ГБ, 5 таймеров. Q-54: `send_recording_wrapper.sh` не переносит и не перекодирует WAV, шаблоны
`phones-out` не менялись.

### 1.2 Свежие backup и практическое восстановление Vtiger

```bash
# сервер:
task backup:run tier=db && task backup:run tier=system
task restore:db name=vtiger7        # дамп из restic → /var/backups/restore/var/backups/mysql/vtiger7.sql
# на сервере: дамп во временную БД без binlog, сравнение набора таблиц с живой, удаление
sudo mysql -e 'CREATE DATABASE vtiger7__check'
sudo mysql --init-command='SET SESSION sql_log_bin=0' vtiger7__check < /var/backups/restore/var/backups/mysql/vtiger7.sql
sudo mysql -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='vtiger7__check'"   # = vtiger7
sudo mysql -e 'DROP DATABASE vtiger7__check' && sudo rm -rf /var/backups/restore/var
```
После 1.4 то же одной командой: `sudo espocrm-restore-check --mysql vtiger7`.

### 1.3 Код в `/data/server`, секреты, роль backup

```bash
scripts/deploy/overlay.sh install --stage10    # роль + плейбуки + патч в /data/server (чистое дерево на базе патча)
cd /data/server && task ansible:lint && task ansible:syntax && git diff --stat   # 0 нарушений; 5 плейбуков
task vault:edit    # vault_db_espocrm_password (≥16), vault_espocrm_admin_password (≥12),
                   # vault_espocrm_ami_listener_secret, vault_espocrm_ami_dialer_secret (16–200 печатных ASCII)
git commit …       # в /data/server
task ansible:backup                     # тир recordings, хук ночного пакета EspoCRM (пока пропускается)
task backup:run tier=recordings         # первый снимок записей (~1,3 ГБ)
```

### 1.4 Развёртывание EspoCRM

```bash
C=$(git -C /data/itvolga/espo rev-parse HEAD)     # коммит модуля = коммит, с которым пройдёт импорт на стенде
T0=$(date -u '+%F %T')                            # момент развёртывания (UTC): с него слушатель пишет звонки
cd /data/server && task ansible:espocrm -- -e espocrm_module_ref=$C   # живая телефония и почта Vtiger — по умолчанию роли
```
Ожидание: health — 0 FAIL (предупреждения: администратор без 2FA, ночного пакета ещё нет; «outgoing mail: configured: True,
port 465, SSL»; слушатель телефонии `connected`); `serv.itvolga.com` — по-прежнему
Vtiger; EspoCRM — `https://serv.itvolga.com:8443` только на `127.0.0.1`. Повтор `task ansible:espocrm` — `changed=0`;
`task ansible:espocrm-check` — `changed=0`. На проверочной машине первый прогон — 1 мин 3 с плюс ожидание cron.

### 1.5 Данные: импорт на стенде и перенос

```bash
task snapshot:create && task snapshot:verify -- <S>                        # 19/19
task stand:backup -- --label pre-stage10
task stand:restore -- 20260929T232413-pre-restore --yes --skip-custom      # чистая установка (rehearsal.md, шаг 3)
test "$(git rev-parse HEAD)" = "$C" && task model:apply && task telephony:up && task telephony:down   # стенд — на коммите C
task espo -- config:get itvolgaTelephonyFallbackExtension                  # 108 = production (D-192), иначе импорт CDR неверен
task import:run -- --snapshot <S>                                          # проблем 0, проверка — все equal
task stand:fingerprint -- take pre-repeat && task import:run -- --snapshot <S> && task stand:fingerprint -- take post-repeat
task stand:backup -- --label for-production                                # пакет с остановленными писателями
task stand:fingerprint -- take for-production                              # дайджест D
scripts/deploy/bundle.sh push <пакет for-production>
# на сервере:
sudo espocrm-restore /var/backups/espocrm/bundles/<пакет> --yes --carry-calls-from "<T0>"   # health в конце
sudo espocrm-fingerprint take after-transfer     # = D, если с T0 звонков не было; иначе — сравнить по таблицам (ниже)
# сервер:
task ansible:espocrm -- -e espocrm_module_ref=$C -e espocrm_admin_reset=true
```
Звонки, которые слушатель записал с `T0`, restore сохраняет до замены БД и возвращает до своего запуска (D-191): звонок,
который пакет уже содержит из истории CDR снимка (тот же `cAsteriskLinkedId`), пропускается — побеждает проверенный
импорт; restore печатает «put back: N; skipped: M». Отпечаток тогда отличается от D только таблицами `call`,
`call_user`, `call_contact`, `call_lead`, `entity_team` (`espocrm-fingerprint diff`). Записи разговоров не переносятся:
звонки хранят путь относительно корня, на сервере это оригиналы (`espocrm-health`: «N calls with a recording, 0 files
missing»).

### 1.6 Интерфейс, обратный путь, backup

- Интерфейс: `ssh -L 8443:127.0.0.1:8443 sergey@serv.sergeyem.ru`, отдельный Chrome
  `--host-resolver-rules="MAP serv.itvolga.com 127.0.0.1" --user-data-dir=<scratchpad>` → `https://serv.itvolga.com:8443/`;
  сценарии этапа 08 (реальные данные — только признаки DOM и коды).
- Проба обратного пути (до окна): сервер `task espocrm:backup label=roundtrip-test` → `scripts/deploy/bundle.sh pull <имя>`
  → `ESPO_HEALTH_LOGIN=0 task stand:restore -- <имя> --yes --skip-custom` (пакет несёт администратора production — его
  пароль и 2FA: вход health стенда пропускается; почту production restore стенда выключает сам до запуска PHP-FPM и cron —
  SMTP системы очищен, у ящиков `EmailAccount`/`InboundEmail` выключены отправка и получение, их значения — в приватном
  файле до `unpark`, D-189) → `scripts/deploy/stand-admin.sh park` (хеш пароля и 2FA
  администратора — в приватный файл, стенду — пароль `local.env` без 2FA: импорт скачивает файлы как администратор) →
  `task telephony:up && task telephony:down` → `task import:run -- --snapshot <S> --check-only` (все equal) →
  `scripts/deploy/stand-admin.sh unpark` (администратор и ящики — обратно; отпечаток стенда = до `park`, проверено
  2026-10-17) → стенд вернуть
  `task stand:restore -- <for-production> --yes --skip-custom`. Проверочный проход здесь — **обязательная** проверка
  переноса: на этапе 10 он нашёл 17 звонков CDR с запасным номером тестовой АТС (D-192).
- Backup: сервер `task backup:run tier=db` (хук → `/var/backups/espocrm/nightly`), `task backup:run tier=recordings`,
  `task espocrm:restore-check` (ночной пакет из restic + записи) и на сервере `sudo espocrm-restore-check --mysql vtiger7`.
- Vtiger остаётся системой записи; пользователи EspoCRM не видят.

### 1.7 Выполнено 2026-10-18

Подробно — `evidence.md`, «Этап 10»; приватные пути — `TASKS.md`.

| Шаг | Результат | Время |
|---|---|---|
| 1.1 Проверки только чтением | как ожидалось; Q-54 закрыт (WAV не переносятся, `phones-out` = стенду) | — |
| 1.2 Backup и восстановление Vtiger | тиры `db`, `system` — код 0; дамп `vtiger7` из restic во временной БД = живой (784 таблицы, 197 076 строк) | 1 мин 15 с + 38 с |
| 1.3 Наложение, vault, роль backup | `/data/server` `a6508c1`; 4 секрета; тир `recordings` — 1,302 ГиБ, в облаке | 31 с (первый снимок) |
| 1.4 Развёртывание | `e698dab`, changed=51, health 0 FAIL; повтор и `--check --diff` — changed=0; Vtiger, `php74-fpm`, Asterisk не перезапускались | 2 мин 30 с |
| 1.5 Снимок, импорт, перенос | снимок `20261018T091226` 19/19; импорт — 7321 создано, 7323 `equal`, проблем 0, повтор — 0 записей; пакет → `espocrm-restore` → **отпечаток = стенду** | снимок 2 мин 20 с; импорт 1 мин 37 с; push 21 с; restore 1 мин 15 с |
| 1.6 Интерфейс, обратный путь, backup | сценарии администратора на production — все признаки; ACL ролей — на стенде с теми же данными; обратный путь: первый — 17 расхождений `cExtension` → исправлено (D-192), импорт и перенос повторены (отпечаток `d4a4b661092f5369`), второй — 7323 `equal`; ночной пакет из restic и записи — 0 FAIL | обратный путь 113 с |

## 2. Этап 11 — окно переключения

Накануне: объявить окно; убедиться, что `backup-db`, `backup-system`, `backup-recordings` прошли этой ночью,
`task espocrm:restore-check` и `espocrm-restore-check --mysql vtiger7` — 0 FAIL; стенд и сервер на коммите `C`.

| # | Шаг | Команды | Оценка |
|---|---|---|---|
| 1 | Запись в Vtiger остановлена | `vars.yml`: `itvolga_crm_primary: maintenance` → коммит → сервер `task crm:switch` (vhost Vtiger выключен, страница 503, cron Vtiger закомментирован, ожидание идущего `vtigercron.php`) | 1–3 мин |
| 2 | Финальный снимок | `task snapshot:create && task snapshot:verify -- <F>` | ≈ 2–5 мин (транзакция ≈ 6 с, файлы ≈ 1,4 ГиБ, проверка) |
| 3 | Production → стенд | сервер `task espocrm:backup label=pre-delta` → `scripts/deploy/bundle.sh pull <имя>` → `ESPO_HEALTH_LOGIN=0 task stand:restore -- <имя> --yes --skip-custom` → `scripts/deploy/stand-admin.sh park` → `task telephony:up && task telephony:down` | ≈ 3 мин (restore стенда ≈ 70 с) |
| 4 | Дельта и контроль | `task import:run -- --snapshot <F>`: проблем 0, проверка — все `equal`, удаления в пределах предохранителя `max(25, 5 %)`; деньги, налоги, файлы, звонки — `report.json`; `task import:summary -- <прогон>` | ≈ 2 мин |
| 5 | Стенд → production | `scripts/deploy/stand-admin.sh unpark` (пароль и 2FA администратора production, ящики почты — обратно) → `task stand:backup -- --label cutover` → `task stand:fingerprint -- take cutover` (D′) → `bundle.sh push` → на сервере `sudo espocrm-restore …/<cutover> --yes --carry-calls-from <pre-delta>` (звонки, которые слушатель записал после пакета шага 3, — сохранены до замены и возвращены до запуска слушателя, D-191; «put back: N; skipped: 0») → `sudo espocrm-fingerprint take cutover` = D′ при N = 0, иначе отличие только в таблицах звонков | ≈ 5 мин |
| 6 | Переключение | `vars.yml`: `itvolga_crm_primary: espocrm` → коммит → сервер `task crm:switch`; **записать время T (UTC)** | 1–2 мин |
| 7 | Проверки | сервер `task espocrm:health`; сценарии интерфейса пользователями; печатные формы; звонок (если живая телефония включена) | 10 мин |
| 8 | После | сервер `task backup:run tier=db`, `task espocrm:restore-check`; объявить | 5 мин |

Окно для пользователей — шаги 1–6. По временам этапа 10 (2026-10-18): шаг 1 ≈ 1–2 мин (прогон роли на production — около
1 мин), шаг 2 ≈ 2,5 мин (снимок с проверкой — 2 мин 20 с), шаги 3–4 ≈ 3,5 мин (pull, restore стенда, `park`, телефония
и проверочный проход — 113 с; полный импорт — 1 мин 37 с, дельта не дольше), шаг 5 ≈ 2,5 мин (backup и отпечаток
стенда ≈ 15 с, push 21 с, restore 1 мин 15 с, отпечаток 10 с), шаг 6 ≈ 1–2 мин — **итого ≈ 12–15 мин** записи в CRM нет
(Vtiger на странице 503, EspoCRM ещё закрыта). Резерв на разбор находок дельты — до 10 мин; превышение — откат
(`vtiger`, §3), данные Vtiger целы.

### Потери истории (что не попадает в EspoCRM)

Решения прежних этапов, числа — сводка импорта этапа 10 (`import-summary.md`, снимок `20261018T091226`):

- **История изменений Vtiger** (`vtiger_modtracker_*`, история статусов) не переносится — остаётся в защищённом снимке
  (D-08).
- **Звонки:** пропуск PBXManager/CDR 2024-07-31…2026-06-12 — источников нет (D-16); звонки PBXManager 2019–2024 — без
  аудио, ссылка коннектора хранится как `cLegacyRecordingUrl` (1033 ссылки, D-10); внутренние звонки (номер из трёх
  цифр) не переносятся — 209 PBXManager; из CDR не импортируются звонки линии тренажёра (127) и конференции (2) —
  перенесено 83 звонка из 212.
- **Записи разговоров:** из 189 WAV привязано 66; не привязаны 9 файлов с несколькими возможными звонками (имя
  `sub-monitor` — минута и номера, Q-54), 1 файл двух звонков, 5 пустых (≤ 44 байт), 108 — линии тренажёра. Файлы
  остаются на сервере и в тире `recordings`.
- **Файлы:** 8 имён файлов без файла в источнике, 5 фото контактов без файла, 3 документа без вложения (D-23); файлы
  удалённых в Vtiger записей (334 строки вложений без файла) не переносятся.
- **Не переносятся по решению:** workflows и шаблоны писем, определения отчётов Vtiger (свой модуль отчётов, D-84),
  портал, периодические счета, интеграции (IMAP, Google, SPVoip, Jivosite, банк «Точка», 1С) — D-15; личные ящики
  MailManager (3) — подключаются в EspoCRM заново (D-189); адреса и домашние телефоны сотрудников, кэш вложений
  MailManager (D-23).
- **Сохранено, но не связями:** связи-конфликты, ссылки на исчезнувшие и неимпортируемые записи (`conflict` 47,
  `dangling` 24, `no_target` 66, `type_conflict` 23, внешний URL не URL — 1) — значения в `vtigerData` и архиве,
  разбор — приватный отчёт прогона; 5 счетов с итогом, отличным от акта, — как в источнике (D-05).

## 3. Откат

| Когда | Что делать |
|---|---|
| До шага 6 (окно, Vtiger не менялся с шага 1) | `itvolga_crm_primary: vtiger` → коммит → сервер `task crm:switch`: vhost и cron Vtiger вернулись, данные Vtiger целы. EspoCRM остаётся как есть для повтора. |
| После шага 6, критический сбой | 1) **сначала закрыть запись**: `itvolga_crm_primary: maintenance` → `task crm:switch` (страница 503, пользователи EspoCRM больше не пишут; слушатель телефонии — `-e espocrm_telephony_enabled=false`, если он включён); 2) на сервере `sudo espocrm-changes-since --against <пакет cutover> --export` — полное сравнение с состоянием момента переключения (добавленное, удалённое, связи, изменённое — по содержимому всех колонок, и без отметок времени; счётчики по таблицам и приватный список `/var/backups/espocrm/changes-*.tsv`, 600: только `id`, ссылки `*_id`/`*_type`, флаг удаления и время — без значений, запись открывается в EspoCRM по `id`), для быстрой оценки — `sudo espocrm-changes-since '<T>'` по времени; 3) `itvolga_crm_primary: vtiger` → `task crm:switch`; 4) сделанное после T вносится в Vtiger вручную по списку (звонки этого периода — в CDR и WAV при любом исходе); 5) EspoCRM и её данные не удаляются: при повторном переключении записи, созданные в EspoCRM (без `vtigerId`), импорт не трогает, импортированные — обновляет дельта. |
| После переключения, повреждены данные EspoCRM (остаёмся на EspoCRM) | сначала `espocrm-changes-since --against <пакет>` (что будет потеряно), затем `sudo espocrm-restore <пакет pre-restore\|cutover\|nightly> --yes` (с `--carry-calls-from <тот же пакет>` звонки слушателя после пакета сохраняются); страховочный пакет текущего состояния restore снимает сам — под той же блокировкой и при уже остановленных писателях. Сбой restore печатает команду отката с `--server-config <файл>` (серверные ключи сохранены до замены `data/`): её выполнить как есть — она снова запускает PHP-FPM, cron и слушатель. Остатки неудачного прогона (`espocrm__prev_*`, `.restore-aside-*`) после успешного отката удаляются вручную (health предупреждает). |

Нельзя: удалять Vtiger, `php74-fpm`, БД, cron, роли; выключать 2FA или метод «Ключ безопасности» в настройках, пока им
пользуются (ядро молча пропустит второй фактор, `security-key.md`); перезапускать Asterisk (только `manager reload`).
