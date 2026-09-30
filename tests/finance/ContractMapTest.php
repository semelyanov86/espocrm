<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

/**
 * Completeness of the finance contract (docs/migration/finance-contract.md §11): every source column and link of the
 * finance modules that field-map.csv / relations.csv carry over has a field of the target entity in the contract.
 */
final class ContractMapTest extends TestCase
{
    private const MODULE_ENTITY = ['Quotes' => 'Quote', 'SalesOrder' => 'SalesOrder', 'Invoice' => 'Invoice', 'Act' => 'Act', 'SPPayments' => 'Payment'];
    private const DOCUMENTS = ['Quote', 'SalesOrder', 'Invoice', 'Act'];
    private const ITEMS = ['QuoteItem', 'SalesOrderItem', 'InvoiceItem', 'ActItem'];

    /** @var array<string, list<string>> entity → fields */
    private array $contract = [];
    /** @var array<string, string> entity → text of the source column */
    private array $sources = [];

    public function setUp(): void
    {
        $text = (string) file_get_contents(ITVOLGA_REPO . '/docs/migration/finance-contract.md');
        $section = explode("\n## 12.", explode("\n## 11.", $text, 2)[1] ?? '', 2)[0];
        $entity = null;

        foreach (explode("\n", $section) as $line) {
            if (preg_match('/^### (\w+)\s*$/', $line, $m)) {
                $entity = $m[1];
                $this->contract[$entity] = [];
                $this->sources[$entity] = '';

                continue;
            }

            if ($entity === null || !str_starts_with($line, '| `')) {
                continue;
            }

            $cells = array_map('trim', explode('|', trim($line, '|')));
            preg_match_all('/`([A-Za-z]\w*)`/', $cells[0], $names);
            array_push($this->contract[$entity], ...$names[1]);
            $this->sources[$entity] .= ' ' . ($cells[2] ?? '');
        }
    }

    public function testContractDescribesEveryFinanceEntity(): void
    {
        foreach (['Document', ...self::DOCUMENTS, 'Item', 'Payment', 'PaymentAllocation', 'LegalEntity'] as $entity) {
            $this->assertTrue(($this->contract[$entity] ?? []) !== [], "no contract table for $entity");
        }

        foreach (['vtigerId', 'number', 'status', 'account', 'legalEntity', 'subtotal', 'preTaxTotal', 'grandTotal', 'sourceFormula', 'totalsCheck'] as $field) {
            $this->assertTrue($this->has('Invoice', $field), "Document.$field");
        }

        foreach (['vtigerId', 'order', 'product', 'quantity', 'unitPrice', 'amount', 'margin', 'invoice', 'act', 'quote', 'salesOrder'] as $field) {
            $this->assertTrue($this->has('InvoiceItem', $field), "Item.$field");
        }
    }

    public function testEveryCarriedFieldOfTheMapIsInTheContract(): void
    {
        $missing = [];
        $checked = 0;

        foreach ($this->csv('field-map.csv') as $row) {
            $entity = self::MODULE_ENTITY[$row['source_module']] ?? null;

            if ($entity === null || !$this->carried($row['fate']) || in_array($row['target_field'], ['—', ''], true)) {
                continue;
            }

            foreach ($this->targets($entity, $row['target_field']) as [$targetEntity, $field]) {
                $checked++;

                if (!$this->has($targetEntity, $field)) {
                    $missing[] = "{$row['source_module']}.{$row['source_column']} → $targetEntity.$field";
                }
            }
        }

        $this->assertTrue($checked > 150, "only $checked fields checked");
        $this->assertSame([], $missing, 'fields missing in finance-contract.md §11:');
    }

    public function testEveryCarriedLinkOfTheMapIsInTheContract(): void
    {
        $missing = [];
        $checked = 0;

        foreach ($this->csv('relations.csv') as $row) {
            $finance = isset(self::MODULE_ENTITY[$row['from_module']]) || isset(self::MODULE_ENTITY[$row['to_module']]);

            if (!$finance || !$this->carried($row['fate'])) {
                continue;
            }

            foreach (preg_split('/\s*\|\s*(?=[A-Z])/', $row['target_link']) as $target) {
                if (!preg_match('/^([A-Z]\w+)\.(\w+)/', $target, $m)) {
                    // Owner links ("assignedUser/teams") belong to the module's own entity.
                    if (preg_match('/^(\w+)\//', $target, $o)) {
                        $m = [null, self::MODULE_ENTITY[$row['from_module']] ?? '', $o[1]];
                    } else {
                        continue;
                    }
                }

                if (!in_array($m[1], [...self::DOCUMENTS, ...self::ITEMS, 'Payment', 'PaymentAllocation'], true)) {
                    continue;
                }

                $checked++;

                if (!$this->has($m[1], $m[2])) {
                    $missing[] = "{$row['relation_id']} → {$m[1]}.{$m[2]}";
                }
            }
        }

        $this->assertTrue($checked > 30, "only $checked links checked");
        $this->assertSame([], $missing, 'links missing in finance-contract.md §11:');
    }

    public function testEveryFilledRequisiteColumnHasALegalEntityField(): void
    {
        $missing = [];

        foreach ($this->csv('field-map.csv') as $row) {
            if ($row['source_table'] === 'vtiger_organizationdetails' && (int) $row['nonempty_all_rows'] > 0
                && $row['source_column'] !== 'organization_id'
                && !preg_match('/`' . preg_quote($row['source_column'], '/') . '`/', $this->sources['LegalEntity'] ?? '')) {
                $missing[] = $row['source_column'];
            }
        }

        $this->assertSame([], $missing, 'requisite columns without a LegalEntity field:');
    }

    private function carried(string $fate): bool
    {
        return str_starts_with($fate, 'перенос') || str_starts_with($fate, 'архив');
    }

    /**
     * @return list<array{string, string}>
     */
    private function targets(string $entity, string $target): array
    {
        $result = [];

        // "assignedUser / teams", "payer (Account|Contact|Vendor)", "sourceFormula + vtigerData.region_id",
        // "InvoiceItem.vtigerData.tax2", "PaymentAllocation.invoice|salesOrder"
        foreach (preg_split('/\s+[\/+]\s+/', preg_replace('/\s*\(.*\)$/', '', $target)) as $part) {
            $targetEntity = $entity;

            if (preg_match('/^([A-Z]\w+)\.(.+)$/', $part, $m)) {
                [$targetEntity, $part] = [$m[1], $m[2]];
            }

            foreach (explode('|', $part) as $field) {
                $result[] = [$targetEntity, explode('.', $field)[0]];
            }
        }

        return $result;
    }

    private function has(string $entity, string $field): bool
    {
        $tables = match (true) {
            in_array($entity, self::DOCUMENTS, true) => ['Document', $entity],
            in_array($entity, self::ITEMS, true) => ['Item'],
            default => [$entity],
        };

        foreach ($tables as $table) {
            if (in_array($field, $this->contract[$table] ?? [], true)) {
                return true;
            }
        }

        return false;
    }

    /**
     * @return list<array<string, string>>
     */
    private function csv(string $name): array
    {
        $handle = fopen(ITVOLGA_REPO . "/docs/migration/$name", 'rb');
        $header = fgetcsv($handle, escape: '');
        $rows = [];

        while (($cells = fgetcsv($handle, escape: '')) !== false) {
            $rows[] = array_combine($header, $cells);
        }

        fclose($handle);

        return $rows;
    }
}
