# Ansible EspoCRM для сервера (этап 09)

Развёртывание EspoCRM рядом с Vtiger на `serv.itvolga.com` как код Ansible сервера (`/data/server/ansible`). До этапа 10
`/data/server` и production только читаются (`AGENTS.md`), поэтому здесь лежит **наложение**: что добавить в репозиторий
сервера и как изменить его общие файлы. Контракт роли — `docs/migration/deploy.md`, runbook этапов 10–11 —
`docs/migration/cutover.md`, решения — D-180…D-188.

| Путь | Что | Куда на этапе 10 |
|---|---|---|
| `roles/espocrm/` | роль: ядро EspoCRM (закреплённый релиз), модуль Itvolga (git archive коммита), PHP-FPM 8.5, БД, cron, телефония, vhost и переключатель `serv.itvolga.com`, fail2ban, инструменты `espocrm-*` | `ansible/roles/espocrm/` |
| `playbooks/11-espocrm.yml` | развёртывание и health-check (не в `site.yml`) | `ansible/playbooks/` |
| `playbooks/12-crm-switch.yml` | переключение `serv.itvolga.com`: vtiger → maintenance → espocrm и обратно | `ansible/playbooks/` |
| `server-ansible.patch` | общие файлы сервера: `itvolga_crm_primary` и `enabled` у vhost Vtiger (`vars.yml`), секреты EspoCRM (`vault.yml.example`), флаг `enabled` роли apache, cron Vtiger роли vtiger, тир `recordings` и ночной пакет EspoCRM роли backup, задачи Taskfile, таблицы `CLAUDE.md` | `git apply` в `/data/server` |
| `SERVER_BASE` | коммит `/data/server`, к которому сделан патч | — |
| `tests/` | одноразовая проверочная машина: Ubuntu 26.04 с systemd в Docker, фикстуры и роли сервера | не переносится |

## Команды (этот репозиторий)

```bash
task ansible:overlay      # клон /data/server на SERVER_BASE + роль + плейбуки + патч → build/ansible-overlay
task ansible:lint         # task ansible:lint сервера на наложении (ansible-lint, профиль production)
task ansible:syntax       # task ansible:syntax сервера на наложении (site, 09, 10, 11, 12)
task ansible:test         # одноразовая машина: роли сервера, роль espocrm дважды (changed=0), --check, сценарий
                          # backup/restore/restic, телефония, переключение vtiger → maintenance → espocrm → vtiger
task ansible:check        # --check --diff роли на развёрнутой проверочной машине (дрейф = 0)
task ansible:test-down    # удалить проверочную машину
scripts/deploy/overlay.sh status            # база патча и HEAD /data/server
scripts/deploy/overlay.sh install --stage10 # этап 10, только с разрешения владельца: роль и патч в /data/server
scripts/deploy/bundle.sh push|pull …        # этапы 10–11: пакет EspoCRM стенд ⇄ production (D-187)
```

Наложение собирается из чистого клона: в нём нет `vault.yml` и `.vault_pass` (они вне Git сервера), поэтому ничего не
расшифровывается; `.vault_pass` наложения — случайная строка для `ansible.cfg`. Секреты проверочной машины генерируются
из `vault.yml.example` случайными значениями (`build/ansible-test/`, 600, не в Git), данные — синтетические.

Правка общих файлов сервера: `task ansible:overlay` → правка в `build/ansible-overlay` → `scripts/deploy/overlay.sh patch`
→ коммит патча здесь. Если `/data/server` ушёл вперёд от `SERVER_BASE` (`overlay.sh status`), патч переносится на новую
базу до этапа 10.
