<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Source\FormulaClass;
use Espo\Modules\Itvolga\Tools\Finance\Source\MarginCheck;
use Espo\Modules\Itvolga\Tools\Finance\Source\SourceVerifier;
use Espo\Modules\Itvolga\Tools\Finance\Source\TotalCheck;
use Itvolga\Tests\Finance\Support\SourceRows;

/**
 * Source documents: one synthetic document per structure found in the live data, plus the shapes the data does not
 * contain (they must come out Unverified, never recalculated).
 */
final class SourceVerifierTest extends TestCase
{
    /** @var list<array<string, mixed>> */
    private array $cases;

    public function setUp(): void
    {
        $file = ITVOLGA_REPO . '/tests/fixtures/synthetic/finance/source-documents.json';
        $this->cases = json_decode((string) file_get_contents($file), true, 512, JSON_THROW_ON_ERROR)['documents'];
    }

    public function testEverySyntheticStructureIsClassifiedAndCompared(): void
    {
        $verifier = new SourceVerifier();

        foreach ($this->cases as $case) {
            $name = $case['name'];
            $header = ($case['header'] ?? []) + $case['stored'] + ['taxtype' => $case['taxtype'], 'region' => $case['region']];
            $result = $verifier->verify(SourceRows::document($header, $case['lines']));
            $expect = $case['expect'];

            $this->assertSame(FormulaClass::from($expect['class']), $result->formulaClass, "$name: class");
            $this->assertSame($expect['consistent'] ?? ($expect['class'] !== 'unverified'), $result->totalsConsistent(), "$name: consistent");
            $this->assertSame(array_map(MarginCheck::from(...), $expect['margins']), $result->margins, "$name: margins");

            if (isset($expect['check'])) {
                $this->assertSame(TotalCheck::from($expect['check']), $result->worstCheck(), "$name: worst check");
            }

            foreach ($expect['checks'] ?? [] as $field => $check) {
                $this->assertSame(TotalCheck::from($check), $result->checks[$field], "$name: $field check");
            }

            foreach (['subtotal' => 'expectedSubtotal', 'preTaxTotal' => 'expectedPreTaxTotal',
                      'taxAmount' => 'expectedTaxAmount', 'grandTotal' => 'expectedGrandTotal'] as $key => $property) {
                if (isset($expect[$key])) {
                    $this->assertDecimal($expect[$key], $result->$property, "$name: $key");
                }
            }

            if (isset($expect['reason'])) {
                $this->assertTrue(str_contains(implode('; ', $result->reasons), $expect['reason']),
                    "$name: reason must mention '{$expect['reason']}', got: " . implode('; ', $result->reasons));
            }

            if ($result->formulaClass === FormulaClass::Unverified) {
                $this->assertSame(null, $result->expectedGrandTotal, "$name: no expected totals when unverified");
                $this->assertSame([], $result->checks, "$name: no checks when unverified");
            }
        }
    }

    public function testFixtureCoversEveryLiveStructure(): void
    {
        $seen = [];

        foreach ($this->cases as $case) {
            $seen[$case['module'] . '|' . $case['taxtype'] . '|' . $case['expect']['class']] = true;
        }

        // Every module × tax mode × formula class of the live data (finance-contract.md §12.2).
        foreach ([
            'Invoice|individual|noLineTax', 'Invoice|individual|lineTaxNotApplied', 'Invoice|group|groupTaxAdded',
            'Invoice|group_tax_inc|taxIncludedInPrice', 'Invoice|group_tax_inc|noLineTax', 'Act|individual|noLineTax',
            'Quotes|individual|lineTaxNotApplied', 'SalesOrder|individual|lineTaxNotApplied', 'SalesOrder|group_tax_inc|noLineTax',
        ] as $structure) {
            $this->assertTrue(isset($seen[$structure]), "no synthetic document for $structure");
        }
    }

    public function testStoredTotalsAreNeverReplaced(): void
    {
        $case = $this->cases[array_search('stored-total-differs-by-a-kopeck', array_column($this->cases, 'name'), true)];
        $header = $case['stored'] + ['taxtype' => $case['taxtype'], 'region' => $case['region']];
        $source = SourceRows::document($header, $case['lines']);
        $result = (new SourceVerifier())->verify($source);

        // The discrepancy is reported next to the stored value, the stored value itself is untouched.
        $this->assertDecimal('5000.01', $source->grandTotal);
        $this->assertDecimal('5000', $result->expectedGrandTotal);
        $this->assertSame(TotalCheck::Mismatch, $result->checks['grandTotal']);
    }
}
