<?php

declare(strict_types=1);

namespace Itvolga\Tests\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\HistoryCall;
use Espo\Modules\Itvolga\Tools\Telephony\Core\TrackerSettings;
use InvalidArgumentException;
use Itvolga\Tests\Finance\TestCase;
use stdClass;

/**
 * The operation of a CDR history call (stage 07.2): every value checked before anything is written; the facts it gives.
 */
final class HistoryCallTest extends TestCase
{
    /** Synthetic numbers built from parts: no phone-shaped literal in Git. */
    private const NUMBER = '7999' . '000' . '0001';
    private const LOCAL = '54' . '3210';

    private TrackerSettings $settings;

    public function setUp(): void
    {
        $this->settings = TrackerSettings::fromArray([]);
    }

    private static function op(array $override = []): stdClass
    {
        return json_decode(json_encode(array_replace([
            'linkedId' => '1760000000.42',
            'source' => 'mysql',
            'direction' => 'Inbound',
            'dateStart' => '2026-08-10 09:00:00',
            'dateEnd' => '2026-08-10 09:02:00',
            'answeredAt' => '2026-08-10 09:00:20',
            'billSeconds' => 100,
            'rawStatus' => 'ANSWER',
            'numberRaw' => self::NUMBER,
            'line' => '290001',
            'clickToCall' => false,
            'callerExtension' => null,
            'answeredExtension' => '108',
            'rungExtensions' => ['108', '208', '108'],
            'recording' => ['path' => '2026/08/10/a.wav', 'size' => 1000, 'sha256' => str_repeat('a', 64)],
        ], $override)), false);
    }

    public function testFactsOfAnAnsweredInboundCall(): void
    {
        $call = HistoryCall::fromOperation(self::op(), $this->settings);
        $facts = $call->facts('8352', '2026/08/10/a.wav', true, '108');

        $this->assertSame('Held', $facts['status']);
        $this->assertSame('108', $facts['cExtension']);
        $this->assertSame('+' . self::NUMBER, $facts['cPhoneNumber'], 'canonical number');
        $this->assertSame(['108', '208'], $call->rungExtensions, 'every phone once');
        $this->assertSame(['108', '208'], $call->participantExtensions());
        $this->assertSame(['ended', 'mysql', true, '2026/08/10/a.wav'],
            [$facts['cLiveState'], $facts['cCdrSource'], $facts['cRecording'], $facts['cRecordingPath']]);
        $this->assertSame(HistoryCall::FACTS, array_keys($facts), 'FACTS names what facts() owns');
    }

    public function testMissedCallAndNoRecording(): void
    {
        $call = HistoryCall::fromOperation(self::op(['answeredAt' => null, 'billSeconds' => 0, 'rawStatus' => 'NOANSWER',
            'answeredExtension' => null, 'recording' => null, 'numberRaw' => self::LOCAL]), $this->settings);
        $facts = $call->facts('8352', null, false, '119');

        $this->assertSame(['Not Held', false, null], [$facts['status'], $facts['cRecording'], $facts['cRecordingPath']]);
        $this->assertSame('+78352' . self::LOCAL, $facts['cPhoneNumber'], 'local six digits');
    }

    public function testAClaimedPathIsKeptButNotPlayed(): void
    {
        $facts = HistoryCall::fromOperation(self::op(), $this->settings)->facts('8352', '2026/08/10/a.wav', false, '108');

        $this->assertSame([false, '2026/08/10/a.wav'], [$facts['cRecording'], $facts['cRecordingPath']],
            'another call stores the path: the claim stays, nothing is played');
    }

    public function testOutboundCallerIsAParticipant(): void
    {
        $call = HistoryCall::fromOperation(self::op(['direction' => 'Outbound', 'callerExtension' => '105',
            'answeredExtension' => null, 'rungExtensions' => [], 'line' => null]), $this->settings);

        $this->assertSame(['105'], $call->participantExtensions());
    }

    public function testRefusals(): void
    {
        $cases = [
            'linkedId' => ['linkedId' => "1760000000.42\nAction: Command"],
            'source' => ['source' => 'live'],
            'direction' => ['direction' => 'Internal'],
            'dateStart' => ['dateStart' => '2026-08-10T09:00:00'],
            'dateEnd' => ['dateEnd' => '2026-02-30 09:00:00'],
            'dates' => ['dateEnd' => '2026-08-10 08:59:59'],
            'billSeconds' => ['billSeconds' => 121],
            'rawStatus' => ['rawStatus' => 'NOANSWER'],
            'numberRaw' => ['numberRaw' => '+7 999 000'],
            'rungExtensions' => ['rungExtensions' => ['5551']],
            'answeredExtension' => ['answeredExtension' => 'trunk-russia'],
            'clickToCall' => ['clickToCall' => 'no'],
            'recording' => ['recording' => ['path' => '../etc/passwd.wav', 'size' => 1, 'sha256' => str_repeat('a', 64)]],
        ];

        foreach ($cases as $code => $override) {
            $e = $this->assertThrows(InvalidArgumentException::class,
                fn () => HistoryCall::fromOperation(self::op($override), $this->settings));
            $this->assertSame($code, $e->getMessage(), $code);
        }
    }
}
