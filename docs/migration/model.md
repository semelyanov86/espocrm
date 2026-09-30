# Модель EspoCRM (этап 03)

Проверено на стенде 2026-09-30 (EspoCRM 10.0.9). Источник истины — метаданные модуля; этот файл их описывает. Сверка с картой: колонки `espo_check` в `field-map.csv` (629 строк реализовано) и `relations.csv` (141 связь), `task model:check`. Решения — D-38…D-44.

## Где код

| Путь | Что |
|---|---|
| `custom/Espo/Modules/Itvolga/Resources/metadata/entityDefs/` | поля и связи: дополнения стандартных сущностей и собственные сущности |
| `…/metadata/{scopes,clientDefs,recordDefs,entityAcl}/` | свойства областей, UI, запреты экспорта/массовых действий, ограничения полей |
| `…/metadata/vtigerValueMap/` | словарь значений Vtiger → опции EspoCRM для импорта (D-38, генерируется) |
| `…/metadata/app/itvolgaAcl.json` | команды групп Vtiger и иерархические команды (D-39) |
| `…/metadata/app/layouts.json` | layouts стандартных сущностей берутся из модуля |
| `…/layouts/`, `…/i18n/{ru_RU,en_US}/` | раскладки карточек/списков/фильтров, подписи |
| `custom/Espo/Modules/Itvolga/{Controllers,Entities}/` | классы собственных сущностей |
| `…/Hooks/ContactAccess/`, `…/Tools/ContactAccess/` | шифрование пароля, показ с журналом (`POST /ContactAccess/:id/password`) |
| `…/Hooks/Common/HierarchyTeams.php` | иерархические команды при смене ответственного |
| `…/Classes/RecordHooks/Call/ProtectTelephonyHistory.php` | история PBXManager только для чтения |
| `…/Classes/ConsoleCommands/SetupAcl.php` | роли, команды, вкладки: `task espo -- itvolga-setup-acl [--dry-run]` |
| `client/custom/modules/itvolga/src/views/` | поле JSON-архива, поле пароля с кнопкой «Показать» |
| `scripts/model/` | сверка модели с картой, генератор словаря значений |
| `tests/stage03/` | приёмочные тесты API и помощники UI-сценариев |

Развёртывание на стенд: `task model:apply` (clear-cache, rebuild, роли, отметка времени клиента). Тесты: `task test:stage03`.

## Служебные поля (D-41)

На каждой импортируемой сущности (21 шт.: стандартные Account, Contact, Lead, Opportunity, Task, Call, Meeting, Email, Case, KnowledgeBaseArticle, Document, DocumentFolder, Note, User, Attachment и собственные): `vtigerId` (int, уникальный индекс, только чтение через API); где был номер — `vtigerNo`; кроме `VtigerArchive` и `ContactAccess` — `vtigerData` (JSON непустых исходных значений без рабочего поля; только чтение, видно только администраторам).

## Стандартные сущности

| Сущность | Добавленные поля (префикс `c`, D-12) | Изменено у поля ядра | Добавленные связи |
|---|---|---|---|
| Account | `cShortName`, `cEmployees`, `cRating`, `cInn`, `cKpp`, `cBankAccount`, `cBankName`, `cCorrAccount`, `cBic`, `cVkUrl` | опции `type`, `industry` | `cProjects`, `cVtigerArchives` |
| Contact | `cLeadSource`, `cDepartment`, `cBirthday`, `cVkUrl`, `cSupportStartDate`, `cSupportEndDate`, `cNeedOriginalDocs`, `cSendNews`, `cPartnerAds`, `cSendAlerts`, `cOtherAddress` (адрес), `cPhoto` (изображение) | опции `salutationName` (+`Prof.`) | `cContactAccesses`, `cVtigerArchives` |
| Lead | `cRating`, `cPriority`, `cJivositeId`, `cVkUrl` | опции `status`, `source`, `salutationName` | `cVtigerArchives` |
| Opportunity | `cOpportunityType`, `cProducts` | опции и вероятности `stage`; `amount` необязательно | `cProducts` (M:N Product), `cProjects` |
| Task | `cTaskType` (вид «Письмо», D-24) | опции `status` (+`Planned`, `Pending Input`), `priority` (+пусто) | — |
| Call | `cPhoneNumber`, `cCallStatusRaw`, `cLegacyRecordingUrl` (не воспроизводится, D-10), `cBillDuration`, `cConnectorCallId`, `cIncomingLine` — только чтение | — | — |
| Meeting | — | `dateStart/dateEnd` необязательны (D-43) | — |
| Case | `cSeverity`, `cSolution`, `cTags` | опции `status`/`priority` (подписи Vtiger), `type` | `cDocuments` |
| KnowledgeBaseArticle | `cTags` | `name` до 500 символов, опции `status` | `cDocuments` |
| Document | `cExternalUrl` | `file`, `publishDate` необязательны | `cCases`, `cKnowledgeBaseArticles`, `cProjects`, `cProjectTasks`, `cVtigerArchives` |
| User | `cPhoneExtension` | — | — |
| Email, Note, DocumentFolder, Attachment | только служебные поля | — | — |
| ActionHistoryRecord | — | действие `reveal` («Показ пароля») | — |

