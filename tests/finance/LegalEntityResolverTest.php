<?php

declare(strict_types=1);

namespace Itvolga\Tests\Finance;

use Espo\Modules\Itvolga\Tools\Finance\Exceptions\UnknownLegalEntity;
use Espo\Modules\Itvolga\Tools\Finance\LegalEntityResolver;

/**
 * 'Default' and 'По умолчанию' are one value in two languages (D-04): one legal entity, never two.
 */
final class LegalEntityResolverTest extends TestCase
{
    public function testBothSpellingsAndEmptyMeanTheSingleEntity(): void
    {
        $resolver = new LegalEntityResolver();

        foreach (['Default', 'По умолчанию', '', null] as $value) {
            $this->assertSame(LegalEntityResolver::KEY, $resolver->resolve($value), var_export($value, true));
        }

        $this->assertSame(1, count(array_unique(array_map($resolver->resolve(...), LegalEntityResolver::SOURCE_VALUES))));
    }

    public function testAnyOtherValueIsRejectedWithoutEchoingIt(): void
    {
        $resolver = new LegalEntityResolver();

        foreach (['default', 'Default ', 'ООО Синтетика', 'All'] as $value) {
            $e = $this->assertThrows(UnknownLegalEntity::class, fn () => $resolver->resolve($value));
            // A company name may be real: the message carries only its length.
            $this->assertTrue(!str_contains($e->getMessage(), $value), 'value leaked into the message');
        }
    }
}
