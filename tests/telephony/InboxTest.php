<?php

declare(strict_types=1);

namespace Itvolga\Tests\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Inbox;
use Espo\Modules\Itvolga\Tools\Telephony\Core\Ami\Parser;
use Itvolga\Tests\Finance\TestCase;

/**
 * One TCP read may carry the awaited answer and the events after it: none of them may be lost (review 2026-10-13).
 */
final class InboxTest extends TestCase
{
    public function testEventsAfterAResponseInTheSameReadAreKept(): void
    {
        $inbox = new Inbox();
        $inbox->expectResponse('a1');

        foreach ((new Parser())->feed("Event: Hangup\r\nUniqueid: 1.0\r\n\r\nResponse: Success\r\nActionID: a1\r\n\r\n"
            . "Event: Newchannel\r\nUniqueid: 2.0\r\n\r\n") as $message) {
            $inbox->push($message);
        }

        $this->assertSame('Success', $inbox->takeResponse('a1')?->response());
        $this->assertSame(['Hangup', 'Newchannel'], array_map(fn ($m) => $m->event(), $inbox->drain()));
        $this->assertSame([], $inbox->drain());
    }

    public function testEventsAfterTheCompletionOfAListAreKept(): void
    {
        $inbox = new Inbox();
        $inbox->expectList('r1', 'CoreShowChannel', 'CoreShowChannelsComplete');
        $stream = "Response: Success\r\nActionID: r1\r\nEventList: start\r\n\r\n"
            . "Event: CoreShowChannel\r\nActionID: r1\r\nChannel: PJSIP/108-00000001\r\n\r\n"
            . "Event: Newstate\r\nUniqueid: 3.0\r\n\r\n"
            . "Event: CoreShowChannelsComplete\r\nActionID: r1\r\nListItems: 1\r\n\r\n"
            . "Event: Newchannel\r\nUniqueid: 4.0\r\n\r\n";

        $messages = (new Parser())->feed($stream);

        foreach (array_slice($messages, 0, 3) as $message) {
            $inbox->push($message);
        }

        $this->assertSame(null, $inbox->takeList('r1'), 'incomplete until the completion event');

        foreach (array_slice($messages, 3) as $message) {
            $inbox->push($message);
        }

        $items = $inbox->takeList('r1');
        $this->assertSame(['PJSIP/108-00000001'], array_map(fn ($m) => $m->get('Channel'), (array) $items));
        $this->assertSame(['Newstate', 'Newchannel'], array_map(fn ($m) => $m->event(), $inbox->drain()));
    }

    public function testRefusedListAndUnexpectedResponses(): void
    {
        $inbox = new Inbox();
        $inbox->expectList('r2', 'CoreShowChannel', 'CoreShowChannelsComplete');
        $parsed = (new Parser())->feed("Response: Error\r\nActionID: r2\r\nMessage: Permission denied\r\n\r\n"
            . "Response: Success\r\nActionID: ping-7\r\nPing: Pong\r\n\r\n");

        foreach ($parsed as $message) {
            $inbox->push($message);
        }

        $this->assertSame(false, $inbox->takeList('r2'));
        $this->assertSame(['ping-7'], array_map(fn ($m) => $m->actionId(), $inbox->drain()),
            'a response nobody awaits stays in the queue');
    }
}
