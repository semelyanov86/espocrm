# Модель EspoCRM (этапы 03, 04.2–04.6, 05.1)

Проверено на стенде 2026-09-30 (EspoCRM 10.0.9), финансовые документы — 2026-10-01, счета и платежи — 2026-10-02, акты и сквозной сценарий — 2026-10-03. Источник истины — метаданные модуля; этот файл их описывает. Сверка с картой: колонки `espo_check` в `field-map.csv` (952 строки — ok: 630 этапа 03, 151 этапа 04.2, 65 этапа 04.3, 47 этапа 04.4, 59 этапа 04.5) и `relations.csv` (197 связей: 140, 19, 17, 11, 10), `task model:check`; покрытие финансовых полей и связей — `finance-coverage.md` (генерируется, этап 04.6). Решения — D-38…D-44, D-50…D-76.

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
| `…/Tools/Finance/` (`Editing/` — правило правки документа), `…/Tools/FinanceDocument/` | расчётное ядро (04.1) и сохранение финансовых документов: позиции, итоги, номера, юрлицо (в том числе исходное `spcompany` при импорте), сверка импорта и контроль итогов (`SourceMarks`), предпросмотр, «Создать заказ»/«Создать счёт» (04.2, 04.3) |
| `…/Hooks/Common/FinanceDocument.php`, `…/Hooks/Common/FinanceItemGuard.php`, `…/Hooks/LegalEntity/Singleton.php` | сохранение документа с позициями в одной транзакции; запрет прямой записи позиций; одно юрлицо |
| `…/Classes/Record/Finance/DecimalInput.php`, `…/Classes/FieldProcessing/Finance/ItemListLoader.php`, `…/Classes/Acl/FinanceItem/AccessChecker.php`, `…/Classes/Select/FinanceItem/DocumentLevel.php` | отказ от float на входе API; поле `itemList` при чтении; доступ к позициям — по правам на документ (запись и списки) |
| `…/metadata/app/itvolgaFinance.json` | реестр финансовых документов (сущность позиций, префикс и первый номер, поля «Создать заказ»/«Создать счёт») и платежей (`payments`: сущность распределений, нумерация, документы-цели) |
| `…/Tools/Finance/Payment/` (`AllocationEditor`, `AllocationInput`, `AllocationPlan`), `…/Tools/FinancePayment/` | правило таблицы распределений (чистое ядро) и сохранение платежей: блокировки, строки, оплата документов (`SettlementUpdater`), импорт строк, история, «Добавить платёж», предпросмотр (04.4) |
| `…/Hooks/Payment/Allocations.php`, `…/Hooks/PaymentAllocation/Integrity.php`, `…/Hooks/Import/FinanceGuard.php`, `…/Hooks/Common/FinanceSilentImport.php`, `…/Classes/Record/Finance/{AllocationRestorer,OwnerRestorer}.php` | платёж с таблицей в одной транзакции; импортированные строки и каскад от документа; запрет CSV-импорта финансов; импорт только тихий (`IMPORT` + `SILENT`); запрет восстановления распределений и их владельцев (метка `removedWith`) |
| `…/Classes/ConsoleCommands/FinanceSettle.php`, `…/Classes/FieldProcessing/Finance/AllocationListLoader.php` | `itvolga-finance-settle` (пересчёт оплаты документов); таблица и остаток платежа при чтении |
| `…/metadata/logicDefs/{Quote,SalesOrder,Invoice}.json` | показ «Пересчёта ядра» и «Итогов Vtiger» (D-59) |
| `…/Classes/ConsoleCommands/{SetupFinance,FinanceVerify}.php` | `itvolga-setup-finance` (юрлицо, счётчики), `itvolga-finance-verify` (`sourceFormula`/`totalsCheck` импорта) |
| `client/custom/modules/itvolga/src/views/finance/`, `…/views/fields/money.js`, `…/finance/decimal-text.js`, `…/handlers/finance/convert-document.js` | редакторы позиций и распределений, показ денег без float, «Создать заказ»/«Создать счёт»/«Добавить платёж» |
| `…/EntryPoints/ItvolgaPrint.php`, `…/Tools/FinancePrint/`, `…/Tools/Finance/Printing/` | печатные формы (этап 05, D-79): `?entryPoint=itvolgaPrint` → `PrintService` (реестр `printForms`, доступ, транзакция чтения) → `PrintData` (запись, строки с единицами, юрлицо, контрагент) → `Presenter` (чистое ядро: `Formatter`, `AmountInWords`) → `CodeTemplate` → Dompdf ядра |
| `…/Resources/printForms/`, `…/Resources/fonts/`, `…/metadata/app/pdfEngines.json` | HTML/CSS форм (счёт, акт, ПКО, КП, заказ), шрифт Liberation Sans и его регистрация (D-82) |
| `client/custom/modules/itvolga/src/handlers/finance/print-form.js` | кнопка «Печать» карточек `Invoice`, `Act`, `Payment` (только приходы), `Quote`, `SalesOrder` |
| `…/Tools/Report/` (`Core/` — чистое ядро), `…/Classes/Select/Where/{Related,FieldCompare,ReportDrillDown}.php`, `…/Classes/ORM/CountDistinct.php`, `…/Classes/Acl/Report/`, `…/Classes/Select/Report/`, `…/Hooks/Report/`, `…/Hooks/ReportFolder/`, `…/Repositories/{Report,ReportFolder}.php`, `…/Services/ReportFolder.php`, `…/Classes/ConsoleCommands/SetupReports.php`, `…/Resources/reports/standard/`, `…/metadata/app/{itvolgaReports,select,orm}.json` | модуль отчётов (этап 05.1, D-84…D-104): движок, свои типы where-элементов, `COUNT(DISTINCT)`, доступ к отчётам, проверка определения, папки, стандартные отчёты — `reports.md` |
| `client/custom/modules/itvolga/src/{report,views/report,handlers/report}/` | конструктор, страница результата, список с папками, детализация, перенос в папку |
| `scripts/model/` | сверка модели с картой (в том числе реестр печатных форм и умолчание условий), генератор словаря значений, покрытие финансов |
| `tests/stage03/`, `tests/stage04/`, `tests/stage05/` | приёмочные тесты API и PDF, помощники UI-сценариев |

