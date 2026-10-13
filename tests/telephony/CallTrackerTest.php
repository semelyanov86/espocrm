<?php

declare(strict_types=1);

namespace Itvolga\Tests\Telephony;

use Espo\Modules\Itvolga\Tools\Telephony\Core\CallSnapshot;
use Espo\Modules\Itvolga\Tools\Telephony\Core\CallTracker;
use Espo\Modules\Itvolga\Tools\Telephony\Core\OpenCall;
use Espo\Modules\Itvolga\Tools\Telephony\Core\TrackerSettings;
use Itvolga\Tests\Finance\TestCase;

/**
 * Call classification, legs, answers, assignment, cards and reconciliation of the tracker on synthetic transcripts in
 * the shapes of the production dialplan (D-166).
 */
final class CallTrackerTest extends TestCase
{
    private const TRUNK = 'PJSIP/trunk-russia-00000000';
    private const REC = '/var/spool/asterisk/monitor/2026/10/13/2026.10.13_18-04_From.79990000001_To.290001.wav';

    private Pbx $pbx;

    public function setUp(): void
    {
        $this->pbx = new Pbx(new CallTracker(TrackerSettings::fromArray([])));
    }

    /**
     * Inbound: the IVR answers, 108 rings and does not answer, 208 answers (prototype transcript).
     */
    public function testInboundAnsweredBySecondPhone(): void
    {
        $p = $this->pbx;
        $l = '1791914658.0';

        $first = $p->at(0, Pbx::newChannel($l, $l, self::TRUNK, 'Ring', 'call-in', '290001', '79990' . '000001'));
        $this->assertSame(1, count($first), 'the inbound call is stored at once');
        $this->assertSame(true, $first[0]->persist);
        $this->assertSame(CallSnapshot::INBOUND, $first[0]->direction);
        $this->assertSame('+79990' . '000001', $first[0]->number);
        $this->assertSame('290001', $first[0]->line);
        $this->assertSame(null, $first[0]->assigneeExtension);
        $this->assertSame([], $first[0]->cards);

        $p->at(1, Pbx::newState($l, $l, self::TRUNK, 'Up'));
        $this->assertSame(null, $p->last()->answeredAt, 'the IVR answer is not a human answer');

        $p->at(3, Pbx::recording($l, $l, self::TRUNK, self::REC));
        $p->at(0, Pbx::newChannel('1791914660.1', $l, 'PJSIP/108-00000001', 'Down', 'call-out', 's', '108'));
        $p->at(0, Pbx::dialBegin($l, self::TRUNK, $l, '1791914660.1', 'PJSIP/108-00000001', '108'));
        $p->at(0, Pbx::newState('1791914660.1', $l, 'PJSIP/108-00000001', 'Ringing'));
        $this->assertSame(['108' => CallSnapshot::CARD_RINGING], $p->last()->cards);
        $this->assertSame('108', $p->last()->assigneeExtension);

        $p->at(6, Pbx::dialEnd($l, self::TRUNK, $l, '1791914660.1', 'PJSIP/108-00000001', 'NOANSWER'));
        $p->at(0, Pbx::hangup('1791914660.1', $l, 'PJSIP/108-00000001', '0'));
        $this->assertSame(['108' => CallSnapshot::CARD_CLOSED], $p->last()->cards);

        $p->at(0, Pbx::newChannel('1791914668.2', $l, 'PJSIP/208-00000002', 'Down', 'call-out', 's', '208'));
        $p->at(0, Pbx::dialBegin($l, self::TRUNK, $l, '1791914668.2', 'PJSIP/208-00000002', '208'));
        $p->at(0, Pbx::newState('1791914668.2', $l, 'PJSIP/208-00000002', 'Ringing'));
        $p->at(2, Pbx::newState('1791914668.2', $l, 'PJSIP/208-00000002', 'Up'));
        $p->at(0, Pbx::dialEnd($l, self::TRUNK, $l, '1791914668.2', 'PJSIP/208-00000002', 'ANSWER'));
        $answered = $p->last();
        $this->assertSame(CallSnapshot::TALKING, $answered->liveState);
        $this->assertSame('208', $answered->assigneeExtension);
        $this->assertSame(['108' => CallSnapshot::CARD_CLOSED, '208' => CallSnapshot::CARD_TALKING], $answered->cards);

        $p->at(4, Pbx::hangup('1791914668.2', $l, 'PJSIP/208-00000002'));
        $final = $p->at(0, Pbx::hangup($l, $l, self::TRUNK));

        $this->assertSame(1, count($final));
        $s = $final[0];
        $this->assertSame(true, $s->final);
        $this->assertSame('Held', $s->status());
        $this->assertSame('ANSWER', $s->rawStatus);
        $this->assertSame(4, $s->talkSeconds($p->now + 100));
        $this->assertSame(16.0, $s->endedAt - $s->startedAt);
        $this->assertSame(['108', '208'], $s->participantExtensions);
        $this->assertSame(['108' => CallSnapshot::CARD_CLOSED, '208' => CallSnapshot::CARD_ENDED], $s->cards);
        $this->assertSame(self::REC, $s->recordingFile);
        $this->assertSame(0, $p->tracker->count(), 'a finished call is forgotten');
    }

