<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Mailing;

use Espo\Core\AclManager;
use Espo\Core\Select\SelectBuilderFactory;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Tools\Report\Core\Info\ConditionText;
use Espo\Modules\Itvolga\Tools\Report\Core\Mailing\MailingSettings;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContext;
use Espo\Modules\Itvolga\Tools\Report\Query\ReportQuery;
use Espo\Modules\Itvolga\Tools\Report\Run\Labels;
use Espo\ORM\EntityManager;

/**
 * «Сведения об отчёте» of a letter (reports.md §13, D-124) for the user the report was run for — the owner for a
 * mailing with his rights, each recipient for «generate for», the requester for a background export: the definition
 * as his schema parsed it (labels in his language), the owner and the conditions with names of records he may read,
 * the limits, the schedule and the record count of his result. Nothing comes from the interface state of the author.
 */
final class ReportInfo
{
    public function __construct(
        private readonly EntityManager $entityManager,
        private readonly SelectBuilderFactory $selectBuilderFactory,
        private readonly MailingClock $clock,
        private readonly AclManager $aclManager,
    ) {}

    /**
     * @param array<string, mixed> $result
     * @return list<array{string, string}>
     */
    public function lines(Report $report, ReportQuery $query, array $result, FormatContext $context,
        ?MailingSettings $settings): array
    {
        $language = $context->language;
        $definition = $query->definition;
        $field = fn (string $name) => $language->translate($name, 'fields', 'Report');
        $label = fn (string $name) => $language->translateLabel($name, 'labels', 'Report');
        $words = new LanguageConditionWords($context, new Labels($language, $definition), $definition->entityType,
            $query->user, $this->selectBuilderFactory, $this->entityManager, $this->aclManager);
        $join = fn (array $items, string $glue) => implode($glue, array_map(fn ($i) => (string) $i['label'], $items));

        $lines = [
            [$label('Report'), (string) $report->get('name')],
            [$field('entityType'), (string) $language->translate($definition->entityType, 'scopeNamesPlural')],
            [$field('type'), (string) $language->translateOption($definition->type->value, 'type', 'Report')],
            [$field('assignedUser'), $this->ownerName($report, $query->user, $label('noAccessRecord'))],
        ];

        if (($result['groups'] ?? []) !== []) {
            $lines[] = [$field('groups'), $join($result['groups'], ' → ')];
        }

        if (($result['columns'] ?? []) !== []) {
            $lines[] = [$field('columns'), $join($result['columns'], ', ')];
        }

        if (($result['aggregates'] ?? []) !== []) {
            $lines[] = [$field('aggregates'), $join($result['aggregates'], ', ')];
        }

        $conditions = ConditionText::describe($definition->filters, $definition->filterFields, $words);
        $lines[] = [$label('Conditions'), $conditions !== '' ? $conditions : '—'];

        $limits = [];

        if ($query->options->noLimit) {
            $limits[] = $label('noLimits');
        } else {
            if ($definition->rowLimit !== null) {
                $limits[] = $field('rowLimit') . ': ' . $definition->rowLimit;
            }

            if ($definition->groupLimit !== null) {
                $limits[] = $field('groupLimit') . ': ' . $definition->groupLimit;
            }
        }

        if ($limits !== []) {
            $lines[] = [$label('Limits'), implode('; ', $limits)];
        }

        if ($settings !== null) {
            $lines[] = [$field('mailing'), $this->clock->summary($settings, $language,
                $report->get('assignedUserId') ? (string) $report->get('assignedUserId') : null)];
        }

        $lines[] = [$label('Total records'), (string) ($result['recordCount'] ?? 0)];

        return $lines;
    }

    /**
     * The owner's name only when the reader may read that user and his name (external review 05.3 B3).
     */
    private function ownerName(Report $report, User $reader, string $noAccess): string
    {
        $ownerId = $report->get('assignedUserId');
        $owner = $ownerId ? $this->entityManager->getRDBRepositoryByClass(User::class)->getById((string) $ownerId) : null;

        if (!$owner) {
            return '';
        }

        return $this->aclManager->checkEntityRead($reader, $owner) &&
            !in_array('name', $this->aclManager->getScopeForbiddenFieldList($reader, User::ENTITY_TYPE), true) ?
            (string) $owner->get('name') : $noAccess;
    }
}