Развёртывание на стенд: `task model:apply` (clear-cache — в том числе кэш шрифтов PDF, rebuild, роли, юрлицо и счётчики номеров, оплата документов, папки и стандартные отчёты, отметка времени клиента). Тесты: `task test:stage03`, `task test:stage04`, `task test:stage05`, `task test:stage05.1`, `task test:finance`, `task test:reports`.

## Служебные поля (D-41)

На каждой импортируемой сущности (21 шт.: стандартные Account, Contact, Lead, Opportunity, Task, Call, Meeting, Email, Case, KnowledgeBaseArticle, Document, DocumentFolder, Note, User, Attachment и собственные): `vtigerId` (int, уникальный индекс, только чтение через API); где был номер — `vtigerNo`; кроме `VtigerArchive` и `ContactAccess` — `vtigerData` (JSON непустых исходных значений без рабочего поля; только чтение, видно только администраторам).

## Стандартные сущности

| Сущность | Добавленные поля (префикс `c`, D-12) | Изменено у поля ядра | Добавленные связи |
|---|---|---|---|
| Account | `cShortName`, `cEmployees`, `cRating`, `cInn`, `cKpp`, `cBankAccount`, `cBankName`, `cCorrAccount`, `cBic`, `cVkUrl` | опции `type`, `industry` | `cProjects`, `cVtigerArchives`, `cPayments` (плательщик) |
| Contact | `cLeadSource`, `cDepartment`, `cBirthday`, `cVkUrl`, `cSupportStartDate`, `cSupportEndDate`, `cNeedOriginalDocs`, `cSendNews`, `cPartnerAds`, `cSendAlerts`, `cOtherAddress` (адрес), `cPhoto` (изображение) | опции `salutationName` (+`Prof.`) | `cContactAccesses`, `cVtigerArchives`, `cPayments` (плательщик) |
| Lead | `cRating`, `cPriority`, `cJivositeId`, `cVkUrl` | опции `status`, `source`, `salutationName`; `opportunityAmount` decimal(25,8) | `cVtigerArchives` |
| Opportunity | `cOpportunityType`, `cProducts` | опции и вероятности `stage`; `amount` decimal(25,8), необязательно | `cProducts` (M:N Product), `cProjects` |
| Task | `cTaskType` (вид «Письмо», D-24) | опции `status` (+`Planned`, `Pending Input`), `priority` (+пусто); родитель — и счёт (D-61) | — |
| Call | `cPhoneNumber`, `cCallStatusRaw`, `cLegacyRecordingUrl` (не воспроизводится, D-10), `cBillDuration`, `cConnectorCallId`, `cIncomingLine` — только чтение | родитель — и счёт (D-61) | — |
| Meeting | — | `dateStart/dateEnd` необязательны (D-43); родитель — и счёт (D-61) | — |
| Case | `cSeverity`, `cSolution`, `cTags` | опции `status`/`priority` (подписи Vtiger), `type` | `cDocuments` |
| KnowledgeBaseArticle | `cTags` | `name` до 500 символов, опции `status` | `cDocuments` |
| Document | `cExternalUrl` | `file` необязателен и без ограничения типов, `publishDate` необязательна | `cCases`, `cKnowledgeBaseArticles`, `cProjects`, `cProjectTasks`, `cVtigerArchives`, `cPayments` |
| User | `cPhoneExtension` | — | — |
| Email, Note, DocumentFolder, Attachment | только служебные поля | — | — |
| ActionHistoryRecord | — | действие `reveal` («Показ пароля») | — |

