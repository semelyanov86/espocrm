<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Report\Core\Info;

use Espo\Modules\Itvolga\Tools\Report\Core\Definition\FieldInfo;

/**
 * Words of the condition text for the user the report info is made for (the adapter translates with his language and
 * resolves record names with his ACL; the tests give literals).
 */
interface ConditionWords
{
    /** «И» / «ИЛИ» of a group type and|or. */
    public function joiner(string $type): string;

    /** «Контрагент → Город». */
    public function field(FieldInfo $field): string;

    /** A where type (equals, in, lastXDays …). */
    public function operator(string $type): string;

    /** A date comparison: «≤ Дата оплаты» (the other field is of the main entity). */
    public function compare(string $operator, string $otherField): string;

    /**
     * Values of a condition as the user may see them: option labels, names of the records he may read (others —
     * a neutral mark), dates in his format.
     *
     * @param list<mixed> $values
     * @return list<string>
     */
    public function values(FieldInfo $field, array $values): array;
}
