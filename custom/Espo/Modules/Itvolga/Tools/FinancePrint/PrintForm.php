<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePrint;

use Espo\ORM\Entity;

/**
 * The print form of a finance record, as registered in metadata app.itvolgaFinance.printForms (stage 05, D-79).
 */
final class PrintForm
{
    /**
     * @param array<string, scalar> $onlyWhen attribute values a record needs to be printed (PKO: incoming payments)
     */
    public function __construct(
        public readonly string $entityType,
        /** Body: Resources/printForms/<template>.html. */
        public readonly string $template,
        /** CSS: Resources/printForms/<style>.css (with common.css). */
        public readonly string $style,
        /** Inline partials shared by forms: Resources/printForms/<partials>.html, put before the body. */
        public readonly ?string $partials,
        /** File name prefix: «Счёт С-637.pdf». */
        public readonly string $title,
        /** The printed document date; a date-time field prints its calendar date in the system time zone. */
        public readonly string $dateField,
        public readonly ?string $extraDateField,
        public readonly array $onlyWhen,
    ) {}

    public function accepts(Entity $record): bool
    {
        foreach ($this->onlyWhen as $attribute => $value) {
            if ($record->get($attribute) !== $value) {
                return false;
            }
        }

        return true;
    }
}
