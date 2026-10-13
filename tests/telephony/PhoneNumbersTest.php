<?php

declare(strict_types=1);

namespace Itvolga\Tests\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\PhoneNumbers;
use Itvolga\Tests\Finance\TestCase;

final class PhoneNumbersTest extends TestCase
{
    private const AREA = '8352';

    public function testCanonicalFollowsTheImportRules(): void
    {
        $cases = [
            '79990' . '000001' => '+79990' . '000001',        // caller id of trunk-russia
            '89990' . '000001' => '+79990' . '000001',
            '+7 (999) ' . '000-00-01' => '+79990' . '000001',
            '99900' . '00001' => '+79990' . '000001',         // ten digits, 9…
            '83520' . '00001' => '+78352' . '000001',         // ten digits, 8…
            '000001' => '+78352' . '000001',             // local six digits as the dialplan dials them
            '+49 151' . ' 0000001' => '+49151' . '0000001',
            '0049 151 0000001' => '+49151' . '0000001',
            '+1 555 0100' => '+15550100',
            '12345' => null,
            '105' => null,
            '' => null,
            '<unknown>' => null,
            'anonymous' => null,
            '+7 999 000-0' . '0-01 доб. 12' => null,
            '+7 999 000-00-0' . '1, +7 999' . ' 000-00-02' => null,
            '+7 999 000-' . '00-01 ext 5' => null,
        ];

        foreach ($cases as $raw => $expected) {
            $this->assertSame($expected, PhoneNumbers::canonical((string) $raw, self::AREA), "canonical($raw)");
        }
    }

    public function testNumericCandidatesCoverTheStoredForms(): void
    {
        $this->assertSame(['79990' . '000001', '89990' . '000001', '99900' . '00001'],
            PhoneNumbers::numericCandidates('+79990' . '000001', self::AREA));
        $this->assertSame(['78352' . '000001', '88352' . '000001', '83520' . '00001', '000001'],
            PhoneNumbers::numericCandidates('+78352' . '000001', self::AREA));
        $this->assertSame(['491510' . '000001', '0049151' . '0000001'], PhoneNumbers::numericCandidates('+49151' . '0000001', self::AREA));
    }

    public function testTail(): void
    {
        $this->assertSame('99900' . '00001', PhoneNumbers::tail('+79990' . '000001'));
        $this->assertSame(null, PhoneNumbers::tail('+15550100'));
    }

    /**
     * The dial string of each stored form must be accepted by a phones-out pattern (checked against the dialplan of
     * the isolated PBX in DialplanTest).
     */
    public function testDialString(): void
    {
        $cases = [
            '+7 (999) ' . '000-00-01' => '+79990' . '000001',
            '8 999 0' . '00 00 01' => '+79990' . '000001',
            '79990' . '000001' => '+79990' . '000001',
            '99900' . '00001' => '+79990' . '000001',
            '22-00-01' => '220001',
            '+7 8352 22-00-01' => '+78352' . '220001',
            '+49 151' . ' 0000001' => '049151' . '0000001',
            '0049 151 0000001' => '049151' . '0000001',
            '+1 555 0100' => '015550100',
            '+7 999 000-0' . '0-01 доб. 12' => null,
            '108' => null,
            '12345' => null,
            '+7 999 000' => null,
            '+70 1' => null,
            '+7999' . "0000001\r\nAction: Command" => null,
        ];

        foreach ($cases as $raw => $expected) {
            $this->assertSame($expected, PhoneNumbers::dialString((string) $raw, self::AREA), "dialString($raw)");
        }
    }
}