## Собственные сущности

| Сущность | Судьба | Поля | Связи |
|---|---|---|---|
| Vendor | рабочая (D-13) | `name`, `website`, `emailAddress`, `phoneNumber`, `inn` | `products` |
| Product | рабочая (D-14) | `type` (товар/услуга), `isActive`, `code`, `unitPrice` (валюта, decimal), `unit`, `qtyPerUnit` (decimal), `category`, `isBillableTime`, `vendor` | `vendor`, `opportunities`, `vtigerArchives` |
| Project | исторический архив, только чтение | `status`, `type`, `priority`, `progress`, `dateStart`, `dateEndPlanned`, `dateEnd`, `budget` (валюта, decimal), `url`, `account`, `opportunity` | `projectTasks`, `documents` |
| ProjectTask | исторический архив, только чтение | `project`, `status`, `priority`, `type`, `progress`, `orderNumber`, `hours`, `dateStart`, `dateEnd`, `showInStat`, `gitCommit`, `tags` | `documents` |
| VtigerArchive | архив Consignment, ServiceContracts, Assets, Jivosite, JVmes; только чтение, создаётся только импортом | `vtigerModule`, `vtigerNo`, `data` (JSON записи и строк), `recordDate`, `account`, `contact`, `lead`, `product`, `parentArchive` (сообщение → чат) | `childArchives`, `documents` |
| ContactAccess | поля доступа контактов (D-06, D-42) | `contact`, `anydeskId`, `anydeskPassword` (шифр, не читается через API), `hasAnydeskPassword`, `hostname`, `ipAddress` | `contact` |

## Справочники (D-38, Q-32)

Опции enum и подписи сгенерированы из настроенных списков Vtiger и подписей SalesPlatform (`task model:value-maps -- <приватный срез>`); словарь `vtigerValueMap/<Entity>.json` задаёт для каждого поля соответствие «значение Vtiger → ключ EspoCRM» по источникам (`Leads.leadstatus`, `Events.eventstatus`, `PBXManager.callstatus` …). Тест проверяет, что каждое значение источника попадает в опцию. Общие списки: `Lead.industry` ← `Account.industry`, `Lead.cRating` ← `Account.cRating`, `Contact.cLeadSource`/`Opportunity.leadSource` ← `Lead.source` (`optionsReference`).

## Доступ (D-39)

| Область | Директор | Заместитель директора | Менеджер по продажам | Менеджер клиентов |
|---|---|---|---|---|
| Account, Contact, Case, Document | all | team | — | Case, Document: team |
| Lead | all | — | all | — |
| Opportunity, Vendor | all | — | — | — |
| Task, Call, Meeting | all | team | team | team |
| Email | all | team | team | — |
| KnowledgeBaseArticle | all | all, без удаления | — | all |
| Product | all | all | all | all |
| Project, ProjectTask | чтение all | чтение team | — | чтение team |
| VtigerArchive | чтение all | — | — | — |
| ContactAccess | только с ролью «Доступы» (создание, чтение, правка, удаление: all) |||||

`team` = свои записи + записи команд пользователя: групп Vtiger и иерархических команд («Подчинённые заместителей» — записи менеджеров, «Заместители директора» — контакты заместителей). Назначение — всем пользователям; экспорт, импорт и массовое обновление разрешены (кроме ContactAccess). Звонки из истории PBXManager не редактируются и не удаляются не-администраторами. Пользователь без ролей не имеет доступа ни к чему.

## Отложено

`LegalEntity`, финансовые сущности и их связи с Document/VtigerArchive/Vendor — этапы 04.x (D-44); живая телефония и импорт истории звонков — 07.x; импорт данных — 06.x.
