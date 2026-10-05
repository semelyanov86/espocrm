<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Mailing;

use Espo\Core\Mail\EmailSender;
use Espo\Core\Mail\Exceptions\NoSmtp;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Core\Utils\Log;
use Espo\Entities\Attachment;
use Espo\Entities\Email;
use Espo\ORM\EntityManager;
use Throwable;

/**
 * One letter of a report (D-123): a core Email record to one address with its files as child attachments, sent by the
 * core sender. Without SMTP the letter and its files stay saved with the status «Failed» — the job goes on; a send
 * error leaves «Failed» too. No retries. The letter is created by the acting (system) user and linked by the core to
 * the users of its address only: the sender address (the system one, set by the core sender) is not kept as the `from`
 * attribute, so a user owning that address is not linked to every report letter (internal review, D-124); the shown
 * sender stays in `fromString`.
 */
final class LetterSender
{
    public const SENT = 'sent';
    public const NO_SMTP = 'noSmtp';
    public const FAILED = 'failed';

    public function __construct(
        private readonly EntityManager $entityManager,
        private readonly EmailSender $emailSender,
        private readonly Log $log,
    ) {}

    /**
     * @param list<Attachment> $attachments stored files with the role «Attachment», not yet of a letter
     * @return self::SENT|self::NO_SMTP|self::FAILED
     */
    public function send(string $address, string $subject, string $html, array $attachments): string
    {
        $email = $this->entityManager->getRDBRepositoryByClass(Email::class)->getNew();
        $email
            ->setSubject($subject)
            ->setBody($html)
            ->setIsHtml()
            ->addToAddress($address)
            ->setAttachmentIdList(array_map(fn (Attachment $a) => $a->getId(), $attachments));

        if (!$this->emailSender->hasSystemSmtp()) {
            $email->setStatus(Email::STATUS_FAILED);
            $this->save($email, [SaveOption::SILENT => true]);

            return self::NO_SMTP;
        }

        // With a Message-ID the core sender does not save the letter itself (after it set the sender address).
        $email
            ->setMessageId('<' . EmailSender::generateMessageId($email) . '>')
            ->setStatus(Email::STATUS_SENDING);
        $this->save($email, [SaveOption::SILENT => true]);

        try {
            $this->emailSender->create()->send($email);
        } catch (Throwable $e) {
            $email->setStatus(Email::STATUS_FAILED);
            $this->save($email, [SaveOption::SILENT => true]);
            // The class only: a message of a transport may carry the address.
            $this->log->warning('Report letter not sent: ' . $e::class);

            return $e instanceof NoSmtp ? self::NO_SMTP : self::FAILED;
        }

        $this->save($email, [Email::SAVE_OPTION_IS_JUST_SENT => true]);

        return self::SENT;
    }

    /**
     * @param array<string, mixed> $options
     */
    private function save(Email $email, array $options): void
    {
        // The core links the users of a `from` address to the letter; the sender is the system, not a user.
        $email->clear('from');
        $this->entityManager->saveEntity($email, $options);
    }
}
