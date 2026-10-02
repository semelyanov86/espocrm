<?php

namespace Espo\Modules\Itvolga\Classes\ConsoleCommands;

use Espo\Core\Console\Command;
use Espo\Core\Console\Command\Params;
use Espo\Core\Console\IO;
use Espo\Core\Utils\Config;
use Espo\Core\Utils\Config\ConfigWriter;
use Espo\Core\Utils\Metadata;
use Espo\Entities\Role;
use Espo\Entities\Team;
use Espo\Modules\Itvolga\Tools\Acl\HierarchyTeams;
use Espo\ORM\EntityManager;

/**
 * Idempotent setup of access control (stage 03: decisions D-22, D-06, D-39; finance documents: stage 04.2):
 * teams of the Vtiger groups and hierarchy teams, the roles of the four used Vtiger profiles, the separate
 * role «Доступы» for ContactAccess, team membership of existing users by role, and the navigation tabs.
 *
 *   task espo -- itvolga-setup-acl            apply
 *   task espo -- itvolga-setup-acl --dry-run  show what would change
 *
 * Levels follow the Vtiger organisation-wide sharing (vtiger_def_org_share): Private modules → `team` (the deputy reads
 * all records of its modules, owner decision Q-34)
 * (owner + members of the record's teams: group teams and hierarchy teams), Public → `all`; modules hidden
 * in a profile (vtiger_profile2tab) → no access; denied standard actions (vtiger_profile2standardpermissions)
 * → `no`. Historic Project/ProjectTask and VtigerArchive are read-only for every role (module-decisions.md).
 * EspoCRM 10 denies every scope that no role grants, so ContactAccess is closed to all users without
 * «Доступы» (administrators excepted: they bypass ACL, reveals are still logged).
 * Finance documents (Quotes and SalesOrder are Private in Vtiger and hidden in every profile but the director's):
 * the director gets them; their items are read with the document's level (FinanceItem access checker) and are never
 * written directly; the legal entity is read-only for the director (requisites are kept by the administrator).
 */
class SetupAcl implements Command
{
    private const FULL = ['create' => 'yes', 'read' => 'all', 'edit' => 'all', 'delete' => 'all', 'stream' => 'all'];
    private const TEAM = ['create' => 'yes', 'read' => 'team', 'edit' => 'team', 'delete' => 'team', 'stream' => 'team'];
    private const PUBLIC = self::FULL;
    private const READ_ALL = ['create' => 'no', 'read' => 'all', 'edit' => 'no', 'delete' => 'no', 'stream' => 'all'];
    private const READ_TEAM = ['create' => 'no', 'read' => 'team', 'edit' => 'no', 'delete' => 'no', 'stream' => 'team'];
    /** Private module for the deputy (owner decision Q-34): reads all records, edits as Vtiger sharing allowed. */
    private const READ_ALL_EDIT_TEAM = ['create' => 'yes', 'read' => 'all', 'edit' => 'team', 'delete' => 'team',
        'stream' => 'all'];

    /** Scopes every working role needs regardless of its modules. */
    private const COMMON = [
        'Activities' => true,
        'Calendar' => true,
        'EmailAccountScope' => true,
        'Import' => true,
        'User' => ['read' => 'all', 'edit' => 'no'],
        'Team' => ['read' => 'all'],
        'DocumentFolder' => ['create' => 'no', 'read' => 'all', 'edit' => 'no', 'delete' => 'no'],
        'KnowledgeBaseCategory' => ['create' => 'no', 'read' => 'all', 'edit' => 'no', 'delete' => 'no'],
    ];

    private const PERMISSIONS = [
        'assignmentPermission' => 'all',
        'userPermission' => 'all',
        'messagePermission' => 'all',
        'portalPermission' => 'no',
        'groupEmailAccountPermission' => 'no',
        'exportPermission' => 'yes',
        'massUpdatePermission' => 'yes',
        'dataPrivacyPermission' => 'no',
        'followerManagementPermission' => 'no',
        'auditPermission' => 'no',
        'mentionPermission' => 'all',
        'userCalendarPermission' => 'team',
        'lockPermission' => 'no',
    ];

