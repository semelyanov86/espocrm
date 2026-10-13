<?php

declare(strict_types=1);

namespace Itvolga\Tests\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Action;
use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Parser;
use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\ProtocolError;
use Itvolga\Tests\Finance\TestCase;

final class AmiTest extends TestCase
{
    private const STREAM = "Asterisk Call Manager/11.0.0\r\n"
        . "Response: Success\r\nMessage: Authentication accepted\r\n\r\n"
        . "Event: VarSet\r\nChannel: PJSIP/105-00000003\r\nVariable: MIXMONITOR_FILENAME\r\n"
        . "Value: /var/spool/asterisk/monitor/2026/10/13/a: b.wav\r\n\r\n";

    public function testWholeStreamAndBanner(): void
    {
        $parser = new Parser();
        $messages = $parser->feed(self::STREAM);

        $this->assertSame('Asterisk Call Manager/11.0.0', $parser->banner());
        $this->assertSame(2, count($messages));
        $this->assertSame('Success', $messages[0]->response());
        $this->assertSame('VarSet', $messages[1]->event());
        $this->assertSame('/var/spool/asterisk/monitor/2026/10/13/a: b.wav', $messages[1]->get('value'),
            'value after the first colon, header names case-insensitive');
    }

    public function testByteByByte(): void
    {
        $parser = new Parser();
        $messages = [];

        foreach (str_split(self::STREAM) as $byte) {
            $messages = [...$messages, ...$parser->feed($byte)];
        }

        $this->assertSame(2, count($messages));
        $this->assertSame('PJSIP/105-00000003', $messages[1]->get('Channel'));
    }

    public function testNoBannerAndBareLineFeeds(): void
    {
        $messages = (new Parser())->feed("Event: Hangup\nUniqueid: 1.1\nCause: 16\n\nEvent: Newstate\nUniqueid: 1.2\n\n");

        $this->assertSame(['Hangup', 'Newstate'], array_map(fn ($m) => $m->event(), $messages));
        $this->assertSame('16', $messages[0]->get('Cause'));
    }

    public function testRepeatedHeadersKeepTheFirstForGet(): void
    {
        $m = (new Parser())->feed("Event: X\r\nVariable: a=1\r\nVariable: b=2\r\n\r\n")[0];

        $this->assertSame('a=1', $m->get('Variable'));
        $this->assertSame(3, count($m->headers));
    }

    public function testOversizedMessageIsRefused(): void
    {
        $parser = new Parser();
        $e = $this->assertThrows(ProtocolError::class, fn () => $parser->feed("Event: X\r\nData: " . str_repeat('a', Parser::MAX_MESSAGE + 10)));
        $this->assertSame(ProtocolError::MESSAGE_TOO_LARGE, $e->reason);
        $this->assertTrue(!str_contains($e->getMessage(), 'aaaa'), 'the bytes never reach the message');
    }

    public function testActionWireForm(): void
    {
        $wire = Action::toWire('Originate', ['ActionID' => 'a1', 'Channel' => 'PJSIP/105', 'Variable' => ['A=1', 'B=2']]);

        $this->assertSame("Action: Originate\r\nActionID: a1\r\nChannel: PJSIP/105\r\nVariable: A=1\r\nVariable: B=2\r\n\r\n", $wire);
    }

    public function testHeaderInjectionIsRefused(): void
    {
        foreach (["+7999\r\nAction: Command", "x\ny", "a\0b"] as $value) {
            $this->assertThrows(ProtocolError::class, fn () => Action::toWire('Originate', ['Exten' => $value]));
        }

        $this->assertThrows(ProtocolError::class, fn () => Action::toWire('Originate', ['Bad Name' => 'x']));
        $this->assertThrows(ProtocolError::class, fn () => Action::toWire("Login\r\nX", []));
    }
}