    public function testInboundMissedIsAssignedToTheFirstPhoneThatRang(): void
    {
        $p = $this->pbx;
        $l = '100.1';
        $p->at(0, Pbx::newChannel($l, $l, self::TRUNK, 'Ring', 'call-in', '290001', '89990' . '000001'));
        $this->ring($l, '100.2', '108', 'NOANSWER');
        $this->ring($l, '100.3', '208', 'NOANSWER');
        $s = $p->at(1, Pbx::hangup($l, $l, self::TRUNK))[0];

        $this->assertSame('+79990' . '000001', $s->number, '8… is the national form of +7…');
        $this->assertSame('Not Held', $s->status());
        $this->assertSame('NOANSWER', $s->rawStatus);
        $this->assertSame('108', $s->assigneeExtension);
        $this->assertSame(['108' => 'closed', '208' => 'closed'], $s->cards);
    }

    public function testHangUpInTheIvrIsStoredWithoutAssignee(): void
    {
        $p = $this->pbx;
        $l = '101.1';
        $p->at(0, Pbx::newChannel($l, $l, self::TRUNK, 'Ring', 'call-in', '290001', '79990' . '000005'));
        $p->at(1, Pbx::newState($l, $l, self::TRUNK, 'Up'));
        $s = $p->at(3, Pbx::hangup($l, $l, self::TRUNK))[0];

        $this->assertSame(true, $s->persist);
        $this->assertSame('NODIAL', $s->rawStatus);
        $this->assertSame(null, $s->assigneeExtension);
        $this->assertSame([], $s->cards);
        $this->assertSame(0, $s->talkSeconds($p->now));
    }

    public function testCallerAbandonsWhileRinging(): void
    {
        $p = $this->pbx;
        $l = '102.1';
        $p->at(0, Pbx::newChannel($l, $l, self::TRUNK, 'Ring', 'call-in', '290001', '79990' . '000001'));
        $p->at(0, Pbx::newChannel('102.2', $l, 'PJSIP/108-0000000a', 'Down'));
        $p->at(0, Pbx::dialBegin($l, self::TRUNK, $l, '102.2', 'PJSIP/108-0000000a', '108'));
        $p->at(0, Pbx::newState('102.2', $l, 'PJSIP/108-0000000a', 'Ringing'));
        $p->at(3, Pbx::dialEnd($l, self::TRUNK, $l, '102.2', 'PJSIP/108-0000000a', 'CANCEL'));
        $p->at(0, Pbx::hangup('102.2', $l, 'PJSIP/108-0000000a'));
        $s = $p->at(0, Pbx::hangup($l, $l, self::TRUNK))[0];

        $this->assertSame('CANCEL', $s->rawStatus);
        $this->assertSame('108', $s->assigneeExtension);
    }

    public function testMobileFailoverAnswerIsHeldButNotAnExtensionAnswer(): void
    {
        $p = $this->pbx;
        $l = '103.1';
        $p->at(0, Pbx::newChannel($l, $l, self::TRUNK, 'Ring', 'call-in', '290001', '79990' . '000001'));
        $this->ring($l, '103.2', '108', 'NOANSWER');
        $p->at(0, Pbx::newChannel('103.3', $l, 'PJSIP/trunk-russia-0000000b', 'Down', 'call-in', 's'));
        $p->at(0, Pbx::dialBegin($l, self::TRUNK, $l, '103.3', 'PJSIP/trunk-russia-0000000b', '+799900000' . '99@trunk-russia'));
        $p->at(2, Pbx::dialEnd($l, self::TRUNK, $l, '103.3', 'PJSIP/trunk-russia-0000000b', 'ANSWER'));
        $p->at(5, Pbx::hangup('103.3', $l, 'PJSIP/trunk-russia-0000000b'));
        $s = $p->at(0, Pbx::hangup($l, $l, self::TRUNK))[0];

        $this->assertSame('Held', $s->status());
        $this->assertSame('108', $s->assigneeExtension);
        $this->assertSame(['108' => 'closed'], $s->cards);
        $this->assertSame(5, $s->talkSeconds($p->now));
        $this->assertSame('+79990' . '000001', $s->number, 'the failover number is not the caller');
    }

