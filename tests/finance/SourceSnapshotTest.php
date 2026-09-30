<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\LegalEntityResolver;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationCalculator;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationDecision;
use Espo\Modules\Itvolga\Tools\Finance\Payment\AllocationShare;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Direction;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SettlementState;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SourceAllocation;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SourceAllocationResolver;
use Espo\Modules\Itvolga\Tools\Finance\Source\SourceVerifier;
use Espo\Modules\Itvolga\Tools\Finance\Source\TotalCheck;
use Espo\Modules\Itvolga\Tools\Finance\Source\Verification;
use Itvolga\Tests\Finance\Support\ControlSums;
use Itvolga\Tests\Finance\Support\SourceSnapshot;

/**
 * The core against every live document and payment of the source (private numeric snapshot of the audit run named in
 * fixtures/source-profile.php). Expected values are server-side aggregates of the same run: counts from the profile
 * (in Git), monetary control sums from the private 35_control_sums_private.tsv and as HMAC digests (in Git).
 * Skipped when the private directory is not available (for example in a review worktree). Prints counts only.
 */
final class SourceSnapshotTest extends TestCase
{
    /** run.php hides messages of unexpected exceptions of this test: they could quote a private value. */
    public const PRIVATE_DATA = true;

    /** @var array<string, mixed> */
    private static array $profile;
    private static ?string $dir = null;
    private static ?SourceSnapshot $snapshot = null;
    /** @var array<int, Verification> */
    private static array $verifications = [];
    /** @var array<int, SourceAllocation> */
    private static array $allocations = [];

    public function setUp(): void
    {
        if (self::$snapshot !== null) {
            return;
        }

        self::$profile = require __DIR__ . '/fixtures/source-profile.php';
        self::$dir = getenv('ITVOLGA_AUDIT_DIR') ?: '/data/itvolga/espo-private/audit/' . self::$profile['run'];
        $file = self::$dir . '/47_finance_snapshot_private.tsv';

        if (!is_readable($file)) {
            $this->skip('private snapshot of run ' . self::$profile['run'] . ' is not available (outside Git)');
        }

        self::$snapshot = SourceSnapshot::load($file);
        $verifier = new SourceVerifier();
        $resolver = new SourceAllocationResolver();

        foreach (array_keys(self::$snapshot->documents) as $id) {
            self::$verifications[$id] = $verifier->verify(self::$snapshot->sourceDocument($id));
        }

        foreach (self::$snapshot->payments as $row) {
            self::$allocations[(int) $row['payid']] = $resolver->resolve(self::$snapshot->sourcePayment($row));
        }
    }

    public function testEveryDocumentReproducesItsStoredTotals(): void
    {
        $classes = [];
        $inconsistent = [];
        $notExact = 0;

        foreach (self::$verifications as $id => $verification) {
            $module = self::$snapshot->documents[$id]['module'];
            $taxMode = self::$snapshot->documents[$id]['header']['taxtype'];
            $key = "$module|$taxMode|{$verification->formulaClass->value}";
            $classes[$key] = ($classes[$key] ?? 0) + 1;

            if (!$verification->totalsConsistent()) {
                $inconsistent[] = $id;
            }

            if ($verification->worstCheck() !== TotalCheck::Exact) {
                $notExact++;
            }
        }

        ksort($classes);
        $this->assertSame(self::$profile['documents'], count(self::$verifications), 'live documents');
        $this->assertSame(self::$profile['formulaClasses'], $classes, 'formula classes (core vs MySQL)');
        $this->assertSame([], array_slice($inconsistent, 0, 5), count($inconsistent) . ' documents do not reproduce their totals; first ids:');
        // No live line has a fraction of a kopeck: every stored total equals the exact recomputation.
        $this->assertSame(0, $notExact, 'documents whose totals match only after rounding');
    }

    public function testStoredMarginsAreNetMinusCostOrNeverComputed(): void
    {
        $margins = [];

        foreach (self::$verifications as $id => $verification) {
            $module = self::$snapshot->documents[$id]['module'];
            $margins[$module] ??= ['lines' => 0, 'ok' => 0, 'notComputed' => 0, 'mismatch' => 0];

            foreach ($verification->margins as $check) {
                $margins[$module]['lines']++;
                $margins[$module][$check->value]++;
            }
        }

        ksort($margins);
        $this->assertSame(self::$profile['margins'], $margins, 'line margins (core vs MySQL)');
    }

