# Источники телефонии (факты аудита 2026-09-29)

Номера телефонов, имена файлов записей и адреса провайдеров в документ не включены. Команды — `evidence.md`, скрипт `scripts/audit/remote/telephony_inventory.sh`, `cdr_overlap.py`.

## 1. Сводная хронология

| Период | Vtiger PBXManager | MySQL `asteriskcdrdb.cdr` | `Master.csv` | WAV `/var/spool/asterisk/monitor` |
|---|---|---|---|---|
| 2019-11 … 2024-07 | 1116 звонков, с перерывами (нет 2020-07…09, 2021-05…2022-03, 2022-05…2023-08, 2024-01…03) | — | — | **нет** (записи были у внешнего коннектора на старом сервере) |
| 2024-08 … 2026-06-12 | **нет данных** | — | — | — |
| 2026-06-13 … 2026-07 | — | — | 72 строки (июнь 25, июль 47) | июнь 21, июль 44 файла |
| 2026-08 … 2026-09-28 | — | 106 строк (авг 33, сен 73) | 124 строки (авг 51, сен 73) | авг 46, сен 55 файлов |

**Пропуск истории:** звонков за 2024-07-31 … 2026-06-12 нет ни в одном доступном источнике. Старый сервер выведен из эксплуатации; `/data/server/scripts/export-asterisk.sh` переносил только IVR-звуки, CDR/WAV не экспортировались; в `/data/server/backup/asterisk` — только `sounds/`. Файловый поиск по новому серверу других записей разговоров или копий CDR не нашёл. Восстановить эту историю нельзя; владелец подтвердил, что других источников нет — потеря фиксируется (Q-19, D-16).

## 2. Vtiger PBXManager

- Таблицы `vtiger_pbxmanager` (+ `vtiger_pbxmanagercf` только id), 1116 живых записей, удалённых нет; создавались от `user#1` (822), `user#6` (133), `user#7` (12), `user#8` (149) — поле `user`/владелец по внутреннему номеру.
- `direction`: outbound 817, inbound 299. `callstatus`: outbound completed 543, busy 127, no-answer 90, Unallocated 18, Circuit/channel congestion 17, No user responding 17, ringing 4, Network out of order 1; inbound completed 217, no-answer 59, ringing 11, no-response 8, busy 2, No user responding 2.
- Длительности `totalduration`/`billduration` (секунды) заполнены; `endtime` пусто у 3. Часовой пояс `starttime`/`endtime`: до 2020-10-22 — Europe/Berlin (время коннектора; `createdtime` в это время писался по Москве, разница +2 ч зимой / +1 ч летом), с 2020-10-23 — совпадает с поясом Vtiger (D-30).
- `customer` (ссылка на клиента) заполнено у 36: Contacts 3 + **23 удалённых Contacts**, Leads 6, Accounts 4; `customertype` у 36; `customernumber` у всех 1116 — номер собеседника (позволяет повторно сопоставить с клиентами при импорте).
- `recordingurl` у 1033: все вида `http://127.0.0.1:5000/recording?id=<n>`; `sourceuuid` — число из 1–4 цифр (id записи во внешнем коннекторе, **не** Asterisk `uniqueid`/`linkedid`). Коннектор работал на старом сервере; на текущем порт 5000 не слушается, коннектор не установлен. **Эти ссылки не являются рабочим аудио** и импортируются только как архивная пометка `cLegacyRecordingUrl`.
- Поля SalesPlatform `sp_*` (провайдер, номера, признак записи) пусты; `incominglinename` у 921.
- Шлюз `vtiger_pbxmanager_gateway`: 1 строка `PBXManager` с ключами `webappurl`, `outboundcontext`, `vtigersecretkey` (значения не читались). Обработчики `PBXManagerHandler`/`PBXManagerBatchHandler` активны; `vtiger_pbxmanager_phonelookup` — 304 строки индекса номеров (Leads/Accounts/Contacts).
- SPVoipIntegration: модуль выключен (`presence=1`), провайдер по умолчанию — zadarma, в настройках заполнены только URL провайдеров, ключей нет. В пользователях заполнен только `phone_crm_extension` (5 из 7); поля `sp_*_extension` пусты; `vtiger_asteriskextensions` без номеров.

## 3. SPCallPopup

210 записей 2020-12 … 2024-07, каждая ровно к одному звонку PBXManager (`callid`, также `crmentityrel` PBXManager↔SPCallPopup 210). Полезные данные: комментарий у 2, имя/тип клиента у 3; связи с Contacts 1, Leads 2. Решение — слить в `Call` (`module-decisions.md`).

## 4. Asterisk на текущем сервере

