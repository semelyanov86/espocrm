# Модель EspoCRM (этапы 03, 04.2)

Проверено на стенде 2026-09-30 (EspoCRM 10.0.9), финансовые документы — 2026-10-01. Источник истины — метаданные модуля; этот файл их описывает. Сверка с картой: колонки `espo_check` в `field-map.csv` (781 строка — ok: 630 этапа 03, 151 этапа 04.2) и `relations.csv` (160 связей), `task model:check`. Решения — D-38…D-44, D-50…D-56.

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
| `…/Tools/Acl/HierarchyTeams.php`, `…/Hooks/Common/HierarchyTeams.php`, `…/Hooks/User/SyncHierarchyTeams.php` | иерархические команды записей и членство пользователей |
| `…/Classes/Acl/Call/AccessChecker.php`, `…/metadata/aclDefs/Call.json` | история PBXManager только для чтения (ACL) |
| `…/Classes/ConsoleCommands/SetupAcl.php` | роли, команды, вкладки: `task espo -- itvolga-setup-acl [--dry-run]` |
| `client/custom/modules/itvolga/src/views/` | поле JSON-архива, поле пароля с кнопкой «Показать» |
| `…/Tools/Finance/` (`Editing/` — правило правки документа), `…/Tools/FinanceDocument/` | расчётное ядро (04.1) и сохранение финансовых документов: позиции, итоги, номера, юрлицо, сверка импорта, предпросмотр, «Создать заказ» (04.2) |
| `…/Hooks/Common/FinanceDocument.php`, `…/Hooks/Common/FinanceItemGuard.php`, `…/Hooks/LegalEntity/Singleton.php` | сохранение документа с позициями в одной транзакции; запрет прямой записи позиций; одно юрлицо |
| `…/Classes/Record/Finance/DecimalInput.php`, `…/Classes/FieldProcessing/Finance/ItemListLoader.php`, `…/Classes/Acl/FinanceItem/AccessChecker.php`, `…/Classes/Select/FinanceItem/DocumentLevel.php` | отказ от float на входе API; поле `itemList` при чтении; доступ к позициям — по правам на документ (запись и списки) |
| `…/metadata/app/itvolgaFinance.json` | реестр финансовых документов: сущность позиций, префикс и первый номер, поля «Создать заказ» |
| `…/Classes/ConsoleCommands/{SetupFinance,FinanceVerify}.php` | `itvolga-setup-finance` (юрлицо, счётчики), `itvolga-finance-verify` (`sourceFormula`/`totalsCheck` импорта) |
| `client/custom/modules/itvolga/src/views/finance/`, `…/views/fields/money.js`, `…/finance/decimal-text.js`, `…/handlers/finance/` | редактор позиций, показ денег без float, «Создать заказ» |
| `scripts/model/` | сверка модели с картой, генератор словаря значений |
| `tests/stage03/`, `tests/stage04/` | приёмочные тесты API и помощники UI-сценариев |

Развёртывание на стенд: `task model:apply` (clear-cache, rebuild, роли, юрлицо и счётчики номеров, отметка времени клиента). Тесты: `task test:stage03`, `task test:stage04`, `task test:finance`.

## Служебные поля (D-41)

На каждой импортируемой сущности (21 шт.: стандартные Account, Contact, Lead, Opportunity, Task, Call, Meeting, Email, Case, KnowledgeBaseArticle, Document, DocumentFolder, Note, User, Attachment и собственные): `vtigerId` (int, уникальный индекс, только чтение через API); где был номер — `vtigerNo`; кроме `VtigerArchive` и `ContactAccess` — `vtigerData` (JSON непустых исходных значений без рабочего поля; только чтение, видно только администраторам).

## Стандартные сущности

