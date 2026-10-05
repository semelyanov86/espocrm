<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Export;

use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Entities\Attachment;
use Espo\ORM\EntityManager;

/**
 * Stores report files as attachments (D-116, D-123). The creator is the user whose rights made the file: with no
 * parent he alone downloads it (the core ACL of an attachment falls back to `createdBy`).
 *
 *  - exportFile — a download (role «Export File», removed by the core cleanup after its period);
 *  - mailFile — a file of a letter (role «Attachment», field `attachments`; the Email becomes its parent when saved
 *    with the ids); copy() — the same stored file for another letter (one file in the storage, D-123).
 */
final class AttachmentStore
{
    public function __construct(private readonly EntityManager $entityManager) {}

    public function exportFile(ExportFile $file, string $createdById): Attachment
    {
        return $this->store($file, Attachment::ROLE_EXPORT_FILE, null, $createdById);
    }

    public function mailFile(ExportFile $file, string $createdById): Attachment
    {
        return $this->store($file, Attachment::ROLE_ATTACHMENT, 'attachments', $createdById);
    }

    public function copy(Attachment $attachment, string $createdById): Attachment
    {
        $copy = $this->entityManager->getRDBRepositoryByClass(Attachment::class)->getNew();
        $copy
            ->setSourceId($attachment->getSourceId())
            ->setName($attachment->getName())
            ->setType($attachment->getType())
            ->setSize($attachment->getSize())
            ->setRole($attachment->getRole())
            ->setTargetField($attachment->getTargetField());
        $this->entityManager->saveEntity($copy, [SaveOption::CREATED_BY_ID => $createdById]);

        return $copy;
    }

    private function store(ExportFile $file, string $role, ?string $field, string $createdById): Attachment
    {
        $attachment = $this->entityManager->getRDBRepositoryByClass(Attachment::class)->getNew();
        $attachment
            ->setName($file->name)
            ->setType($file->mimeType)
            ->setRole($role)
            ->setTargetField($field)
            ->setContents($file->contents);
        $this->entityManager->saveEntity($attachment, [SaveOption::CREATED_BY_ID => $createdById]);

        return $attachment;
    }
}
