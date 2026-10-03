<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\FinancePrint;

use Espo\Core\Utils\Metadata;

/**
 * Registry of the print forms (metadata app.itvolgaFinance.printForms, stage 05): one form per finance entity type.
 */
class PrintForms
{
    /** Names of the template files: no path, no dots. */
    private const FILE_NAME = '/^[a-z][a-z-]*$/';

    public function __construct(private Metadata $metadata) {}

    public function find(string $entityType): ?PrintForm
    {
        $defs = $this->metadata->get(['app', 'itvolgaFinance', 'printForms', $entityType]);

        if (!is_array($defs)) {
            return null;
        }

        $template = (string) ($defs['template'] ?? '');
        $style = (string) ($defs['style'] ?? $template);
        $partials = $defs['partials'] ?? null;

        foreach ([$template, $style, $partials ?? 'none'] as $name) {
            if (!preg_match(self::FILE_NAME, (string) $name)) {
                return null;
            }
        }

        return new PrintForm(
            $entityType,
            $template,
            $style,
            $partials,
            $defs['title'],
            $defs['dateField'],
            $defs['extraDateField'] ?? null,
            $defs['onlyWhen'] ?? [],
        );
    }
}