- Asterisk 22.5.2 (apt), активен; `chan_pjsip`; модули CDR: `cdr_adaptive_odbc` (MySQL через ODBC DSN `asterisk-cdr`) и `cdr_csv` — оба зарегистрированы. `app_mixmonitor` загружен.
- Диалплан `/etc/asterisk/extensions.conf`: 1 `MixMonitor` (подпрограмма `sub-monitor`), 2 `AGI`, 3 `System`, упоминаний Vtiger/CURL нет. Формат пути записи по шаблону Ansible `extensions.conf.j2`: `/var/spool/asterisk/monitor/%Y/%m/%d/<дата>_From.<номер>_To.<номер>.wav`, путь пишется в `CDR(recordingpath)`, после записи вызывается `send_recording_wrapper.sh`; на сервере подтверждены структура каталогов по датам и заполнение `recordingpath`, сам текст диалплана не сравнивался с шаблоном.
- **AMI:** `manager.conf` — `enabled=yes`, `port=5038`, `bindaddr=127.0.0.1`; пользователей AMI нет (`manager.d` содержит только README). Порт 5038 слушает только localhost. Для интеграции (этап 07.1) нужен отдельный пользователь с минимальными правами — это изменение production, требует разрешения.
- Слушаются: UDP 5060 (SIP), UDP 4569 (IAX), TCP 127.0.0.1:5038 (AMI).
- Контексты CDR (MySQL): call-out ANSWERED 63 / NO ANSWER 5, call-in 20/4, german-training 10, incoming-menu 3/1. По README роли `asterisk` в `cdr.conf` задано `unanswered=no` (неотвеченные вызовы без ответа системы не пишутся) — на сервере **не проверено**.

## 5. CDR: MySQL и CSV

- MySQL `asteriskcdrdb.cdr` — колонки `id, calldate, clid, src, dst, dcontext, channel, dstchannel, lastapp, lastdata, duration, billsec, disposition, amaflags, accountcode, uniqueid, linkedid, peeraccount, sequence, userfield, recordingpath`; 106 строк (2026-08-… 2026-09-28), 102 различных `uniqueid`, 98 `linkedid` (плечи одного звонка), `recordingpath` у 90 строк (86 различных путей).
- `Master.csv` — 196 строк, 18 полей (стандартный формат `cdr_csv` без `linkedid`), 2026-06-13 … 2026-09-28, 192 различных `uniqueid`.
- **`uniqueid` не уникален для строки CDR** (одна запись вызова может дать несколько строк): MySQL 106 строк / 102 `uniqueid`, CSV 196 / 192. В MySQL пара (`uniqueid`, `sequence`) уникальна для всех 106 строк.
- **Часовые пояса различаются:** время начала в `Master.csv` — UTC, `calldate` в MySQL — местное время сервера (ровно +2 ч в CEST у всех 114 пар с общим `uniqueid`).
- Сопоставление по составному ключу (`uniqueid`, время начала после перевода CSV в местное время, `dst`, `dstchannel`, `billsec`): в обоих — 106 строк, только в CSV — 90 (период до включения ODBC), только в MySQL — 0; внутри каждого источника ключ уникален. Без перевода времени совпадений 0.
- Ключи для импорта (D-20): строка MySQL — (`uniqueid`, `sequence`); CSV-строка сопоставляется с MySQL по составному ключу; группировка плеч — `linkedid` (только MySQL). 90 CSV-only строк (2026-06…08) — по одной строке на `uniqueid`, группировать плечи не нужно (проверено, Q-20).
- Бэкап: ночной `mysqldump` `asteriskcdrdb.sql` есть (тир `db`); `/var/log/asterisk/cdr-csv` в бэкап **не** входит.

**Перепроверено 2026-10-06 (снимок `20261006T192211`, этап 06.1):**
- MySQL `cdr` — 114 строк (2026-08-09 … 2026-10-05), путей `recordingpath` — 93, все записи найдены;
- `Master.csv` — 204 строки по 18 полей, в нём есть все 114 `uniqueid` MySQL;
- записей — 173 файла / 1,2 ГиБ, из них без строки CDR — 80.

## 6. Записи разговоров (WAV)

- 166 файлов, ~1.21 ГБ, только `.wav`, 2026-06 … 2026-09, пустых файлов нет; владелец `asterisk:asterisk`, права каталога `750`.
- Все 86 путей `recordingpath` из MySQL существуют на диске; 80 WAV не упомянуты в MySQL (период до ODBC). Сопоставление по местной минуте начала (±1 мин), звонящему и вызываемому из имени файла проверено на 86 известных парах — верно в 85; для 80 непривязанных: 76 однозначных совпадений (все — CSV-only строки), 4 неоднозначных → отчёт (D-31, `remote/wav_csv_match.py`).
- Каталог **не входит** в резервное копирование (restic-тиры `db/system/immich/opencloud`). Добавить в покрытие — этап 09.

## 7. Сопоставление при импорте (этап 07.2)

| Источник | Ключ | Клиент | Пользователь | Аудио |
|---|---|---|---|---|
| PBXManager | `vtigerId`, `sourceuuid` (архив) | `customer` → Contact/Lead/Account; иначе поиск по `customernumber` | `user` → User | нет (только архивная ссылка) |
| MySQL CDR | (`uniqueid`, `sequence`), группировка по `linkedid` | поиск по `src`/`dst` среди телефонов | внутренний номер → `User.cPhoneExtension` | `recordingpath` (проверка существования + sha256) |
| CSV CDR | составной ключ с переводом UTC → местное (дедупликация с MySQL) | как выше | как выше | по местной минуте ±1 и номерам из имени файла (D-31) |

Требования: не создавать вымышленных звонков; каждое плечо и каждый файл — в отчёт с причиной, если не сопоставлен; доступ к записи — по ACL звонка (владелец/команда), без публичных ссылок.