## Собственные сущности

| Сущность | Судьба | Поля | Связи |
|---|---|---|---|
| Vendor | рабочая (D-13) | `name`, `website`, `emailAddress`, `phoneNumber`, `inn` | `products`, `payments` (получатель) |
| Product | рабочая (D-14) | `type` (товар/услуга), `isActive`, `code`, `unitPrice` (валюта, decimal), `unit`, `qtyPerUnit` (decimal), `category`, `isBillableTime`, `vendor` | `vendor`, `opportunities`, `vtigerArchives` |
| Project | исторический архив, только чтение | `status`, `type`, `priority`, `progress`, `dateStart`, `dateEndPlanned`, `dateEnd`, `budget` (валюта, decimal), `url`, `account`, `opportunity` | `projectTasks`, `documents` |
| ProjectTask | исторический архив, только чтение | `project`, `status`, `priority`, `type`, `progress`, `orderNumber`, `hours`, `dateStart`, `dateEnd`, `showInStat`, `gitCommit`, `tags` | `documents` |
| VtigerArchive | архив Consignment, ServiceContracts, Assets, Jivosite, JVmes; только чтение, создаётся только импортом | `vtigerModule`, `vtigerNo`, `data` (JSON записи и строк), `recordDate`, `account`, `contact`, `lead`, `product`, `invoice` (накладная → счёт, D-61), `parentArchive` (сообщение → чат) | `childArchives`, `documents` |
| ContactAccess | поля доступа контактов (D-06, D-42) | `contact`, `anydeskId`, `anydeskPassword` (шифр, не читается через API), `hasAnydeskPassword`, `hostname`, `ipAddress` | `contact` |
| Quote, SalesOrder, Invoice, Act | рабочие финансовые документы (D-50…D-53, D-57, D-69) | поля «Document» `finance-contract.md` §11 (`number`, `status`, `account`, `legalEntity`, `taxMode`, деньги decimal, `sourceFormula`, `totalsCheck`, контроль итогов `expected*`/`source*`, адреса, `vtigerId`, `vtigerData`) + `itemList` (нехранимая таблица позиций); Quote: `dateValidUntil`, `inventoryManager`; SalesOrder: `dateDue`, `quote`; Invoice: `dateInvoiced`, `dateDue` (обязательны для формы и API), `salesOrder`, `quote`, `act` (несколько счетов на один акт, audited), `balanceSource`; Act: `dateAct` (обязательна для формы и API) | `items` (каскад), `salesOrders` / `quote`, `invoices` (у Quote, SalesOrder и Act), `documents`; Invoice: `vtigerArchives`, активности (`tasks`, `calls`, `meetings`, `emails`); обратные `cQuotes`, `cSalesOrders`, `cInvoices` у Account, Contact, Opportunity, Document, `cActs` у Account, Contact, Document |
| QuoteItem, SalesOrderItem, InvoiceItem, ActItem | позиции (пишутся только через документ) | поля «Item» §11 (`order`, `product`, `quantity`, `unitPrice`, скидки, `taxRate`, `amount`, `purchaseCost`, `margin`) + `name` (название товара на момент сохранения) | `quote` / `salesOrder` / `invoice` / `act`, `product` |
| LegalEntity | одно юрлицо (D-55) | реквизиты §11, `vtigerCompanyKey` = `Default` | — |
| Payment | рабочий платёж (D-62…D-68) | поля «Payment» §11 (`number` без префикса, `datePaid`, `direction`, `method`, `amount`, `status`, `payer` Account/Contact/Vendor, `legalEntity`, реквизиты контрагента, `vtigerId`, `vtigerData`) + `allocationList` (нехранимая таблица распределений, audited), `allocatedAmount`/`unallocatedAmount` (при чтении); лента | `paymentAllocations` (каскад), `payer`, `documents` |
| PaymentAllocation | строка распределения (пишется только через платёж и импорт) | `payment`, `invoice` или `salesOrder`, `amount`, `order`, `source`, `sourceConflict`, `vtigerData`, `paymentDatePaid`/`paymentStatus` (foreign) | `payment`, `invoice`, `salesOrder` |