    public const TABS = ['Vendor', 'Product', 'Quote', 'SalesOrder', 'Project', 'ProjectTask', 'VtigerArchive',
        'ContactAccess'];

    /** Finance scopes of stage 04.2: closed to every role that does not list them. */
    private const FINANCE = ['Quote', 'SalesOrder', 'QuoteItem', 'SalesOrderItem', 'LegalEntity'];

    public function __construct(
        private EntityManager $entityManager,
        private Metadata $metadata,
        private Config $config,
        private ConfigWriter $configWriter,
        private HierarchyTeams $hierarchyTeams,
    ) {}

    /**
     * @return array<string, array{data: array<string, mixed>, permissions: array<string, string>}>
     */
    public static function roleDefinitions(): array
    {
        $director = [
            'Account' => self::FULL, 'Contact' => self::FULL, 'Lead' => self::FULL, 'Opportunity' => self::FULL,
            'Task' => self::FULL, 'Call' => self::FULL, 'Meeting' => self::FULL, 'Email' => self::FULL,
            'Case' => self::FULL, 'KnowledgeBaseArticle' => self::FULL, 'Document' => self::FULL,
            'Vendor' => self::FULL, 'Product' => self::FULL,
            'Project' => self::READ_ALL, 'ProjectTask' => self::READ_ALL, 'VtigerArchive' => ['read' => 'all'],
            'DocumentFolder' => self::FULL, 'KnowledgeBaseCategory' => self::FULL,
            'GlobalStream' => true,
            'Quote' => self::FULL, 'SalesOrder' => self::FULL,
            'QuoteItem' => ['read' => 'all'], 'SalesOrderItem' => ['read' => 'all'],
            'LegalEntity' => ['read' => 'all', 'edit' => 'no'],
        ];
        // Vtiger profile «Заместитель директора+Профиль»: hidden Leads, Potentials, Vendors, Assets, Consignment,
        // ServiceContracts and all finance; Faq delete denied; PBXManager edit/delete denied (Call access checker).
        // Private modules: all records readable (owner decision 2026-09-30, Q-34), editing as the Vtiger sharing.
        $deputy = [
            'Account' => self::READ_ALL_EDIT_TEAM, 'Contact' => self::READ_ALL_EDIT_TEAM,
            'Task' => self::READ_ALL_EDIT_TEAM, 'Call' => self::READ_ALL_EDIT_TEAM,
            'Meeting' => self::READ_ALL_EDIT_TEAM, 'Email' => self::READ_ALL_EDIT_TEAM,
            'Case' => self::READ_ALL_EDIT_TEAM, 'Document' => self::READ_ALL_EDIT_TEAM,
            'KnowledgeBaseArticle' => ['delete' => 'no'] + self::PUBLIC,
            'Product' => self::PUBLIC,
            'Project' => self::READ_ALL, 'ProjectTask' => self::READ_ALL,
            'Lead' => false, 'Opportunity' => false, 'Vendor' => false, 'VtigerArchive' => false,
        ];
        // «Менеджер по Продажам+Профиль»: hidden Accounts, Contacts, Documents, Faq, HelpDesk, Potentials, Project(Task),
        // Vendors and all finance.
        $sales = [
            'Lead' => self::PUBLIC, 'Task' => self::TEAM, 'Call' => self::TEAM, 'Meeting' => self::TEAM,
            'Email' => self::TEAM, 'Product' => self::PUBLIC,
            'Account' => false, 'Contact' => false, 'Document' => false, 'KnowledgeBaseArticle' => false,
            'Case' => false, 'Opportunity' => false, 'Project' => false, 'ProjectTask' => false, 'Vendor' => false,
            'VtigerArchive' => false, 'DocumentFolder' => false, 'KnowledgeBaseCategory' => false,
        ];
        // «Менеджер клиентов+Профиль»: hidden Accounts, Contacts, Emails, Leads, PBXManager, Potentials, Vendors, Assets,
        // Consignment, ServiceContracts and all finance; Project/ProjectTask delete denied (archive: read-only anyway).
        $customer = [
            'Task' => self::TEAM, 'Call' => self::TEAM, 'Meeting' => self::TEAM, 'Case' => self::TEAM,
            'Document' => self::TEAM, 'KnowledgeBaseArticle' => self::PUBLIC, 'Product' => self::PUBLIC,
            'Project' => self::READ_TEAM, 'ProjectTask' => self::READ_TEAM,
            'Account' => false, 'Contact' => false, 'Email' => false, 'Lead' => false, 'Opportunity' => false,
            'Vendor' => false, 'VtigerArchive' => false,
        ];
        $roles = [
            'Директор' => [$director, ['userCalendarPermission' => 'all',
                'followerManagementPermission' => 'all', 'auditPermission' => 'yes',
                'groupEmailAccountPermission' => 'all']],
            'Заместитель директора' => [$deputy, []],
            'Менеджер по продажам' => [$sales, []],
            'Менеджер клиентов' => [$customer, []],
        ];
        $result = [];

        foreach ($roles as $name => [$data, $permissions]) {
            $data = $data + self::COMMON + array_fill_keys(self::FINANCE, false);
            $data['ContactAccess'] = false;
            $result[$name] = ['data' => $data, 'permissions' => $permissions + self::PERMISSIONS];
        }

        // Granted explicitly to the people who administer remote access (D-06); combined with a working role.
        $result['Доступы'] = [
            'data' => ['ContactAccess' => ['create' => 'yes', 'read' => 'all', 'edit' => 'all', 'delete' => 'all',
                'stream' => 'no']],
            'permissions' => array_map(fn () => 'not-set', self::PERMISSIONS),
        ];

        return $result;
    }