| Сущность | Добавленные поля (префикс `c`, D-12) | Изменено у поля ядра | Добавленные связи |
|---|---|---|---|
| Account | `cShortName`, `cEmployees`, `cRating`, `cInn`, `cKpp`, `cBankAccount`, `cBankName`, `cCorrAccount`, `cBic`, `cVkUrl` | опции `type`, `industry` | `cProjects`, `cVtigerArchives` |
| Contact | `cLeadSource`, `cDepartment`, `cBirthday`, `cVkUrl`, `cSupportStartDate`, `cSupportEndDate`, `cNeedOriginalDocs`, `cSendNews`, `cPartnerAds`, `cSendAlerts`, `cOtherAddress` (адрес), `cPhoto` (изображение) | опции `salutationName` (+`Prof.`) | `cContactAccesses`, `cVtigerArchives` |
| Lead | `cRating`, `cPriority`, `cJivositeId`, `cVkUrl` | опции `status`, `source`, `salutationName`; `opportunityAmount` decimal(25,8) | `cVtigerArchives` |
| Opportunity | `cOpportunityType`, `cProducts` | опции и вероятности `stage`; `amount` decimal(25,8), необязательно | `cProducts` (M:N Product), `cProjects` |
| Task | `cTaskType` (вид «Письмо», D-24) | опции `status` (+`Planned`, `Pending Input`), `priority` (+пусто) | — |
| Call | `cPhoneNumber`, `cCallStatusRaw`, `cLegacyRecordingUrl` (не воспроизводится, D-10), `cBillDuration`, `cConnectorCallId`, `cIncomingLine` — только чтение | — | — |
| Meeting | — | `dateStart/dateEnd` необязательны (D-43) | — |
| Case | `cSeverity`, `cSolution`, `cTags` | опции `status`/`priority` (подписи Vtiger), `type` | `cDocuments` |
| KnowledgeBaseArticle | `cTags` | `name` до 500 символов, опции `status` | `cDocuments` |
| Document | `cExternalUrl` | `file` необязателен и без ограничения типов, `publishDate` необязательна | `cCases`, `cKnowledgeBaseArticles`, `cProjects`, `cProjectTasks`, `cVtigerArchives` |
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
| Quote, SalesOrder | рабочие финансовые документы (D-50…D-53) | поля «Document» `finance-contract.md` §11 (`number`, `status`, `account`, `legalEntity`, `taxMode`, деньги decimal, `sourceFormula`, `totalsCheck`, адреса, `vtigerId`, `vtigerData`) + `itemList` (нехранимая таблица позиций); Quote: `dateValidUntil`, `inventoryManager`; SalesOrder: `dateDue`, `quote` | `items` (каскад), `salesOrders` / `quote`, `documents`; обратные `cQuotes`, `cSalesOrders` у Account, Contact, Opportunity, Document |
| QuoteItem, SalesOrderItem | позиции (пишутся только через документ) | поля «Item» §11 (`order`, `product`, `quantity`, `unitPrice`, скидки, `taxRate`, `amount`, `purchaseCost`, `margin`) + `name` (название товара на момент сохранения) | `quote` / `salesOrder`, `product` |
| LegalEntity | одно юрлицо (D-55) | реквизиты §11, `vtigerCompanyKey` = `Default` | — |

## Справочники (D-38, утверждены — Q-32)

Опции enum и подписи сгенерированы из настроенных списков Vtiger и подписей SalesPlatform (`task model:value-maps -- <приватный срез>`); словарь `vtigerValueMap/<Entity>.json` задаёт для каждого поля соответствие «значение Vtiger → ключ EspoCRM» по источникам (`Leads.leadstatus`, `Events.eventstatus`, `PBXManager.callstatus` …). Тест проверяет, что каждое значение источника попадает в опцию. Общие списки: `Lead.industry` ← `Account.industry`, `Lead.cRating` ← `Account.cRating`, `Contact.cLeadSource`/`Opportunity.leadSource` ← `Lead.source` (`optionsReference`).

## Доступ (D-39)

| Область | Директор | Заместитель директора | Менеджер по продажам | Менеджер клиентов |
|---|---|---|---|---|
| Account, Contact, Case, Document | all | чтение all, правка team | — | Case, Document: team |
| Lead | all | — | all | — |
| Opportunity, Vendor | all | — | — | — |
| Task, Call, Meeting | all | чтение all, правка team | team | team |
| Email | all | чтение all, правка team | team | — |
| KnowledgeBaseArticle | all | all, без удаления | — | all |
| Product | all | all | all | all |
| Project, ProjectTask | чтение all | чтение all | — | чтение team |
| VtigerArchive | чтение all | — | — | — |
| ContactAccess | только с ролью «Доступы» (создание, чтение, правка, удаление: all) |||||
| Quote, SalesOrder | all | — | — | — |
| QuoteItem, SalesOrderItem, LegalEntity | чтение all (позиции — по доступу к документу; запись позиций — никому) | — | — | — |

`team` = свои записи + записи команд пользователя: групп Vtiger и иерархических команд («Подчинённые заместителей» — записи менеджеров, «Заместители директора» — контакты заместителей). Иерархические команды записи восстанавливаются при любом сохранении, связь `teams` не меняется через API link/unlink не-администраторами; членство следует ролям сразу при их изменении. Назначение — всем пользователям; экспорт, импорт и массовое обновление разрешены (кроме ContactAccess). Звонки из истории PBXManager не редактируются и не удаляются не-администраторами. Пользователь без ролей не имеет доступа ни к чему.

## Отложено

Invoice, Act, Payment и их связи с Document/VtigerArchive/Vendor — этапы 04.3–04.5 по контракту `finance-contract.md` §11 (D-44); Quote, SalesOrder, позиции и LegalEntity — этап 04.2 (§14); расчётное ядро — `Tools/Finance/`, этап 04.1 (D-45); живая телефония и импорт истории звонков — 07.x; импорт данных — 06.x.
