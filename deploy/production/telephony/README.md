# Телефония EspoCRM на production — шаблон пользователей AMI (этап 07.1)

Ничего из этого каталога на сервер не копируется вручную: на production телефонию разворачивает роль Ansible
`deploy/ansible/roles/espocrm` (этап 09, применение — этап 10 с разрешения владельца; `docs/migration/deploy.md` §6).
Контракт интеграции — `docs/migration/telephony.md`.

| Файл | Кто использует | Что |
|---|---|---|
| `manager.d-itvolga-espo.conf.example` | тестовая АТС стенда (`deploy/telephony/entrypoint.sh` подставляет свои секреты); роль `espocrm` рендерит **тот же текст** (`templates/manager.d-itvolga-espo.conf.j2`, секреты — vault; совпадение проверяет `task ansible:test`) | два пользователя AMI с минимальными правами → `/etc/asterisk/manager.d/itvolga-espo.conf` (`root:asterisk 0640`), `manager reload` **без рестарта**; диалплан, транки и `manager.conf` не меняются |

Прежние примеры этапа 07.1 заменены ролью (этап 09): служба слушателя — `templates/espocrm-telephony.service.j2`
(`espocrm-telephony.service`, пользователь `espocrm`, PHP 8.5, `/var/www/espocrm`); ACL записей — задачи роли: `u:espocrm:rx`
и default ACL на `/var/spool/asterisk/monitor` и **ACL прохода `u:espocrm:--x` на `/var/spool/asterisk`** (на сервере
`asterisk:root 0750`, проверено только чтением 2026-10-17 — ACL одного корня до файлов не пускал бы); пакет `acl` (на
сервере его нет) роль ставит.

Настройки EspoCRM (`itvolga-setup-telephony`, JSON через stdin) роль пишет из `/etc/espocrm/telephony.json` (0600 root):
адрес AMI `tcp://127.0.0.1:5038`, учётки `itvolga-espo-listener`/`itvolga-espo-dialer` (секреты — vault), пустые
`rules` — правила production по умолчанию (`TrackerSettings::DEFAULTS`), корень записей `/var/spool/asterisk/monitor`,
запасной внутренний номер `108` — только если в EspoCRM он не задан. Живая интеграция — `espocrm_telephony_enabled`
(Q-56); самопроверка прав — `espocrm itvolga-setup-telephony --check` (слушатель — список каналов да, Originate нет;
набор — Command, Hangup и список каналов нет).

Перед этапом 10 перепроверить только чтением (Q-54): что `send_recording_wrapper.sh` не переносит и не перекодирует
WAV после записи (иначе путь в CRM устареет), и что шаблоны `phones-out` на сервере не изменились.
