<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Classes\ORM;

use Espo\ORM\QueryComposer\Part\FunctionConverter;
use RuntimeException;

/**
 * ORM function ITVOLGA_GROUP_TOKEN with one argument: the weight of a space and the weight string of the value, joined
 * by a colon, both in hex and in the expression's own collation (reports, external review B8). Values the database puts into one text group have
 * equal weight strings up to trailing space weights (PAD SPACE), which the report strips; so rows of separate queries
 * find their group exactly as GROUP BY formed it, whatever the collation folds (case, accents, symbols).
 * ANY_VALUE keeps ONLY_FULL_GROUP_BY satisfied: within a group the tokens differ at most by those trailing weights.
 * The argument arrives already compiled by the query composer, never as user input.
 */
final class GroupToken implements FunctionConverter
{
    public function convert(string ...$argumentList): string
    {
        if (count($argumentList) !== 1) {
            throw new RuntimeException('ITVOLGA_GROUP_TOKEN takes exactly one argument.');
        }

        $value = $argumentList[0];

        return "ANY_VALUE(CONCAT(HEX(WEIGHT_STRING(RIGHT(CONCAT($value, ' '), 1))), ':', HEX(WEIGHT_STRING($value))))";
    }
}