    public function run(Params $params, IO $io): void
    {
        $dryRun = $params->hasFlag('dryRun');
        $changes = [];

        $teamNames = array_merge(
            $this->metadata->get(['app', 'itvolgaAcl', 'groupTeams']) ?? [],
            array_map(fn ($r) => $r['team'], $this->metadata->get(['app', 'itvolgaAcl', 'hierarchyTeams']) ?? [])
        );

        foreach (array_unique($teamNames) as $name) {
            if (!$this->entityManager->getRDBRepositoryByClass(Team::class)->where(['name' => $name])->findOne()) {
                $changes[] = "team + $name";

                if (!$dryRun) {
                    $this->entityManager->createEntity(Team::ENTITY_TYPE, ['name' => $name]);
                }
            }
        }

        foreach (self::roleDefinitions() as $name => $definition) {
            $role = $this->entityManager->getRDBRepositoryByClass(Role::class)->where(['name' => $name])->findOne();
            $isNew = !$role;

            if (!$role) {
                $role = $this->entityManager->getRDBRepositoryByClass(Role::class)->getNew();
                $role->set('name', $name);
            }

            $data = json_decode(json_encode($definition['data'], JSON_THROW_ON_ERROR));
            $role->set('data', $data);
            $role->set('fieldData', (object) []);
            $role->setMultiple($definition['permissions']);

            if ($isNew || $role->isAttributeChanged('data') || $this->permissionsChanged($role, $definition['permissions'])) {
                $changes[] = ($isNew ? "role + " : "role ~ ") . $name;

                if (!$dryRun) {
                    $this->entityManager->saveEntity($role);
                }
            }
        }

        if (!$dryRun) {
            $changes = array_merge($changes, $this->hierarchyTeams->syncAllUsers());
        }

        $tabList = $this->config->get('tabList') ?? [];
        $missingTabs = array_values(array_filter(self::TABS, fn ($t) => !in_array($t, $tabList, true)));

        if ($missingTabs) {
            $changes[] = 'tabs + ' . implode(', ', $missingTabs);

            if (!$dryRun) {
                $this->configWriter->set('tabList', array_merge($tabList, $missingTabs));
                $this->configWriter->save();
            }
        }

        $io->writeLine(($dryRun ? '[dry-run] ' : '') . ($changes ? implode("\n", $changes) : 'no changes'));
    }

    /**
     * @param array<string, string> $permissions
     */
    private function permissionsChanged(Role $role, array $permissions): bool
    {
        foreach (array_keys($permissions) as $attribute) {
            if ($role->isAttributeChanged($attribute)) {
                return true;
            }
        }

        return false;
    }
}
