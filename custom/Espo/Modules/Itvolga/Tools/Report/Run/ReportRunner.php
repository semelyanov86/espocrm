<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Run;

use Collator;
use Espo\Core\AclManager;
use Espo\Core\Exceptions\Forbidden;
use Espo\Core\Exceptions\NotFound;
use Espo\Core\Select\SelectBuilderFactory;
use Espo\Core\Utils\Config;
use Espo\Entities\Preferences;
use Espo\Entities\User;
use Espo\Modules\Itvolga\Entities\Report;
use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Report\Core\DecimalMath;
use Espo\Modules\Itvolga\Tools\Report\Core\Chart\ChartBuilder;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Aggregate;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\Definition;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\DefinitionParser;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\GroupLevel;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\ReportType;
use Espo\Modules\Itvolga\Tools\Report\Core\Definition\RunOptions;
use Espo\Modules\Itvolga\Tools\Report\Core\Filter\RunContext;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\NumberText;
use Espo\Modules\Itvolga\Tools\Report\Core\Format\RawNumber;
use Espo\Modules\Itvolga\Tools\Report\Core\Metric\MetricRules;
use Espo\Modules\Itvolga\Tools\Report\Core\Result\KeyOrder;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContext;
use Espo\Modules\Itvolga\Tools\Report\Format\FormatContextFactory;
use Espo\Modules\Itvolga\Tools\Report\Format\ValueFormatter;
use Espo\Modules\Itvolga\Tools\Report\Query\ReportQuery;
use Espo\Modules\Itvolga\Tools\Report\Schema\SchemaFactory;
use Espo\ORM\EntityManager;
use Espo\ORM\Query\Part\Order;
use Espo\ORM\Query\Part\Expression as Expr;
use Espo\ORM\Query\Part\WhereClause;
use Espo\ORM\Query\Select;
use Espo\ORM\Query\SelectBuilder;
use PDO;
use DateTimeImmutable;
use DateTimeZone;

/**
 * Runs a report for a user (POST Report/:id/run, reports.md §5): the definition is checked again with the ACL of the
 * user, the queries of the type are built by ReportQuery and executed as plain rows, the result is assembled and
 * formatted in the user's notation. Nothing is written and nothing is cached (D-95). The user is a parameter, so a
 * dashlet (05.2) or a mailing on behalf of a recipient (05.3) runs the same code.
 */
final class ReportRunner
{
    public const DEFAULT_MAX_ROWS = 5000;
    public const MAX_GROUPS = 1000;
    public const MAX_MATRIX_COLUMNS = 50;
    public const MAX_QUICK_FILTER_OPTIONS = 200;

    public function __construct(
        private readonly SchemaFactory $schemaFactory,
        private readonly SelectBuilderFactory $selectBuilderFactory,
        private readonly EntityManager $entityManager,
        private readonly FormatContextFactory $formatContextFactory,
        private readonly AclManager $aclManager,
        private readonly Config $config,
    ) {}

    public function maxRows(): int
    {
        return max(1, (int) ($this->config->get('itvolgaReportMaxRows') ?? self::DEFAULT_MAX_ROWS));
    }

    /**
     * @throws NotFound
     * @throws Forbidden
     */
    public function loadReadable(string $id, User $user): Report
    {
        $report = $this->entityManager->getRDBRepositoryByClass(Report::class)->getById($id);

        if (!$report) {
            throw new NotFound();
        }

        if (!$this->aclManager->checkEntityRead($user, $report)) {
            throw new Forbidden();
        }

        return $report;
    }

    /**
     * The checked definition of a report with the one-off parameters of a run, as the given user may run it.
     *
     * @param array<string, mixed> $raw
     */
    public function prepare(Report $report, array $raw, User $user): ReportQuery
    {
        $parser = new DefinitionParser($this->schemaFactory->create($user));
        $definition = $parser->parse(self::attributes($report));
        [$definition, $options] = $parser->parseRun($definition, $raw);

        return new ReportQuery($definition, $options, $user, $this->runContext($user), $this->selectBuilderFactory,
            $this->entityManager->getDefs());
    }

    /**
     * @return array<string, mixed>
     */
    public static function attributes(Report $report): array
    {
        $result = [];

        foreach (Report::DEFINITION_ATTRIBUTES as $attribute) {
            $value = $report->get($attribute);
            $result[$attribute] = is_object($value) || is_array($value) ?
                json_decode((string) json_encode($value), true) : $value;
        }

        return $result;
    }