    /**
     * Outbound from desk phone 105: the trunk channel is created in the trunk's inbound context and must not turn
     * the call into an inbound one (prototype transcript).
     */
    public function testOutboundFromDeskPhone(): void
    {
        $p = $this->pbx;
        $l = '1791914699.5';
        $root = 'PJSIP/105-00000003';
        $trunk = 'PJSIP/trunk-russia-00000004';

        $this->assertSame([], $p->at(0, Pbx::newChannel($l, $l, $root, 'Ring', 'call-out', '89990' . '000002', '105')),
            'not stored before it dials a trunk');
        $p->at(0, Pbx::recording($l, $l, $root, '/var/spool/asterisk/monitor/2026/10/13/x_From.105_To.+79990000002.wav'));
        $this->assertSame([], $p->at(0, Pbx::newChannel('1791914699.6', $l, $trunk, 'Down', 'call-in', 's')));
        $begin = $p->at(0, Pbx::dialBegin($l, $root, $l, '1791914699.6', $trunk, '+799900000' . '02@trunk-russia'));
        $this->assertSame(1, count($begin));
        $this->assertSame(CallSnapshot::OUTBOUND, $begin[0]->direction);
        $this->assertSame('+79990' . '000002', $begin[0]->number);
        $this->assertSame('105', $begin[0]->assigneeExtension);
        $this->assertSame(['105' => CallSnapshot::CARD_DIALING], $begin[0]->cards);
        $this->assertSame(null, $begin[0]->line);

        $p->at(1, Pbx::newState('1791914699.6', $l, $trunk, 'Ringing'));
        $p->at(2, Pbx::newState('1791914699.6', $l, $trunk, 'Up'));
        $p->at(0, Pbx::dialEnd($l, $root, $l, '1791914699.6', $trunk, 'ANSWER'));
        $this->assertSame(['105' => CallSnapshot::CARD_TALKING], $p->last()->cards);
        $p->at(3, Pbx::hangup('1791914699.6', $l, $trunk));
        $s = $p->at(0, Pbx::hangup($l, $l, $root))[0];

        $this->assertSame('Held', $s->status());
        $this->assertSame(3, $s->talkSeconds($p->now));
        $this->assertSame(['105' => CallSnapshot::CARD_ENDED], $s->cards);
        $this->assertSame(false, $s->viaCrm);
    }

    public function testOutboundBusy(): void
    {
        $s = $this->outbound('BUSY');

        $this->assertSame('Not Held', $s->status());
        $this->assertSame('BUSY', $s->rawStatus);
    }

    public function testOutboundNoAnswerAndCongestion(): void
    {
        $this->assertSame('NOANSWER', $this->outbound('NOANSWER')->rawStatus);
        $this->setUp();
        $this->assertSame('CONGESTION', $this->outbound('CONGESTION')->rawStatus);
    }

