<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePrint;

use Espo\Core\Acl;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Modules\Itvolga\Tools\Finance\Printing\Presenter;
use Espo\Modules\Itvolga\Tools\FinanceDocument\DocumentTypes;
use Espo\ORM\Entity;
use Espo\ORM\EntityManager;
use Espo\Tools\Pdf\Builder;
use Espo\Tools\Pdf\Data;
use Espo\Tools\Pdf\Params;

/**
 * Print form of a finance record as a PDF (stage 05, D-79): the registered form of the entity type, read access to the
 * record (and, in PrintData, to its account and legal entity), the form's condition (PKO: incoming payments only).
 * The values are read in one transaction so the header and the lines come from one state of the document; nothing is
 * written. The PDF is made by the core Dompdf engine from the module template files (CodeTemplate).
 */
class PrintService
{
    private const ENGINE = 'Dompdf';
    /** Root key of the view model in the template data: no attribute or link of the printed entities has this name. */
    public const DATA_KEY = 'form';

    public function __construct(
        private EntityManager $entityManager,
        private Acl $acl,
        private PrintForms $printForms,
        private DocumentTypes $documentTypes,
        private PrintData $printData,
        private Builder $builder,
    ) {}

    /**
     * @throws NotFound no print form for the entity type, no record
     * @throws Forbidden no read access; the record does not meet the form's condition
     */
    public function print(string $entityType, string $id): PrintResult
    {
        $form = $this->printForms->find($entityType) ?? throw new NotFound("No print form for '$entityType'.");

        [$record, $view] = $this->entityManager->getTransactionManager()->run(
            fn () => $this->read($form, $id)
        );

        $template = CodeTemplate::load($form, $form->title . ' ' . $view['number']);

        $contents = $this->builder
            ->setTemplate($template)
            ->setEngine(self::ENGINE)
            ->build()
            ->printEntity(
                $record,
                Params::create()->withAcl(),
                Data::create()->withAdditionalTemplateData((object) [self::DATA_KEY => $view])
            );

        return new PrintResult($contents, $form->title . ' ' . $view['number'] . '.pdf');
    }

    /**
     * @return array{Entity, array<string, mixed>}
     * @throws NotFound
     * @throws Forbidden
     */
    private function read(PrintForm $form, string $id): array
    {
        $record = $this->entityManager->getEntityById($form->entityType, $id)
            ?? throw new NotFound('Record not found.');

        if (!$this->acl->checkEntityRead($record)) {
            throw new Forbidden('No read access to the record.');
        }

        if (!$form->accepts($record)) {
            throw new Forbidden('The record has no print form in its current state.');
        }

        $documentType = $this->documentTypes->find($form->entityType);

        $view = $documentType
            ? Presenter::document($this->printData->document($record, $documentType, $form))
            : Presenter::cashReceipt($this->printData->payment($record, $form));

        return [$record, $view];
    }
}
