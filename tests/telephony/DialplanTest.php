<?php

declare(strict_types=1);

namespace Itvolga\Tests\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\PhoneNumbers;
use Itvolga\Tests\Finance\TestCase;

/**
 * The dial strings of click-to-call against the dialplan of the test PBX (deploy/telephony/pbx/extensions.conf): its
 * `phones-out` patterns are those of production (role asterisk, extensions.conf.j2; contexts checked read-only on the
 * server 2026-10-13), and every string the CRM sends must be taken by the pattern a person dialling the same number
 * on the desk phone would hit.
 */
final class DialplanTest extends TestCase
{
    private const PRODUCTION_PHONES_OUT = [
        '_0[1-689]XXXX.',
        '_+7XXXXXXXXXX',
        '_[78]XXXXXXXXXX',
        '_+78352XXXXXX',
        '_[78]8352XXXXXX',
        '_XXXXXX',
    ];

    public function testStandDialplanKeepsTheProductionPatterns(): void
    {
        $this->assertSame(self::PRODUCTION_PHONES_OUT, $this->patterns('phones-out'));
        $this->assertSame(['_[12][01]X', '118'], $this->patterns('phones-local'));
    }

    public function testEveryDialStringIsTakenByThePatternOfAManualDial(): void
    {
        $cases = [
            '+7 (999) ' . '000-00-01' => '_+7XXXXXXXXXX',
            '8 999 0' . '00 00 01' => '_+7XXXXXXXXXX',
            '99900' . '00001' => '_+7XXXXXXXXXX',
            '+7 8352 22-00-01' => '_+78352XXXXXX',
            '22-00-01' => '_XXXXXX',
            '+49 151' . ' 0000001' => '_0[1-689]XXXX.',
            '0049 151 0000001' => '_0[1-689]XXXX.',
            '+1 555 0100' => '_0[1-689]XXXX.',
        ];

        foreach ($cases as $raw => $pattern) {
            $dial = PhoneNumbers::dialString((string) $raw, '8352');
            $this->assertTrue($dial !== null, "dialString($raw)");
            $this->assertSame($pattern, self::best($this->patterns('phones-out'), (string) $dial), "pattern of $raw");
        }
    }

    public function testInternalNumbersAreNeverDialledFromTheCrm(): void
    {
        foreach (['111', '808', '811', '555'] as $internal) {
            $this->assertSame(null, PhoneNumbers::dialString($internal, '8352'), $internal);
        }
    }

    /**
     * @return list<string>
     */
    private function patterns(string $context): array
    {
        $file = ITVOLGA_REPO . '/deploy/telephony/pbx/extensions.conf';
        $current = null;
        $patterns = [];

        foreach (file($file, FILE_IGNORE_NEW_LINES) ?: [] as $line) {
            if (preg_match('/^\[([^\]]+)\]/', $line, $m)) {
                $current = $m[1];
            } elseif ($current === $context && preg_match('/^exten\s*=>\s*([^,]+),1,/', $line, $m)) {
                $patterns[] = trim($m[1]);
            }
        }

        return $patterns;
    }

    /**
     * The pattern Asterisk chooses: of the matching ones, the most specific (fewest possibilities per position, as
     * the dialplan sorts them); null when none matches.
     *
     * @param list<string> $patterns
     */
    private static function best(array $patterns, string $exten): ?string
    {
        $matching = array_values(array_filter($patterns, static fn ($p) => self::matches($p, $exten)));
        usort($matching, static fn ($a, $b) => self::weight($a) <=> self::weight($b));

        return $matching[0] ?? null;
    }

    private static function matches(string $pattern, string $exten): bool
    {
        if (!str_starts_with($pattern, '_')) {
            return $pattern === $exten;
        }

        $regex = '';
        $chars = substr($pattern, 1);

        for ($i = 0; $i < strlen($chars); $i++) {
            $c = $chars[$i];
            $regex .= match ($c) {
                'X' => '[0-9]',
                'Z' => '[1-9]',
                'N' => '[2-9]',
                '.' => '.+',
                '!' => '.*',
                '[' => (function () use ($chars, &$i) {
                    $end = strpos($chars, ']', $i);
                    $class = substr($chars, $i, $end - $i + 1);
                    $i = $end;

                    return $class;
                })(),
                default => preg_quote($c, '/'),
            };
        }

        return (bool) preg_match('/^' . $regex . '$/', $exten);
    }

    /**
     * Position-by-position size of the character set: a literal (1) is more specific than X (10) or a wildcard.
     *
     * @return list<int>
     */
    private static function weight(string $pattern): array
    {
        $weights = [];
        $chars = substr($pattern, 1);

        for ($i = 0; $i < strlen($chars); $i++) {
            $c = $chars[$i];

            if ($c === '[') {
                $end = strpos($chars, ']', $i);
                $class = substr($chars, $i + 1, $end - $i - 1);
                $weights[] = strlen(preg_replace_callback('/(.)-(.)/', fn ($m) => implode('', range($m[1], $m[2])), $class));
                $i = $end;
            } else {
                $weights[] = match ($c) { 'X' => 10, 'Z' => 9, 'N' => 8, '.', '!' => 99, default => 1 };
            }
        }

        return $weights;
    }
}
