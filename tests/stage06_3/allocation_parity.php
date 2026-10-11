<?php

/**
 * Parity of the D-11 allocation rule (stage 06.3): the pure SourceAllocationResolver of the finance core on synthetic
 * source payments, for comparison with the Python port of the importer (scripts/import/spec_finance.py). Runs as the
 * stand user with the stand PHP; the script comes on stdin, the synthetic cases as JSON in argv:
 *
 *   [{"id": 1, "direction": "incoming", "amount": "10.00", "relatedToId": 5, "relatedToType": "Invoice",
 *     "relatedToDeleted": false, "linkedInvoiceIds": [5]}, …]
 *
 * Prints one JSON line: [{"category", "decision", "candidateType", "candidateId", "conflicts"}, …].
 */

declare(strict_types=1);

$root = getenv('ESPO_ROOT') ?: '';
include $root . '/bootstrap.php';

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Finance\Payment\Direction;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SourceAllocationResolver;
use Espo\Modules\Itvolga\Tools\Finance\Payment\SourcePayment;

$resolver = new SourceAllocationResolver();
$out = [];

foreach (json_decode($argv[1] ?? '[]', true, 512, JSON_THROW_ON_ERROR) as $case) {
    $result = $resolver->resolve(new SourcePayment(
        $case['id'],
        Direction::from($case['direction']),
        '',
        Decimal::of($case['amount']),
        $case['relatedToId'],
        $case['relatedToType'],
        $case['relatedToDeleted'],
        $case['linkedInvoiceIds'],
    ));
    $out[] = [
        'category' => $result->category->value,
        'decision' => $result->decision->value,
        'candidateType' => $result->candidateType,
        'candidateId' => $result->candidateId,
        'conflicts' => $result->conflictInvoiceIds,
    ];
}

echo json_encode($out), "\n";