    public function testInternalCallsVoicemailAndConferenceAreNeverStored(): void
    {
        $p = $this->pbx;
        // 105 → 108 (phones-local), then the dialplan's failover to the mobile via a trunk: still internal.
        $p->at(0, Pbx::newChannel('200.1', '200.1', 'PJSIP/105-00000020', 'Ring', 'call-out', '108', '105'));
        $p->at(0, Pbx::newChannel('200.2', '200.1', 'PJSIP/108-00000021', 'Down'));
        $p->at(0, Pbx::dialBegin('200.1', 'PJSIP/105-00000020', '200.1', '200.2', 'PJSIP/108-00000021', '108'));
        $p->at(0, Pbx::newState('200.2', '200.1', 'PJSIP/108-00000021', 'Ringing'));
        $p->at(0, Pbx::dialEnd('200.1', 'PJSIP/105-00000020', '200.1', '200.2', 'PJSIP/108-00000021', 'NOANSWER'));
        $p->at(0, Pbx::newChannel('200.3', '200.1', 'PJSIP/trunk-russia-00000022', 'Down', 'call-in', 's'));
        $p->at(0, Pbx::dialBegin('200.1', 'PJSIP/105-00000020', '200.1', '200.3', 'PJSIP/trunk-russia-00000022', '+799900000' . '99@trunk-russia'));
        $p->at(0, Pbx::hangup('200.3', '200.1', 'PJSIP/trunk-russia-00000022'));
        $p->at(0, Pbx::hangup('200.2', '200.1', 'PJSIP/108-00000021'));
        $p->at(0, Pbx::hangup('200.1', '200.1', 'PJSIP/105-00000020'));
        // 105 → 808 (voicemail) and 811 (conference): no dial at all.
        $p->at(0, Pbx::newChannel('201.1', '201.1', 'PJSIP/105-00000023', 'Ring', 'call-out', '811', '105'));
        $p->at(0, Pbx::recording('201.1', '201.1', 'PJSIP/105-00000023', '/var/spool/asterisk/monitor/2026/10/13/c.wav'));
        $p->at(9, Pbx::hangup('201.1', '201.1', 'PJSIP/105-00000023'));

        $this->assertSame([], $p->snapshots);
        $this->assertSame(0, $p->tracker->count());
    }

    public function testGermanTrainerTrunkAndUnknownChannelsAreIgnored(): void
    {
        $p = $this->pbx;
        $p->at(0, Pbx::newChannel('300.1', '300.1', 'PJSIP/trunk-easybell-00000030', 'Ring', 'easybell-in', '555', '49123' . '45678'));
        $p->at(0, Pbx::newState('300.1', '300.1', 'PJSIP/trunk-easybell-00000030', 'Up'));
        $p->at(9, Pbx::hangup('300.1', '300.1', 'PJSIP/trunk-easybell-00000030'));
        // An inbound trunk outside the inbound contexts, a Local channel.
        $p->at(0, Pbx::newChannel('301.1', '301.1', 'PJSIP/trunk-russia-00000031', 'Ring', 'german-training', '555', '79990' . '000001'));
        $p->at(0, Pbx::newChannel('302.1', '302.1', 'Local/811@conf-room-00000032;1', 'Ring', 'conf-room', '811'));

        $this->assertSame([], $p->snapshots);
    }

    /**
     * Click-to-call (prototype transcript): Originate rings the user's desk phone first (DialBegin without Channel),
     * then the dialplan dials the trunk; the card says «dialing» from the start.
     */
    public function testClickToCall(): void
    {
        $p = $this->pbx;
        $l = 'crm-abc123';
        $root = 'PJSIP/105-00000005';
        $trunk = 'PJSIP/trunk-russia-00000006';

        $first = $p->at(0, Pbx::newChannel($l, $l, $root, 'Down', 'call-out', 's', '105'));
        $this->assertSame(false, $first[0]->persist, 'no Call before the trunk is dialled');
        $this->assertSame(true, $first[0]->viaCrm);
        $this->assertSame('abc123', $first[0]->intentId);
        $this->assertSame(['105' => CallSnapshot::CARD_DIALING], $first[0]->cards);

        $this->assertSame([], $p->at(0, Pbx::dialBegin(null, null, $l, $l, $root, '105')));
        $p->at(0, Pbx::newState($l, $l, $root, 'Ringing'));
        $p->at(2, Pbx::newState($l, $l, $root, 'Up'));
        $this->assertSame([], $p->at(0, Pbx::dialEnd(null, null, $l, $l, $root, 'ANSWER')),
            'picking up the own desk phone is not the answer of the call');
        $p->at(0, Pbx::recording($l, $l, $root, '/var/spool/asterisk/monitor/2026/10/13/y.wav'));
        $p->at(0, Pbx::newChannel('1791914710.9', $l, $trunk, 'Down', 'call-in', 's'));
        $begin = $p->at(0, Pbx::dialBegin($l, $root, $l, '1791914710.9', $trunk, '+799900000' . '03@trunk-russia'));
        $this->assertSame(true, $begin[0]->persist);
        $this->assertSame(null, $begin[0]->answeredAt);
        $this->assertSame('+79990' . '000003', $begin[0]->number);

        $p->at(1, Pbx::dialEnd($l, $root, $l, '1791914710.9', $trunk, 'BUSY'));
        $p->at(0, Pbx::hangup('1791914710.9', $l, $trunk, '17'));
        $s = $p->at(0, Pbx::hangup($l, $l, $root, '17'))[0];

        $this->assertSame('BUSY', $s->rawStatus);
        $this->assertSame(true, $s->viaCrm);
        $this->assertSame('abc123', $s->intentId);
        $this->assertSame(['105' => CallSnapshot::CARD_ENDED], $s->cards);
    }

