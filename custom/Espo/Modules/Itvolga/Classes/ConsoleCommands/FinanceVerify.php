<?php

namespace Espo\Modules\Itvolga\Classes\ConsoleCommands;

use Espo\Core\Console\Command;
use Espo\Core\Console\Command\Params;
use Espo\Core\Console\IO;
use Espo\Core\Exceptions\Error;
use Espo\Core\ORM\Repository\Option\SaveOption;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentProcessor;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentType;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\Modules\Itvolga\Tools\FinanceDocument\SourceMarks;
use Espo\Modules\Itvolga\Tools\FinanceDocument\SourceVerification;
use Espo\ORM\EntityManager;

/**
 * Source marks of imported documents (D-46, SourceMarks): `sourceFormula`, `totalsCheck` and the core recomputation
 * of the totals («Пересчёт ядра») — the step the importer (stage 06.3) runs after it has written a document with its
 * items. SourceVerifier classifies the stored totals, which are not changed (D-05). The marks are saved with the import
 * option, so the source legal entity is resolved again (an unknown spcompany stops the run, D-48). Documents
 * recalculated in EspoCRM (vtigerData.sourceTotals) are skipped. Prints counts only.
 *
 *   task espo -- itvolga-finance-verify [--entity=Invoice] [--id=<id>[,<id>…]] [--dry-run]
 */
class FinanceVerify implements Command
{
    public function __construct(
        private EntityManager $entityManager,
        private DocumentTypes $types,
        private DocumentProcessor $processor,
        private SourceVerification $verification,
    ) {}

    public function run(Params $params, IO $io): void
    {
        $only = $params->getOption('entity');
        $ids = array_values(array_filter(explode(',', (string) $params->getOption('id'))));
        $dryRun = $params->hasFlag('dryRun');
        $types = array_filter($this->types->all(), fn ($type) => $only === null || $type->entityType === $only);

        if ($types === []) {
            throw new Error("Unknown finance document '$only'.");
        }

        foreach ($types as $type) {
            $counts = [];
            $count = function (string $key) use (&$counts): void {
                $counts[$key] = ($counts[$key] ?? 0) + 1;
            };
            $where = ['vtigerId!=' => null];

            if ($ids !== []) {
                $where['id'] = $ids;
            }

            $documents = $this->entityManager->getRDBRepository($type->entityType)->where($where)->find();

            foreach ($documents as $listed) {
                // Locked and re-read: a concurrent recalculation (D-51) is never followed by stale source marks.
                $this->entityManager->getTransactionManager()->run(
                    fn () => $count($this->verifyOne($type, (string) $listed->getId(), $dryRun)));
            }

            ksort($counts);
            $summary = $counts === [] ? 'no imported documents'
                : implode(', ', array_map(fn ($key, $n) => "$key — $n", array_keys($counts), $counts));
            $io->writeLine(($dryRun ? '[dry-run] ' : '') . "{$type->entityType}: $summary");
        }
    }

    /**
     * @return string the count key of the outcome
     */
    private function verifyOne(DocumentType $type, string $id, bool $dryRun): string
    {
        $document = $this->entityManager
            ->getRDBRepository($type->entityType)
            ->where(['id' => $id])
            ->forUpdate()
            ->findOne();

        if (!$document) {
            return 'removed meanwhile (skipped)';
        }

        if (!$this->processor->hasSourceTotals($document)) {
            return 'recalculated in EspoCRM (skipped)';
        }

        $result = $this->verification->verify($document, $type);

        if (!$result) {
            return 'no region_id in vtigerData (skipped)';
        }

        $marks = SourceMarks::of($result);

        if (!$dryRun) {
            $document->set($marks);
            // Import option: the stored totals and items stay as they are (no recalculation, no number).
            $this->entityManager->saveEntity($document, [SaveOption::IMPORT => true, SaveOption::SILENT => true]);
        }

        return "{$marks['sourceFormula']} / {$marks['totalsCheck']}";
    }
}
