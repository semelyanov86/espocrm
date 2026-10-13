<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Entities\User;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use stdClass;

/**
 * Call cards of the current user for the popup notifications (D-170). The listener decides who gets a card and its
 * state; this service shows only what the viewer may read: the Call link only with read access to the call, each
 * client only with read access to it (a hidden client is not even counted). A card in progress stays while the call
 * lasts (at most 4 h without a change: a lost listener), an ended one 30 min, a closed one is shown for 2 min so that
 * every open tab removes it; a dismissed card never comes back unless the call becomes active again for this user.
 */
class CardService
{
    private const ACTIVE = ['ringing', 'dialing', 'talking'];
    private const ACTIVE_MAX = 4 * 3600;
    private const ENDED_FOR = 30 * 60;
    private const CLOSED_FOR = 120;
    private const CLIENTS_SHOWN = 10;

    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private User $user,
        private TelephonyConfig $config,
    ) {}

    /**
     * @return list<array{id: string, data: stdClass}>
     */
    public function list(): array
    {
        if (!$this->config->isEnabled() || $this->user->isPortal()) {
            return [];
        }

        $now = time();
        $cards = $this->entityManager->getRDBRepository('TelephonyCard')
            ->where([
                'userId' => $this->user->getId(),
                'dismissed' => false,
                'modifiedAt>' => gmdate('Y-m-d H:i:s', $now - self::ACTIVE_MAX),
            ])
            ->order('createdAt', 'DESC')
            ->limit(0, 10)
            ->find();

        $out = [];

        foreach ($cards as $card) {
            $age = $now - (int) strtotime($card->get('modifiedAt') . ' UTC');
            $state = (string) $card->get('state');

            if (($state === 'ended' && $age > self::ENDED_FOR) || ($state === 'closed' && $age > self::CLOSED_FOR)) {
                continue;
            }

            if (!in_array($state, [...self::ACTIVE, 'ended', 'closed'], true)) {
                continue;
            }

            $out[] = ['id' => $card->getId(), 'data' => $this->data($card)];
        }

        return $out;
    }

    /**
     * @throws NotFound not a card of the current user
     */
    public function dismiss(string $id): void
    {
        $card = $this->entityManager->getRDBRepository('TelephonyCard')
            ->where(['id' => $id, 'userId' => $this->user->getId()])
            ->findOne();

        if (!$card) {
            throw new NotFound();
        }

        if (!$card->get('dismissed')) {
            $card->set('dismissed', true);
            $this->entityManager->saveEntity($card, [SaveOption::SILENT => true]);
        }
    }

    private function data(Entity $card): stdClass
    {
        $call = null;
        $callId = $card->get('callId');

        if ($callId) {
            $entity = $this->entityManager->getEntityById('Call', $callId);

            if ($entity && $this->acl->checkEntityRead($entity)) {
                $call = (object) ['id' => $entity->getId(), 'name' => $entity->get('name')];
            }
        }

        $clients = [];
        $exactVisible = false;

        foreach ((array) $card->get('matches') as $match) {
            $match = (array) $match;
            $type = $match['entityType'] ?? null;
            $id = $match['id'] ?? null;

            if (!in_array($type, ClientLookup::TYPES, true) || !is_string($id)
                || !$this->acl->checkScope($type, Table::ACTION_READ)) {
                continue;
            }

            $entity = $this->entityManager->getEntityById($type, $id);

            if (!$entity || !$this->acl->checkEntityRead($entity)) {
                continue;
            }

            $possible = (bool) ($match['possible'] ?? false);
            $exactVisible = $exactVisible || !$possible;
            $client = ['entityType' => $type, 'id' => $id, 'name' => (string) $entity->get('name'), 'possible' => $possible];

            if ($type === 'Contact' && $entity->get('accountId') && $this->acl->checkScope('Account', Table::ACTION_READ)) {
                $account = $this->entityManager->getEntityById('Account', $entity->get('accountId'));

                if ($account && $this->acl->checkEntityRead($account)) {
                    $client['accountName'] = (string) $account->get('name');
                }
            }

            $clients[] = (object) $client;

            if (count($clients) >= self::CLIENTS_SHOWN) {
                break;
            }
        }

        return (object) [
            'state' => $card->get('state'),
            'direction' => $card->get('direction'),
            'number' => $card->get('number'),
            'viaCrm' => (bool) $card->get('viaCrm'),
            'startedAt' => $card->get('startedAt'),
            'answeredAt' => $card->get('answeredAt'),
            'endedAt' => $card->get('endedAt'),
            'call' => $call,
            'clients' => $clients,
            'canCreateContact' => !$exactVisible && $this->acl->checkScope('Contact', Table::ACTION_CREATE),
            'canCreateLead' => !$exactVisible && $this->acl->checkScope('Lead', Table::ACTION_CREATE),
        ];
    }
}