    public function testClickToCallNotPickedUpLeavesNoCall(): void
    {
        $p = $this->pbx;
        $l = 'crm-def456';
        $root = 'PJSIP/105-00000007';
        $p->at(0, Pbx::newChannel($l, $l, $root, 'Down', 'call-out', 's', '105'));
        $p->at(0, Pbx::dialBegin(null, null, $l, $l, $root, '105'));
        $p->at(0, Pbx::newState($l, $l, $root, 'Ringing'));
        $p->at(20, Pbx::dialEnd(null, null, $l, $l, $root, 'NOANSWER'));
        $s = $p->at(0, Pbx::hangup($l, $l, $root, '19'))[0];

        $this->assertSame(true, $s->final);
        $this->assertSame(false, $s->persist);
        $this->assertSame(['105' => CallSnapshot::CARD_CLOSED], $s->cards);
    }

    public function testRepeatedEventsEmitNothingNew(): void
    {
        $p = $this->pbx;
        $l = '400.1';
        $p->at(0, Pbx::newChannel($l, $l, self::TRUNK, 'Ring', 'call-in', '290001', '79990' . '000001'));
        $this->ring($l, '400.2', '108', null);
        $count = count($p->snapshots);
        $p->at(1, Pbx::newState('400.2', $l, self::legChannel('108', '400.2'), 'Ringing'));
        $p->at(1, Pbx::newState($l, $l, self::TRUNK, 'Up'));
        $this->assertSame($count, count($p->snapshots), 'unchanged state is not emitted again');

        $p->at(0, Pbx::dialEnd($l, self::TRUNK, $l, '400.2', self::legChannel('108', '400.2'), 'ANSWER'));
        $answered = $p->last()->answeredAt;
        $p->at(5, Pbx::dialEnd($l, self::TRUNK, $l, '400.2', self::legChannel('108', '400.2'), 'ANSWER'));
        $this->assertSame($answered, $p->last()->answeredAt, 'a repeated DialEnd does not move the answer');
    }

    public function testParallelRingingLegs(): void
    {
        $p = $this->pbx;
        $l = '500.1';
        $p->at(0, Pbx::newChannel($l, $l, self::TRUNK, 'Ring', 'call-in', '290001', '79990' . '000001'));

        foreach (['108' => '500.2', '208' => '500.3'] as $ext => $uid) {
            $ext = (string) $ext;
            $channel = "PJSIP/$ext-0000050" . substr($uid, -1);
            $p->at(0, Pbx::newChannel($uid, $l, $channel, 'Down'));
            $p->at(0, Pbx::dialBegin($l, self::TRUNK, $l, $uid, $channel, $ext));
            $p->at(0, Pbx::newState($uid, $l, $channel, 'Ringing'));
        }

        $this->assertSame(['108' => 'ringing', '208' => 'ringing'], $p->last()->cards);
        $p->at(2, Pbx::dialEnd($l, self::TRUNK, $l, '500.3', 'PJSIP/208-00000503', 'ANSWER'));
        $p->at(0, Pbx::dialEnd($l, self::TRUNK, $l, '500.2', 'PJSIP/108-00000502', 'CANCEL'));
        $this->assertSame(['108' => 'closed', '208' => 'talking'], $p->last()->cards);
        $this->assertSame('208', $p->last()->assigneeExtension);
    }