    public function testAllocationsFollowTheStrictPartition(): void
    {
        $categories = [];
        $decisions = [];

        foreach (self::$allocations as $allocation) {
            $categories[$allocation->category->value] = ($categories[$allocation->category->value] ?? 0) + 1;
            $decisions[$allocation->decision->value] = ($decisions[$allocation->decision->value] ?? 0) + 1;
        }

        ksort($categories);
        $this->assertSame(self::$profile['allocationPartition'], $categories, 'allocation categories (core vs MySQL)');
        // The only unresolved shape of the live data: outgoing bank-import payments linked to customer invoices (Q-36).
        $this->assertSame(self::$profile['outgoingLinkedToInvoices'], $decisions['unresolved'] ?? 0, 'unresolved allocations');

        foreach (self::$snapshot->payments as $row) {
            $allocation = self::$allocations[(int) $row['payid']];

            if ($allocation->decision === AllocationDecision::Unresolved) {
                $this->assertSame('Expense', $row['pay_type'], 'unresolved allocation of an incoming payment');
            }
        }
    }

    public function testSettlementsMatchTheCoverageOfTheSource(): void
    {
        $shares = [];

        foreach (self::$snapshot->payments as $row) {
            $allocation = self::$allocations[(int) $row['payid']];

            if ($allocation->decision === AllocationDecision::Allocate) {
                $shares[$allocation->candidateId][] = new AllocationShare(
                    $allocation->amount, Direction::fromSource($row['pay_type']), $row['status']);
            }
        }

        $calculator = new AllocationCalculator();
        $coverage = [];

        foreach (self::$snapshot->documents as $id => $doc) {
            if (!in_array($doc['module'], ['Invoice', 'SalesOrder'], true)) {
                continue;
            }

            $settlement = $calculator->settle(Decimal::of($doc['header']['total']), $shares[$id] ?? []);
            $key = $doc['module'] . '|' . $doc['header']['status'];
            $coverage[$key] ??= ['n' => 0, 'none' => 0, 'one' => 0, 'many' => 0, 'paid' => 0, 'partial' => 0, 'overpaid' => 0];
            $coverage[$key]['n']++;
            $coverage[$key][match (true) {
                $settlement->countedPayments === 0 => 'none',
                $settlement->countedPayments === 1 => 'one',
                default => 'many',
            }]++;
            $state = match ($settlement->state) {
                SettlementState::Paid => 'paid',
                SettlementState::Partial => 'partial',
                SettlementState::Overpaid => 'overpaid',
                SettlementState::Unpaid => null,
            };

            if ($state !== null) {
                $coverage[$key][$state]++;
            }
        }

        ksort($coverage);
        $this->assertSame(self::$profile['coverage'], $coverage, 'coverage of invoices and sales orders (core vs MySQL)');
    }

    public function testEverySpcompanyValueIsTheSingleLegalEntity(): void
    {
        $resolver = new LegalEntityResolver();
        $values = [];
        $count = static function (string $module, string $raw) use (&$values, $resolver): void {
            $resolver->resolve($raw === '(null)' ? null : $raw); // throws on an unknown value
            $label = match (true) {
                $raw === '' => '(empty)',
                in_array($raw, ['(null)', 'Default', 'По умолчанию'], true) => $raw,
                default => '(other)',
            };
            $values["$module|$label"] = ($values["$module|$label"] ?? 0) + 1;
        };

        foreach (self::$snapshot->documents as $doc) {
            $count($doc['module'], $doc['header']['spcompany']);
        }

        foreach (self::$snapshot->payments as $row) {
            $count('SPPayments', $row['spcompany']);
        }

        ksort($values);
        $this->assertSame(self::$profile['legalEntityValues'], $values, 'spcompany values (core vs MySQL)');
    }

    public function testControlSumsEqualServerAggregates(): void
    {
        $server = ControlSums::fromServer(self::$dir . '/35_control_sums_private.tsv');
        $core = ControlSums::fromSnapshot(self::$snapshot, self::$allocations);

        foreach (ControlSums::GROUPS as $group => $_) {
            $missing = count(array_diff($server[$group], $core[$group]));
            $this->assertTrue($server[$group] !== [], "$group: no server rows");
            // Only counts of differing rows are shown: the sums themselves are private.
            $this->assertTrue($missing === 0 && count($server[$group]) === count($core[$group]),
                "$group: " . $missing . ' of ' . count($server[$group]) . ' server rows differ from the core');
        }
    }

    public function testControlSumsMatchCommittedDigests(): void
    {
        $keyFile = getenv('ITVOLGA_DIGEST_KEY') ?: '/data/itvolga/espo-private/finance/control-digest.key';

        if (!is_readable($keyFile)) {
            $this->skip('digest key is not available (outside Git)');
        }

        $key = trim((string) file_get_contents($keyFile));
        $core = ControlSums::fromSnapshot(self::$snapshot, self::$allocations);

        foreach (self::$profile['controlSumDigests'] as $group => $expected) {
            $this->assertSame($expected['rows'], count($core[$group]), "$group rows");
            $this->assertTrue(hash_equals($expected['hmac'], ControlSums::digest($key, $group, $core[$group])), "$group digest");
        }
    }
}
