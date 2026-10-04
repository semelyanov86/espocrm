<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Calculation;

use Espo\Modules\Itvolga\Tools\Finance\Decimal;
use Espo\Modules\Itvolga\Tools\Report\Core\DecimalMath;

/**
 * A parsed calculation (Parser). Evaluation is exact (bcmath through Decimal): an empty operand or a division by
 * zero makes the result empty (null), a quotient keeps DecimalMath::DIVISION_SCALE decimals.
 */
final class Expression
{
    /**
     * @param array<int, mixed> $node
     */
    public function __construct(
        public readonly string $text,
        private readonly array $node,
    ) {}

    /**
     * Column references in order of appearance, without repeats.
     *
     * @return list<string>
     */
    public function references(): array
    {
        $list = [];
        $this->collect($this->node, $list);

        return array_values(array_unique($list));
    }

    /**
     * Position (1-based) of the first reference to $id, for an error message.
     */
    public function positionOf(string $id): int
    {
        return $this->find($this->node, $id) ?? 0;
    }

    /**
     * @param array<string, Decimal|null> $values column id → value of one row
     */
    public function evaluate(array $values): ?Decimal
    {
        return $this->evaluateNode($this->node, $values);
    }

    /**
     * Decimals of the value when the outermost operation is round(x, n), else null.
     */
    public function roundScale(): ?int
    {
        return $this->node[0] === 'round' ? $this->node[2] : null;
    }

    /**
     * @param array<int, mixed> $node
     * @param list<string> $list
     */
    private function collect(array $node, array &$list): void
    {
        match ($node[0]) {
            'ref' => $list[] = $node[1],
            'neg' => $this->collect($node[1], $list),
            'round' => $this->collect($node[1], $list),
            'op' => [$this->collect($node[2], $list), $this->collect($node[3], $list)],
            default => null,
        };
    }

    /**
     * @param array<int, mixed> $node
     */
    private function find(array $node, string $id): ?int
    {
        return match ($node[0]) {
            'ref' => $node[1] === $id ? $node[2] : null,
            'neg', 'round' => $this->find($node[1], $id),
            'op' => $this->find($node[2], $id) ?? $this->find($node[3], $id),
            default => null,
        };
    }

    /**
     * @param array<int, mixed> $node
     * @param array<string, Decimal|null> $values
     */
    private function evaluateNode(array $node, array $values): ?Decimal
    {
        switch ($node[0]) {
            case 'num':
                return $node[1];

            case 'ref':
                return $values[$node[1]] ?? null;

            case 'neg':
                return $this->evaluateNode($node[1], $values)?->negate();

            case 'round':
                return $this->evaluateNode($node[1], $values)?->round($node[2]);
        }

        $left = $this->evaluateNode($node[2], $values);
        $right = $this->evaluateNode($node[3], $values);

        if ($left === null || $right === null) {
            return null;
        }

        return match ($node[1]) {
            '+' => $left->add($right),
            '-' => $left->sub($right),
            '*' => $left->mul($right),
            '/' => DecimalMath::divide($left, $right),
        };
    }
}