У `Invoice` и `SalesOrder` (этап 04.4): `paidAmount`, `balanceAmount`, `settlementState` — хранимая оплата (только чтение, audited, D-64), связь `paymentAllocations` (каскад, только чтение), панель «Оплаты», действие «Добавить платёж».

`Act` (этап 04.5, D-69…D-71): номер — счётчик без префикса, статусы Создан/Отправлен/Выполнен/Получен + пусто; связи с платежами нет (в источнике ни одной). На счёте — «Создать акт» (обратная конвертация: ссылка хранится в счёте, `Tools/FinanceDocument/ConversionSourceGuard`) или «Открыть акт», если у счёта есть живой акт; панель «Счета» акта — только просмотр, счета привязываются полем «Акт» счёта.

Сквозной сценарий (этап 04.6, D-73…D-76, `finance-contract.md` §18): «Создать заказ/счёт/акт» копируют и команды источника (`DocumentConverter` загружает поля linkMultiple — до исправления форма получала пустые команды); номер сохранённого документа или платежа меняет только импорт (`Hooks/Common/FinanceNumberGuard`, `financeNumberReadOnly`); смена статуса или типа платежа и его удаление требуют права чтения каждого документа платежа (как правка строк, D-63); панели «Заказы»/«Счета» предложения и «Счета» заказа — только просмотр, у контрагента, контакта и сделки на панелях документов нет «Выбрать»/«Отвязать» (создание остаётся).

## Отчёты (этап 05.1, D-84…D-104)

| Сущность | Поля | Связи |
|---|---|---|
| Report | `name`, `description`, `type` (табличный, сводный, сводный с детализацией, матрица; после создания не меняется), `entityType` (не меняется), `accessType` (личный, публичный, по списку), лимиты `rowLimit`/`groupLimit`, JSON-части определения (`columns`, `sorting`, `groups`, `aggregates`, `groupSort`, `totals`, `calculations`, `filters`, `havingFilters`, `quickFilters`, `labels`), `seedKey` | `folder` → ReportFolder, `assignedUser` (владелец), `sharedUsers` → User, `sharedTeams` → Team (обратные `cSharedReports` у User и Team, без панелей) |
| ReportFolder | `name` (уникально), `description`, `isSystem` («Общие»), `assignedUser`, `seedKey`; CategoryTree без вложенности | `reports` |

Сущности, доступные отчётам, — по флагу `scopes.<E>.itvolgaReports` (`true` у строк документов, распределений и ContactAccess, `"admin"` у User, Team, журналов, `false` у Report и ReportFolder) и `object`. Контракт — `reports.md`.

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
| Report | создание, чтение team (свои, публичные, адресованные пользователю или его команде), правка и удаление own | то же | то же | то же |
| ReportFolder | создание, чтение all, правка и удаление own | то же | то же | то же |
| Quote, SalesOrder, Invoice, Act, Payment | all | — | — | — |
| QuoteItem, SalesOrderItem, InvoiceItem, ActItem, PaymentAllocation, LegalEntity | чтение all (позиции — по доступу к документу, распределения — к платежу; запись позиций и распределений — никому) | — | — | — |

`team` = свои записи + записи команд пользователя: групп Vtiger и иерархических команд («Подчинённые заместителей» — записи менеджеров, «Заместители директора» — контакты заместителей). Иерархические команды записи восстанавливаются при любом сохранении, связь `teams` не меняется через API link/unlink не-администраторами; членство следует ролям сразу при их изменении. Назначение — всем пользователям; экспорт, импорт и массовое обновление разрешены (кроме ContactAccess). Звонки из истории PBXManager не редактируются и не удаляются не-администраторами. Пользователь без ролей не имеет доступа ни к чему.

## Отложено

Графики, дашлеты и ключевые показатели — этап 05.2; экспорт, печать и рассылка отчётов — 05.3 (`reports.md`). Quote, SalesOrder, позиции и LegalEntity — этап 04.2 (§14); Invoice и InvoiceItem — этап 04.3 (§15); Payment, PaymentAllocation и оплата документов — этап 04.4 (§16); Act, ActItem и `Invoice.act` — этап 04.5 (§17); сквозной сценарий — этап 04.6 (§18); печатные формы — этап 05 (§19, `print-forms.md`); расчётное ядро — `Tools/Finance/`, этап 04.1 (D-45); живая телефония и импорт истории звонков — 07.x; импорт данных — 06.x.