    public function testReconcileClosesCallsThatEndedWhileAway(): void
    {
        $tracker = $this->pbx->tracker;
        $open = [
            new OpenCall('600.1', 'Inbound', false, '+79990' . '000001', '79990' . '000001', '290001', 1000.0, 1010.0, 1040.0, '208'),
            new OpenCall('601.1', 'Outbound', false, '+79990' . '000002', '+79990' . '000002', null, 1000.0, null, 1020.0, '105'),
        ];
        $out = $tracker->reconcile([], $open, 2000.0);

        $this->assertSame(2, count($out));
        [$answered, $unanswered] = $out;
        $this->assertSame(CallSnapshot::LOST, $answered->liveState);
        $this->assertSame('ANSWER', $answered->rawStatus);
        $this->assertSame(1040.0, $answered->endedAt);
        $this->assertSame(30, $answered->talkSeconds(2000.0));
        $this->assertSame('208', $answered->assigneeExtension);
        $this->assertSame('LOST', $unanswered->rawStatus);
        $this->assertSame(['105' => 'ended'], $unanswered->cards);
        $this->assertSame(0, $tracker->count());
    }

    public function testReconcileAdoptsLiveCallsAndContinues(): void
    {
        $p = $this->pbx;
        $l = '700.1';
        $open = [new OpenCall($l, 'Inbound', false, '+79990' . '000001', '79990' . '000001', '290001', 1000.0, 1010.0, 1040.0, '208')];
        $live = [
            Pbx::showChannel($l, $l, self::TRUNK, 'Up', '00:01:00', '79990' . '000001', 'incoming-menu', 't'),
            Pbx::showChannel('700.2', $l, 'PJSIP/208-00000702', 'Up', '00:00:50'),
        ];
        $out = $p->tracker->reconcile($live, $open, 1060.0);

        $this->assertSame(1, count($out));
        $this->assertSame(['208' => 'talking'], $out[0]->cards);
        $this->assertSame(1010.0, $out[0]->answeredAt, 'the stored answer time wins');
        $this->assertSame([$l], $p->tracker->liveStoredIds());

        $p->now = 1070.0;
        $p->at(0, Pbx::hangup('700.2', $l, 'PJSIP/208-00000702'));
        $s = $p->at(0, Pbx::hangup($l, $l, self::TRUNK))[0];
        $this->assertSame('ANSWER', $s->rawStatus);
        $this->assertSame(60, $s->talkSeconds(2000.0));
    }

    public function testReconcileClassifiesUnknownLiveCalls(): void
    {
        $l = '800.1';
        $live = [
            Pbx::showChannel($l, $l, self::TRUNK, 'Up', '00:00:20', '79990' . '000001', 'chose-client', 't'),
            Pbx::showChannel('800.2', $l, 'PJSIP/118-00000802', 'Ringing', '00:00:04'),
            Pbx::showChannel('900.1', '900.1', 'PJSIP/105-00000901', 'Up', '00:00:30', '105', 'sub-ifrussia', 's'),
            Pbx::showChannel('900.2', '900.1', 'PJSIP/trunk-russia-00000902', 'Up', '00:00:25', '', 'call-in', 's'),
        ];
        $out = $this->pbx->tracker->reconcile($live, [], 1000.0);

        $this->assertSame(2, count($out));
        $this->assertSame(CallSnapshot::INBOUND, $out[0]->direction);
        $this->assertSame(980.0, $out[0]->startedAt);
        $this->assertSame(['118' => 'ringing'], $out[0]->cards);
        $this->assertSame(true, $out[0]->approximate);
        $this->assertSame(CallSnapshot::OUTBOUND, $out[1]->direction);
        $this->assertSame(975.0, $out[1]->answeredAt);
        $this->assertSame('105', $out[1]->assigneeExtension);
    }

    public function testPeriodicReconcileWaitsForEventsOfFreshCalls(): void
    {
        $p = $this->pbx;
        $l = '960.1';
        $p->at(0, Pbx::newChannel($l, $l, self::TRUNK, 'Ring', 'call-in', '290001', '79990' . '000001'));
        $unknown = [Pbx::showChannel('961.1', '961.1', 'PJSIP/trunk-russia-00000961', 'Up', '00:00:05', '79990' . '000002')];

        $this->assertSame([], $p->tracker->reconcile($unknown, [], $p->now + 10, 60.0, false),
            'a call silent for 10 s is not closed, an unknown live call is not adopted');
        $this->assertSame(1, $p->tracker->count());
        $closed = $p->tracker->reconcile([], [], $p->now + 61, 60.0, false);
        $this->assertSame('LOST', $closed[0]->rawStatus);
    }

