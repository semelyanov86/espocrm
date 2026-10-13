<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony;

use Espo\Core\Acl;
use Espo\Core\Acl\Table;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Error\Body;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\ServiceUnavailable;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Tools\FinanceDocument\RowLock;
use Espo\Modules\Itvolga\Tools\Telephony\Core\PhoneNumbers;
use Espo\ORM\EntityManager;
use InvalidArgumentException;

/**
 * Click-to-call (D-170): rings the user's own desk phone through AMI Originate (the dialer user may only originate);
 * once the user picks up, the dialplan context of the desk phones dials the number exactly as if the user had dialled
 * it — the caller id stays the extension, so the trunk choice is the same as for a manual call. The extension comes
 * from the user record (only administrators set it), the number must be one the dialplan accepts. The request is
 * stored first (TelephonyCallIntent): its id is the Originate ChannelId, by which the listener links the call and
 * the record the user called from. At most one request per user every 5 s.
 */
class DialService
{
    private const PARENT_TYPES = ['Account', 'Contact', 'Lead', 'Opportunity', 'Case', 'Invoice'];
    private const GAP = 5;

    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private User $user,
        private TelephonyConfig $config,
        private ExtensionDirectory $directory,
        private RowLock $rowLock,
    ) {}

    /**
     * @return array{intentId: string, extension: string}
     * @throws BadRequest
     * @throws Forbidden
     * @throws ServiceUnavailable
     */
    public function dial(string $number, ?string $parentType, ?string $parentId): array
    {
        $address = $this->config->amiAddress();
        $credentials = $this->config->credentials('dialer');

        if (!$this->config->isEnabled() || $address === null || $credentials === null) {
            throw ServiceUnavailable::createWithBody('telephonyDisabled', self::body('telephonyDisabled'));
        }

        if ($this->user->isPortal() || $this->user->isApi() || !$this->acl->checkScope('Call', Table::ACTION_CREATE)) {
            throw new Forbidden();
        }

        try {
            $settings = $this->config->trackerSettings();
        } catch (InvalidArgumentException) {
            throw ServiceUnavailable::createWithBody('telephonyDisabled', self::body('telephonyDisabled'));
        }

        $extension = trim((string) $this->user->get('cPhoneExtension'));

        if (!$settings->isExtension($extension) || $this->directory->userId($extension) !== $this->user->getId()) {
            throw Forbidden::createWithBody('telephonyNoExtension', self::body('telephonyNoExtension'));
        }

        $dial = PhoneNumbers::dialString($number, $settings->localAreaCode);

        if ($dial === null) {
            throw BadRequest::createWithBody('telephonyNumberRefused', self::body('telephonyNumberRefused'));
        }

        [$parentType, $parentId] = $this->parent($parentType, $parentId);

        $intent = $this->entityManager->getTransactionManager()->run(function () use ($extension, $dial, $parentType, $parentId) {
            $this->rowLock->one(User::ENTITY_TYPE, $this->user->getId());

            $recent = $this->entityManager->getRDBRepository('TelephonyCallIntent')
                ->where(['userId' => $this->user->getId(), 'createdAt>' => gmdate('Y-m-d H:i:s', time() - self::GAP)])
                ->count();

            if ($recent > 0) {
                throw Forbidden::createWithBody('telephonyRateLimited', self::body('telephonyRateLimited'));
            }

            $intent = $this->entityManager->getNewEntity('TelephonyCallIntent');
            $intent->setMultiple([
                'userId' => $this->user->getId(),
                'extension' => $extension,
                'number' => $dial,
                'parentType' => $parentType,
                'parentId' => $parentId,
                'status' => 'queued',
            ]);
            $this->entityManager->saveEntity($intent, [SaveOption::SILENT => true]);

            return $intent;
        });

        try {
            $ami = AmiConnection::open($address, $credentials, false);
            $response = $ami->request('Originate', [
                'Channel' => 'PJSIP/' . $extension,
                'Context' => $this->config->dialContext(),
                'Exten' => $dial,
                'Priority' => '1',
                'CallerID' => $this->config->callerId($extension),
                'Timeout' => (string) $this->config->originateTimeoutMs(),
                'Async' => 'true',
                'ChannelId' => $settings->originatePrefix . $intent->getId(),
            ], 5.0);
            $ami->close();
            $accepted = strcasecmp((string) $response->response(), 'Success') === 0;
        } catch (AmiError) {
            $accepted = false;
        }

        if (!$accepted) {
            $intent->set('status', 'failed');
            $this->entityManager->saveEntity($intent, [SaveOption::SILENT => true]);

            throw ServiceUnavailable::createWithBody('telephonyPbxUnavailable', self::body('telephonyPbxUnavailable'));
        }

        return ['intentId' => $intent->getId(), 'extension' => $extension];
    }

    /**
     * The record the user called from, kept only when the user may read it.
     *
     * @return array{?string, ?string}
     */
    private function parent(?string $type, ?string $id): array
    {
        if (!$type || !$id || !in_array($type, self::PARENT_TYPES, true) || !$this->acl->checkScope($type, Table::ACTION_READ)) {
            return [null, null];
        }

        $entity = $this->entityManager->getEntityById($type, $id);

        return $entity && $this->acl->checkEntityRead($entity) ? [$type, $id] : [null, null];
    }

    private static function body(string $label): Body
    {
        return Body::create()->withMessageTranslation($label, 'Call');
    }
}
