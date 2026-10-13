# Телефония EspoCRM на production — шаблоны (этап 07.1, применение — этап 10)

Ничего из этого каталога на этапе 07.1 на сервер не попадает: production только читается (`AGENTS.md`). Шаблоны
проверены на изолированной тестовой АТС стенда с тем же пакетом Asterisk (`deploy/telephony`, `task telephony:up`).
Контракт интеграции — `docs/migration/telephony.md`.

| Файл | Куда (этап 10) | Что меняет на сервере |
|---|---|---|
| `manager.d-itvolga-espo.conf.example` | `/etc/asterisk/manager.d/itvolga-espo.conf` (`root:asterisk 0640`), секреты — из vault | два пользователя AMI; `asterisk -rx "manager reload"`, **без рестарта**; диалплан, транки и `manager.conf` не меняются |
| `recordings-acl.sh.example` | разово: `sh recordings-acl.sh <пользователь EspoCRM>` | ACL чтения `/var/spool/asterisk/monitor` для пользователя EspoCRM |
| `itvolga-espo-telephony.service.example` | `/etc/systemd/system/itvolga-espo-telephony.service` | служба слушателя AMI (пользователь, PHP и путь — этап 09) |

Настройки EspoCRM — команда `itvolga-setup-telephony`, JSON через stdin (секреты не в argv):

```json
{"enabled": true,
 "ami": {"address": "tcp://127.0.0.1:5038",
         "listener": {"username": "itvolga-espo-listener", "secret": "<vault>"},
         "dialer": {"username": "itvolga-espo-dialer", "secret": "<vault>"}},
 "rules": {},
 "recordings": {"root": "/var/spool/asterisk/monitor", "asteriskDir": "/var/spool/asterisk/monitor"},
 "fallbackExtension": "108"}
```

Пустые `rules` — правила production по умолчанию (`TrackerSettings::DEFAULTS`): телефоны `^[12][01][0-9]$`, транки
`trunk-russia`/`trunk-megafon` — входящие, `trunk-easybell` — тренажёр (не записывается), входящий контекст `call-in`,
исходящий — `call-out`, местный код `8352`, Caller ID звонка из CRM — `"<номер>" <номер>` (как у телефонов в
`pjsip.conf`). После настройки: `itvolga-setup-telephony --check` — самопроверка прав AMI (ожидается: слушатель —
список каналов разрешён, Originate запрещён; набор — Command, Hangup и список каналов запрещены).

Перед этапом 10 перепроверить только чтением (Q-54): что `send_recording_wrapper.sh` не переносит и не перекодирует
WAV после записи (иначе путь в CRM устареет), и что шаблоны `phones-out` на сервере не изменились.