    public function testRungExtensionsAreListedInRingOrder(): void
    {
        $p = $this->pbx;
        $l = '110.1';
        $p->at(0, Pbx::newChannel($l, $l, self::TRUNK, 'Ring', 'call-in', '290001', '79990' . '000001'));
        $this->ring($l, '110.2', '108', 'NOANSWER');
        $this->ring($l, '110.3', '208', 'ANSWER');
        $s = $p->last();

        $this->assertSame(['108', '208'], $s->rungExtensions);
        $this->assertSame('208', $s->answeredExtension);
    }

    public function testADeskCallThroughTheTrainersTrunkIsNotStored(): void
    {
        $p = $this->pbx;
        $l = '120.1';
        $p->at(0, Pbx::newChannel($l, $l, 'PJSIP/105-00000120', 'Ring', 'call-out', '555', '105'));
        $p->at(0, Pbx::newChannel('120.2', $l, 'PJSIP/trunk-easybell-00000121', 'Down', 'easybell-in', 's'));
        $p->at(0, Pbx::dialBegin($l, 'PJSIP/105-00000120', $l, '120.2', 'PJSIP/trunk-easybell-00000121', '491234567' . '8@trunk-easybell'));
        $p->at(2, Pbx::dialEnd($l, 'PJSIP/105-00000120', $l, '120.2', 'PJSIP/trunk-easybell-00000121', 'ANSWER'));
        $p->at(5, Pbx::hangup('120.2', $l, 'PJSIP/trunk-easybell-00000121'));
        $p->at(0, Pbx::hangup($l, $l, 'PJSIP/105-00000120'));

        $this->assertSame([], $p->snapshots);
    }

    public function testReconcileRestoresTheTalkingPairOfAStoredAnswer(): void
    {
        $p = $this->pbx;
        $l = '130.1';
        $open = [new OpenCall($l, 'Inbound', false, '+79990' . '000001', '79990' . '000001', '290001', 1000.0, 1010.0, 1040.0,
            '208', ['108', '208'], '208')];
        $live = [
            Pbx::showChannel($l, $l, self::TRUNK, 'Up', '00:01:00', '79990' . '000001', 'chose-client', 't'),
            Pbx::showChannel('130.2', $l, 'PJSIP/208-00000132', 'Up', '00:00:50'),
        ];
        $out = $p->tracker->reconcile($live, $open, 1060.0);
        $cards = $out[0]->cards;
        ksort($cards);
        $this->assertSame(['108' => 'closed', '208' => 'talking'], $cards);
        $this->assertSame(['108', '208'], $out[0]->participantExtensions);

        $p->now = 1070.0;
        $p->at(0, Pbx::hangup('130.2', $l, 'PJSIP/208-00000132'));
        $s = $p->at(10, Pbx::hangup($l, $l, self::TRUNK))[0];
        $this->assertSame(60, $s->talkSeconds(5000.0), 'the conversation ends with the answering phone');
    }

    public function testReconcileKeepsAMobileAnswerOffTheDeskPhone(): void
    {
        $p = $this->pbx;
        $l = '140.1';
        $open = [new OpenCall($l, 'Inbound', false, '+79990' . '000001', '79990' . '000001', '290001', 1000.0, 1020.0, 1040.0,
            '108', ['108'], null)];
        $live = [
            Pbx::showChannel($l, $l, self::TRUNK, 'Up', '00:01:00', '79990' . '000001', 'chose-client', 't'),
            Pbx::showChannel('140.2', $l, 'PJSIP/trunk-russia-00000142', 'Up', '00:00:40'),
        ];
        $out = $p->tracker->reconcile($live, $open, 1060.0);
        $this->assertSame(['108' => 'closed'], $out[0]->cards, 'no talking card for a desk phone that did not answer');
        $this->assertSame('Held', $out[0]->status());
        $this->assertSame('108', $out[0]->assigneeExtension);
        $this->assertSame(null, $out[0]->answeredExtension);
    }