    private function runContext(User $user): RunContext
    {
        $preferences = $this->entityManager->getEntityById(Preferences::ENTITY_TYPE, $user->getId());
        $timeZone = (string) ($preferences?->get('timeZone') ?: ($this->config->get('timeZone') ?: 'UTC'));

        return new RunContext(new DateTimeImmutable('now', new DateTimeZone('UTC')), $timeZone, $user->getId(),
            (int) ($this->config->get('fiscalYearShift') ?? 0));
    }

    /**
     * @param array<string, mixed> $raw parameters of the run (offset, maxSize, filters, quickFilters, noLimit)
     * @return array<string, mixed>
     */
    public function run(Report $report, array $raw, User $user): array
    {
        $query = $this->prepare($report, $raw, $user);
        [$assembler, $context, $formatter, $labels, $order] = $this->tools($query, $user);

        $counts = $this->fetch($query->base()->select([['ITVOLGA_COUNT_DISTINCT:(id)', 'records'],
            ['COUNT:(id)', 'rows']])->build())[0] ?? [];

        $result = [
            'id' => $report->getId(),
            'name' => $report->get('name'),
            'type' => $query->definition->type->value,
            'entityType' => $query->definition->entityType,
            'recordCount' => (int) ($counts['records'] ?? 0),
            'rowCount' => (int) ($counts['rows'] ?? 0),
        ];

        $result += match ($query->definition->type) {
            ReportType::TABULAR => $assembler->tabular($result['rowCount']),
            ReportType::SUMMARIES, ReportType::SUMMARIES_WITH_DETAILS => $assembler->grouped(),
            ReportType::MATRIX => $assembler->matrix(),
        };

        // Charts are made of the assembled result, no query of their own (D-105).
        $charts = (new ChartBuilder($order, $context->numbers, fn (Aggregate $a) => $labels->aggregate($a),
            fn (Aggregate $a, string $function, Decimal $value, ?string $currency) =>
                self::progressCell($formatter, $context->numbers, $a, $function, $value, $currency)))
            ->build($query->definition, $result);

        if ($charts !== null) {
            $result['charts'] = $charts;
        }

        $result['dashboard'] = $query->definition->dashboard->toArray();

        if ($query->options->withQuickFilterOptions) {
            $result['quickFilters'] = $assembler->quickFilterOptions();
        }

        if ($query->options->withDashboardFilterOptions && $query->definition->dashboard->filterField !== null) {
            $result['dashboardFilter'] = $assembler->filterOptions($query->definition->dashboard->filterField);
        }

        $result['limits']['maxRows'] = $this->maxRows();

        return $result;
    }

    /**
     * One metric of a tabular report for a user (D-112): the record count or SUM/AVG/MIN/MAX of a numeric column over
     * all records of the report's conditions, checked and computed like the report itself (its definition parsed with
     * the user's ACL, the same query as `recordCount` and the column totals). The caller loads the report readable for
     * the user and runs this in a reading transaction, as for run().
     *
     * @return array<string, mixed> the cell of the value
     */
    public function metric(Report $report, string $function, ?string $column, User $user): array
    {
        $query = $this->prepare($report, ['withQuickFilterOptions' => false], $user);
        $aggregate = MetricRules::aggregate($query->definition, $function, $column);

        return $this->tools($query, $user)[0]->overall([$aggregate])[0];
    }

    /**
     * @return array{Assembler, FormatContext, ValueFormatter, Labels, KeyOrder}
     */
    private function tools(ReportQuery $query, User $user): array
    {
        $context = $this->formatContextFactory->create($user);
        $formatter = new ValueFormatter($context, $this->entityManager);
        $labels = new Labels($context->language, $query->definition);
        $order = new KeyOrder(class_exists(Collator::class) ? new Collator($context->languageCode) : null);
        $assembler = new Assembler($query, $formatter, $labels, $order, $this->maxRows(), fn (Select $s) =>
            $this->fetch($s));

        return [$assembler, $context, $formatter, $labels, $order];
    }

    /**
     * A progress-line value (D-107) in the notation of the aggregate: an average with two decimals, money with its
     * currency.
     *
     * @return array<string, mixed>
     */
    private static function progressCell(ValueFormatter $formatter, NumberText $numbers, Aggregate $aggregate,
        string $function, Decimal $value, ?string $currency): array
    {
        $scale = $function === 'AVG' ? 2 : null;

        if ($aggregate->field === null) {
            return ['v' => $value->toString(), 'f' => $numbers->format($value, $scale)];
        }

        return $formatter->number($aggregate->field, $value, $currency,
            $scale ?? ($aggregate->function === 'AVG' || $aggregate->field->isCurrency() ? 2 : null));
    }

    /**
     * @return list<array<string, mixed>>
     */
    private function fetch(Select $select): array
    {
        return $this->entityManager->getQueryExecutor()->execute($select)->fetchAll(PDO::FETCH_ASSOC);
    }
}