    public function testReconcileOfUnknownDeskCalls(): void
    {
        $live = [
            // phones-local 118 → mobile failover through a trunk: internal, as on the event path
            Pbx::channel('CoreShowChannel', '150.1', '150.1', 'PJSIP/105-00000150', 'Up', 'phones-local', '118', '105',
                ['Duration' => '00:00:20', 'Application' => 'Dial', 'ApplicationData' => 'PJSIP/+799900000' . '99@trunk-russia,30,tm']),
            Pbx::channel('CoreShowChannel', '150.2', '150.1', 'PJSIP/trunk-russia-00000151', 'Up', 'call-in', 's', '',
                ['Duration' => '00:00:10']),
            // phones-out → sub-ifrussia: external, the number from the Dial data
            Pbx::channel('CoreShowChannel', '160.1', '160.1', 'PJSIP/105-00000160', 'Up', 'sub-ifrussia', 's', '105',
                ['Duration' => '00:00:30', 'Application' => 'Dial', 'ApplicationData' => 'PJSIP/+799900000' . '02@trunk-russia,,wWtT']),
            Pbx::channel('CoreShowChannel', '160.2', '160.1', 'PJSIP/trunk-russia-00000161', 'Up', 'call-in', 's', '',
                ['Duration' => '00:00:25']),
        ];
        $out = $this->pbx->tracker->reconcile($live, [], 1000.0);

        $this->assertSame(1, count($out));
        $this->assertSame('160.1', $out[0]->linkedId);
        $this->assertSame('+79990' . '000002', $out[0]->number);
    }

    public function testReconcileKeepsThePhonesThatRangBefore(): void
    {
        $p = $this->pbx;
        $l = '170.1';
        $open = [new OpenCall($l, 'Inbound', false, '+79990' . '000001', '79990' . '000001', '290001', 1000.0, null, 1040.0,
            '108', ['108'], null)];
        $live = [
            Pbx::showChannel($l, $l, self::TRUNK, 'Up', '00:01:00', '79990' . '000001', 'chose-client', 't'),
            Pbx::showChannel('170.2', $l, 'PJSIP/208-00000172', 'Ringing', '00:00:04'),
        ];
        $out = $p->tracker->reconcile($live, $open, 1060.0);

        $this->assertSame('108', $out[0]->assigneeExtension, 'the first phone that rang stays the assignee');
        $this->assertSame(['108', '208'], $out[0]->participantExtensions);
        $cards = $out[0]->cards;
        ksort($cards);
        $this->assertSame(['108' => 'closed', '208' => 'ringing'], $cards);
        $this->assertSame(['108', '208'], $out[0]->rungExtensions);
    }

    public function testSweepForgetsStalePendingCalls(): void
    {
        $p = $this->pbx;
        $p->at(0, Pbx::newChannel('950.1', '950.1', 'PJSIP/105-00000950', 'Ring', 'call-out', '811', '105'));
        $this->assertSame(1, $p->tracker->count());
        $p->tracker->sweep($p->now + 7200);
        $this->assertSame(0, $p->tracker->count());
    }

    // ---------------------------------------------------------------------------------------------------------------

    private function ring(string $linked, string $uid, string $ext, ?string $result): void
    {
        $p = $this->pbx;
        $channel = self::legChannel($ext, $uid);
        $p->at(0, Pbx::newChannel($uid, $linked, $channel, 'Down', 'call-out', 's', $ext));
        $p->at(0, Pbx::dialBegin($linked, self::TRUNK, $linked, $uid, $channel, $ext));
        $p->at(0, Pbx::newState($uid, $linked, $channel, 'Ringing'));

        if ($result !== null) {
            $p->at(6, Pbx::dialEnd($linked, self::TRUNK, $linked, $uid, $channel, $result));
            $p->at(0, Pbx::hangup($uid, $linked, $channel, '0'));
        }
    }

    private static function legChannel(string $ext, string $uid): string
    {
        return "PJSIP/$ext-" . str_pad(str_replace('.', '', $uid), 8, '0', STR_PAD_LEFT);
    }

    private function outbound(string $status): CallSnapshot
    {
        $p = $this->pbx;
        $l = '1000.1';
        $root = 'PJSIP/112-00001000';
        $trunk = 'PJSIP/trunk-russia-00001001';
        $p->at(0, Pbx::newChannel($l, $l, $root, 'Ring', 'call-out', '+79990' . '000002', '112'));
        $p->at(0, Pbx::newChannel('1000.2', $l, $trunk, 'Down', 'call-in', 's'));
        $p->at(0, Pbx::dialBegin($l, $root, $l, '1000.2', $trunk, '+799900000' . '02@trunk-russia'));
        $p->at(4, Pbx::dialEnd($l, $root, $l, '1000.2', $trunk, $status));
        $p->at(0, Pbx::hangup('1000.2', $l, $trunk, '17'));

        return $p->at(2, Pbx::hangup($l, $l, $root, '17'))[0];
    }
}
